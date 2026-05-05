import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.matching_engine import MatchingEngine, MatchResult
from core.ubid_generator import UBIDGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MatchService:

    def __init__(self, db_manager=None):
        self.db = db_manager
        self.engine = MatchingEngine()
        self.ubid_gen = UBIDGenerator(db_manager)

    def _has_db(self) -> bool:
        return self.db is not None

    # -----------------------------
    # MAIN PIPELINE
    # -----------------------------
    def process_matching(self, df: pd.DataFrame, batch_id: Optional[str] = None) -> Tuple[List[MatchResult], List[List[int]], Dict[int, Dict]]:
        if df is None or df.empty:
            return [], [], {}

        matches = self.engine.find_matches(df)
        groups = self.engine.group_matches(matches, len(df))
        assignments = self.ubid_gen.assign_ubids(df, groups, matches)

        return matches, groups, assignments

    # -----------------------------
    # EXPLANATION (UI READY)
    # -----------------------------
    def get_match_explanation(self, match: MatchResult, r1: pd.Series, r2: pd.Series) -> Dict[str, Any]:
        score = float(match.score or 0.0)

        if score >= 90:
            level = "High"
            desc = "Very strong match"
        elif score >= 70:
            level = "Medium"
            desc = "Needs verification"
        else:
            level = "Low"
            desc = "Likely different"

        return {
            "score": f"{score:.1f}%",
            "tier": match.tier,
            "decision": match.decision,
            "reason": match.reason,
            "fields": match.matched_fields,
            "confidence_level": level,
            "confidence_description": desc,
            "record1": self._record_summary(r1),
            "record2": self._record_summary(r2),
        }

    def _record_summary(self, r: pd.Series) -> Dict[str, Any]:
        return {
            "name": r.get("business_name"),
            "pan": r.get("pan"),
            "gstin": r.get("gstin"),
            "district": r.get("district"),
            "state": r.get("state"),
        }

    # -----------------------------
    # FAST SINGLE RECORD MATCH
    # -----------------------------
    def find_potential_matches_for_record(self, record: pd.Series, existing: pd.DataFrame, top_k: int = 10) -> List[Dict]:
        if record is None or existing is None or existing.empty:
            return []

        from rapidfuzz import fuzz

        results: List[Dict] = []

        name1 = record.get("cleaned_name")
        pan1 = record.get("cleaned_pan")
        gst1 = record.get("cleaned_gstin")

        for idx, row in existing.iterrows():

            pan2 = row.get("cleaned_pan")
            gst2 = row.get("cleaned_gstin")

            # Tier 1 fast path
            if pan1 and pan2 and pan1 == pan2:
                results.append(self._build_result(row, idx, "PAN", 100.0, pan1))
                continue

            if gst1 and gst2 and gst1 == gst2:
                results.append(self._build_result(row, idx, "GSTIN", 100.0, gst1))
                continue

            # Name similarity
            name2 = row.get("cleaned_name")
            if not name1 or not name2:
                continue

            score = max(
                fuzz.token_sort_ratio(name1, name2),
                fuzz.token_set_ratio(name1, name2),
                fuzz.partial_ratio(name1, name2),
            )

            if score < 70:
                continue

            location_match = (
                record.get("normalized_pincode") == row.get("normalized_pincode")
                or record.get("district") == row.get("district")
                or record.get("state_code") == row.get("state_code")
            )

            if not location_match:
                continue

            results.append(self._build_result(row, idx, "NAME+LOCATION", float(score), None))

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _build_result(self, row: pd.Series, idx: int, typ: str, score: float, detail: Optional[str]) -> Dict:
        return {
            "record_id": row.get("db_id", idx),
            "type": typ,
            "score": score,
            "detail": detail,
            "name": row.get("business_name"),
            "district": row.get("district"),
            "state": row.get("state"),
        }

    # -----------------------------
    # OPTIONAL DB STORAGE (SAFE)
    # -----------------------------
    def store_matches(self, batch_id: str, matches: List[MatchResult], df: pd.DataFrame):
        if not self._has_db() or not matches:
            return

        query = """
            INSERT INTO match_logs
            (upload_batch_id, record1_id, record2_id, match_score, match_tier, match_fields, match_decision)
            VALUES (:batch_id, :r1, :r2, :score, :tier, :fields, :decision)
        """

        for m in matches:
            try:
                r1 = df.iloc[m.record1_id].get("db_id", m.record1_id)
                r2 = df.iloc[m.record2_id].get("db_id", m.record2_id)

                self.db.execute_command(query, {
                    "batch_id": batch_id,
                    "r1": r1,
                    "r2": r2,
                    "score": float(m.score or 0),
                    "tier": m.tier,
                    "fields": m.matched_fields,
                    "decision": m.decision,
                })
            except Exception as e:
                logger.warning(f"Match log skipped: {e}")
