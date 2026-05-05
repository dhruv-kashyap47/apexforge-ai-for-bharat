import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.data_cleaner import DataCleaner
from core.matching_engine import MatchingEngine
from core.status_analyzer import StatusAnalyzer
from core.ubid_generator import UBIDGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataService:

    def __init__(self, db_manager=None):
        self.db = db_manager
        self.cleaner = DataCleaner()
        self.matcher = MatchingEngine()
        self.status_analyzer = StatusAnalyzer()
        self.ubid_gen = UBIDGenerator(db_manager)

    def _has_db(self) -> bool:
        return self.db is not None

    def _safe_na(self, value: Any) -> Any:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        return value

    def _ensure_batch_id(self, batch_id: Optional[str] = None) -> str:
        return batch_id or f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"

    def process_upload(self, df: pd.DataFrame, batch_id: Optional[str] = None) -> Tuple[str, pd.DataFrame]:
        batch_id = self._ensure_batch_id(batch_id)
        df_clean = self.cleaner.clean_dataframe(df)
        df_clean["upload_batch_id"] = batch_id
        df_clean["db_id"] = range(len(df_clean))

        if self._has_db():
            try:
                inserted_ids = self._store_raw_records(df_clean)
                for idx, db_id in enumerate(inserted_ids):
                    if idx < len(df_clean):
                        df_clean.at[idx, "db_id"] = db_id
            except Exception as exc:
                logger.warning("Raw record storage skipped: %s", exc)

        df_status = self.status_analyzer.analyze_dataframe(df_clean)
        return batch_id, df_status

    def process_full_pipeline(self, df: pd.DataFrame, batch_id: Optional[str] = None) -> Dict[str, Any]:
        batch_id, df_status = self.process_upload(df, batch_id=batch_id)
        matches = self.matcher.find_matches(df_status)
        groups = self.matcher.group_matches(matches, len(df_status))
        assignments = self.ubid_gen.assign_ubids(df_status, groups, matches)
        df_final = self._attach_results(df_status, assignments)

        if self._has_db():
            try:
                self.store_match_results(batch_id, matches, groups, assignments, df_final)
            except Exception as exc:
                logger.warning("Match result storage skipped: %s", exc)

        return {
            "batch_id": batch_id,
            "df": df_final,
            "matches": matches,
            "groups": groups,
            "assignments": assignments,
        }

    def _attach_results(self, df: pd.DataFrame, assignments: Dict[int, Dict]) -> pd.DataFrame:
        out = df.copy()
        out["ubid"] = ""
        out["match_confidence"] = 0.0
        out["match_tier"] = ""
        out["match_decision"] = ""
        out["is_master"] = False

        for idx, assignment in assignments.items():
            if 0 <= idx < len(out) and isinstance(assignment, dict):
                out.at[idx, "ubid"] = assignment.get("ubid", "")
                out.at[idx, "match_confidence"] = float(assignment.get("confidence", 0.0) or 0.0)
                out.at[idx, "match_tier"] = assignment.get("tier", "")
                out.at[idx, "match_decision"] = assignment.get("decision", "")
                out.at[idx, "is_master"] = bool(assignment.get("is_master", False))

        return out

    def _store_raw_records(self, df: pd.DataFrame) -> List[int]:
        if not self._has_db():
            return []

        cols = [
            "upload_batch_id", "business_name", "pan", "gstin", "address", "pincode",
            "district", "state", "registration_date", "last_activity_date", "department",
            "cleaned_name", "cleaned_pan", "cleaned_gstin", "cleaned_address",
            "normalized_pincode", "name_phonetic"
        ]
        available_cols = [c for c in cols if c in df.columns]
        if not available_cols:
            return []

        df_to_store = df[available_cols].copy()
        inserted_ids: List[int] = []

        for _, row in df_to_store.iterrows():
            row_dict = {col: self._safe_na(row.get(col)) for col in df_to_store.columns}
            cols_sql = ", ".join(row_dict.keys())
            placeholders = ", ".join([f":{k}" for k in row_dict.keys()])
            query = f"INSERT INTO raw_records ({cols_sql}) VALUES ({placeholders}) RETURNING id"
            result = self.db.execute_query(query, row_dict)
            if result:
                inserted_ids.append(result[0]["id"])

        return inserted_ids

    def store_match_results(
        self,
        batch_id: str,
        matches: List,
        match_groups: List[List[int]],
        ubid_assignments: Dict[int, Dict],
        df: pd.DataFrame,
    ) -> Dict:
        if not self._has_db():
            return {"ubids_stored": 0, "groups_stored": 0, "review_queue_items": 0}

        if not ubid_assignments:
            return {"ubids_stored": 0, "groups_stored": 0, "review_queue_items": 0}

        stored_ubids = 0
        stored_groups = 0
        review_queue_items = 0

        ubid_groups: Dict[str, Dict[str, Any]] = {}
        for idx, assignment in ubid_assignments.items():
            if not isinstance(assignment, dict):
                continue
            ubid = assignment.get("ubid")
            if not ubid:
                continue
            ubid_groups.setdefault(ubid, {"indices": [], "assignment": assignment})["indices"].append(idx)

        for ubid, group_data in ubid_groups.items():
            try:
                indices = [i for i in group_data.get("indices", []) if isinstance(i, int) and 0 <= i < len(df)]
                if not indices:
                    continue

                assignment = group_data["assignment"]
                master_idx = indices[0]
                master_record = df.iloc[master_idx]
                db_ids = [self._safe_na(df.iloc[i].get("db_id", i)) for i in indices]
                db_ids = [x for x in db_ids if x is not None]
                if not db_ids:
                    continue

                master_db_id = db_ids[0]
                self._store_ubid_registry(ubid, master_record, assignment, len(indices))
                stored_ubids += 1

                group_id = self._store_matched_group(ubid, master_db_id, db_ids, assignment)
                if group_id:
                    stored_groups += 1

                if assignment.get("decision") == "NeedsReview" and len(db_ids) > 1 and group_id:
                    for i in range(len(db_ids)):
                        for j in range(i + 1, len(db_ids)):
                            item = self._add_to_review_queue(group_id, db_ids[i], db_ids[j], assignment)
                            if item:
                                review_queue_items += 1
            except Exception as exc:
                logger.warning("Skipping UBID group %s: %s", ubid, exc)

        self._store_match_logs(batch_id, matches, ubid_assignments, df)

        return {
            "ubids_stored": stored_ubids,
            "groups_stored": stored_groups,
            "review_queue_items": review_queue_items,
        }

    def _store_ubid_registry(self, ubid: str, master_record: pd.Series, assignment: Dict, total_records: int):
        if not self._has_db():
            return

        parts = ubid.split("-")
        query = """
            INSERT INTO ubid_registry
            (ubid, state_code, district_code, category, sequence_number,
             business_name, primary_pan, primary_gstin, business_status,
             total_records, last_activity_date, registration_date)
            VALUES
            (:ubid, :state_code, :district_code, :category, :sequence,
             :business_name, :primary_pan, :primary_gstin, :business_status,
             :total_records, :last_activity_date, :registration_date)
            ON CONFLICT (ubid) DO UPDATE SET
                total_records = EXCLUDED.total_records,
                updated_at = CURRENT_TIMESTAMP
        """
        params = {
            "ubid": ubid,
            "state_code": parts[0] if len(parts) > 0 else "XX",
            "district_code": parts[1] if len(parts) > 1 else "XXX",
            "category": parts[2] if len(parts) > 2 else "TR",
            "sequence": int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0,
            "business_name": self._safe_na(master_record.get("business_name")),
            "primary_pan": self._safe_na(master_record.get("cleaned_pan")),
            "primary_gstin": self._safe_na(master_record.get("cleaned_gstin")),
            "business_status": self._safe_na(master_record.get("business_status")) or "Closed",
            "total_records": total_records,
            "last_activity_date": self._safe_na(master_record.get("last_activity_date")),
            "registration_date": self._safe_na(master_record.get("registration_date")),
        }
        self.db.execute_command(query, params)

    def _store_matched_group(self, ubid: str, master_id: int, record_ids: List[int], assignment: Dict) -> Optional[int]:
        if not self._has_db():
            return None

        query = """
            INSERT INTO matched_groups
            (ubid, master_record_id, record_ids, match_confidence, match_tier,
             match_reason, matched_fields, status)
            VALUES
            (:ubid, :master_id, :record_ids, :confidence, :tier,
             :reason, :fields, :status)
            RETURNING id
        """
        params = {
            "ubid": ubid,
            "master_id": master_id,
            "record_ids": record_ids,
            "confidence": float(assignment.get("confidence", 50.0) or 50.0),
            "tier": assignment.get("tier", "Tier3"),
            "reason": f"Decision: {assignment.get('decision', 'Unknown')}",
            "fields": assignment.get("matched_fields", []),
            "status": "Active" if assignment.get("decision") == "AutoMerge" else "UnderReview",
        }
        result = self.db.execute_query(query, params)
        return result[0]["id"] if result else None

    def _add_to_review_queue(self, group_id: int, record1_id: int, record2_id: int, assignment: Dict) -> Optional[int]:
        if not self._has_db():
            return None

        query = """
            INSERT INTO review_queue
            (match_group_id, record1_id, record2_id, match_score, match_details, status)
            VALUES
            (:group_id, :record1_id, :record2_id, :score, :details, 'Pending')
            RETURNING id
        """
        params = {
            "group_id": group_id,
            "record1_id": record1_id,
            "record2_id": record2_id,
            "score": float(assignment.get("confidence", 0.0) or 0.0),
            "details": {
                "tier": assignment.get("tier", ""),
                "matched_fields": assignment.get("matched_fields", []),
                "reason": "Weak match requires review",
            },
        }
        result = self.db.execute_query(query, params)
        return result[0]["id"] if result else None

    def _store_match_logs(self, batch_id: str, matches: List, ubid_assignments: Dict, df: pd.DataFrame):
        if not self._has_db() or not matches:
            return

        query = """
            INSERT INTO match_logs
            (upload_batch_id, record1_id, record2_id, match_score, match_tier,
             match_fields, match_decision)
            VALUES
            (:batch_id, :record1_id, :record2_id, :score, :tier, :fields, :decision)
        """

        for match in matches:
            idx1 = getattr(match, "record1_id", None)
            idx2 = getattr(match, "record2_id", None)
            if idx1 is None or idx2 is None:
                continue

            db_id1 = self._safe_na(df.iloc[idx1].get("db_id", idx1)) if idx1 < len(df) else idx1
            db_id2 = self._safe_na(df.iloc[idx2].get("db_id", idx2)) if idx2 < len(df) else idx2

            params = {
                "batch_id": batch_id,
                "record1_id": db_id1,
                "record2_id": db_id2,
                "score": float(getattr(match, "score", 0.0) or 0.0),
                "tier": getattr(match, "tier", ""),
                "fields": getattr(match, "matched_fields", []),
                "decision": getattr(match, "decision", ""),
            }
            self.db.execute_command(query, params)

    def get_batch_stats(self, batch_id: str) -> Dict:
        stats = {
            "batch_id": batch_id,
            "total_records": 0,
            "matches_found": 0,
            "ubids_generated": 0,
            "active_count": 0,
            "dormant_count": 0,
            "closed_count": 0,
            "pending_reviews": 0,
        }

        if not self._has_db():
            return stats

        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM raw_records WHERE upload_batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            stats["total_records"] = int(result[0]["count"]) if result else 0
        except Exception:
            pass

        try:
            ubid_result = self.db.execute_query(
                """
                SELECT COUNT(DISTINCT mg.ubid) as count
                FROM matched_groups mg
                JOIN raw_records rr ON rr.id = ANY(mg.record_ids)
                WHERE rr.upload_batch_id = :batch_id
                """,
                {"batch_id": batch_id},
            )
            stats["ubids_generated"] = int(ubid_result[0]["count"]) if ubid_result else 0
        except Exception:
            pass

        try:
            status_result = self.db.execute_query(
                """
                SELECT business_status, COUNT(*) as count
                FROM ubid_registry
                WHERE ubid IN (
                    SELECT DISTINCT mg.ubid
                    FROM matched_groups mg
                    JOIN raw_records rr ON rr.id = ANY(mg.record_ids)
                    WHERE rr.upload_batch_id = :batch_id
                )
                GROUP BY business_status
                """,
                {"batch_id": batch_id},
            )
            for row in status_result or []:
                key = f"{str(row['business_status']).lower()}_count"
                if key in stats:
                    stats[key] = int(row["count"])
        except Exception:
            pass

        try:
            review_result = self.db.execute_query(
                """
                SELECT COUNT(*) as count
                FROM review_queue rq
                JOIN matched_groups mg ON rq.match_group_id = mg.id
                JOIN raw_records rr ON rr.id = ANY(mg.record_ids)
                WHERE rr.upload_batch_id = :batch_id AND rq.status = 'Pending'
                """,
                {"batch_id": batch_id},
            )
            stats["pending_reviews"] = int(review_result[0]["count"]) if review_result else 0
        except Exception:
            pass

        return stats

    def get_review_queue(self, status: str = "Pending", limit: int = 100) -> pd.DataFrame:
        if not self._has_db():
            return pd.DataFrame()

        query = """
            SELECT
                rq.id as review_id,
                rq.match_score,
                rq.match_details,
                rq.status as review_status,
                rq.created_at,
                r1.business_name as record1_name,
                r1.pan as record1_pan,
                r1.gstin as record1_gstin,
                r1.address as record1_address,
                r2.business_name as record2_name,
                r2.pan as record2_pan,
                r2.gstin as record2_gstin,
                r2.address as record2_address,
                mg.ubid
            FROM review_queue rq
            JOIN raw_records r1 ON rq.record1_id = r1.id
            JOIN raw_records r2 ON rq.record2_id = r2.id
            JOIN matched_groups mg ON rq.match_group_id = mg.id
            WHERE rq.status = :status
            ORDER BY rq.match_score DESC
            LIMIT :limit
        """
        try:
            return self.db.read_dataframe(query, {"status": status, "limit": limit})
        except Exception:
            return pd.DataFrame()

    def update_review_decision(self, review_id: int, decision: str, notes: str = "", reviewer: str = "system") -> bool:
        if not self._has_db():
            return False

        try:
            self.db.execute_command(
                """
                UPDATE review_queue
                SET status = :status,
                    reviewer_notes = :notes,
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = :reviewer
                WHERE id = :review_id
                """,
                {
                    "status": decision,
                    "notes": notes,
                    "reviewer": reviewer,
                    "review_id": review_id,
                },
            )

            if decision == "Approved":
                self.db.execute_command(
                    """
                    UPDATE matched_groups
                    SET status = 'Merged'
                    WHERE id = (SELECT match_group_id FROM review_queue WHERE id = :review_id)
                    """,
                    {"review_id": review_id},
                )

            return True
        except Exception as exc:
            logger.error("Failed to update review decision: %s", exc)
            return False

    def search_ubid(self, query: str) -> pd.DataFrame:
        if not self._has_db():
            return pd.DataFrame()

        sql = """
            SELECT
                u.*,
                mg.record_ids,
                mg.match_confidence,
                mg.match_tier
            FROM ubid_registry u
            LEFT JOIN matched_groups mg ON u.ubid = mg.ubid
            WHERE u.ubid ILIKE :query
               OR u.business_name ILIKE :query
               OR u.primary_pan ILIKE :query
               OR u.primary_gstin ILIKE :query
            ORDER BY u.created_at DESC
            LIMIT 100
        """
        try:
            return self.db.read_dataframe(sql, {"query": f"%{query}%"})
        except Exception:
            return pd.DataFrame()

    def get_ubid_details(self, ubid: str) -> Optional[Dict]:
        if not self._has_db():
            return None

        try:
            ubid_result = self.db.execute_query(
                "SELECT * FROM ubid_registry WHERE ubid = :ubid",
                {"ubid": ubid},
            )
            if not ubid_result:
                return None

            records_result = self.db.execute_query(
                """
                SELECT rr.*
                FROM raw_records rr
                JOIN matched_groups mg ON rr.id = ANY(mg.record_ids)
                WHERE mg.ubid = :ubid
                """,
                {"ubid": ubid},
            )

            match_result = self.db.execute_query(
                "SELECT * FROM matched_groups WHERE ubid = :ubid",
                {"ubid": ubid},
            )

            return {
                "ubid_info": ubid_result[0],
                "records": records_result or [],
                "match_info": match_result[0] if match_result else None,
            }
        except Exception:
            return None
