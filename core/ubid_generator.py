"""UBID (Unified Business ID) generation module.

This module is built to play nicely with the cleaner, matcher, and status analyzer.
It supports:
- deterministic UBID formatting
- safe fallback codes
- per state/district/category sequencing
- grouped assignment for matched records
- display parsing helpers

UBID format:
    ST-DST-CC-XXXXXXX
Where:
    ST  = 2-letter state code
    DST = 3-letter district code
    CC  = 2-letter category code
    XXXXXXX = 7-digit sequence number
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UBIDParts:
    state_code: str
    district_code: str
    category_code: str
    sequence: str


class UBIDGenerator:
    """Generates unique UBIDs for business entities."""

    CATEGORIES = {
        "trading": "TR",
        "manufacturing": "MF",
        "services": "SV",
        "service": "SV",
        "consultancy": "CS",
        "consulting": "CS",
        "retail": "RT",
        "wholesale": "WS",
        "export": "EX",
        "import": "IM",
        "logistics": "LG",
        "technology": "TC",
        "it": "TC",
        "default": "TR",
    }

    def __init__(self, db_manager=None):
        """Initialize UBID generator.

        db_manager is optional. If present, it may expose:
            get_next_sequence_number(state_code, district_code, category_code)
        """
        self.db_manager = db_manager
        self.sequence_cache: Dict[str, int] = {}
        self.generated_ubids: List[str] = []

    def generate_ubid(
        self,
        state_code: Optional[str],
        district_code: Optional[str],
        category: str = "TR",
        sequence: Optional[int] = None,
    ) -> str:
        """Generate a UBID in format: ST-DST-CC-XXXXXXX."""
        state_code = self._normalize_state_code(state_code)
        district_code = self._normalize_district_code(district_code)
        category_code = self._normalize_category_code(category)

        if sequence is None:
            sequence = self._get_next_sequence(state_code, district_code, category_code)
        else:
            sequence = self._normalize_sequence(sequence)
            self._sync_sequence_cache(state_code, district_code, category_code, sequence)

        ubid = f"{state_code}-{district_code}-{category_code}-{sequence:07d}"
        self.generated_ubids.append(ubid)
        return ubid

    def _get_next_sequence(self, state_code: str, district_code: str, category_code: str) -> int:
        """Get the next sequence for a state-district-category combination."""
        cache_key = self._cache_key(state_code, district_code, category_code)

        if cache_key in self.sequence_cache:
            self.sequence_cache[cache_key] += 1
            return self.sequence_cache[cache_key]

        # Try DB first.
        if self.db_manager is not None:
            try:
                next_seq = self.db_manager.get_next_sequence_number(
                    state_code, district_code, category_code
                )
                next_seq = self._normalize_sequence(next_seq)
                self.sequence_cache[cache_key] = next_seq
                return next_seq
            except Exception as exc:
                logger.warning("Could not get sequence from DB: %s", exc)

        # Safe fallback.
        self.sequence_cache[cache_key] = 1
        return 1

    def _sync_sequence_cache(self, state_code: str, district_code: str, category_code: str, sequence: int) -> None:
        """Ensure the cache never goes backwards."""
        cache_key = self._cache_key(state_code, district_code, category_code)
        current = self.sequence_cache.get(cache_key, 0)
        self.sequence_cache[cache_key] = max(current, sequence)

    def _cache_key(self, state_code: str, district_code: str, category_code: str) -> str:
        return f"{state_code}-{district_code}-{category_code}"

    def _normalize_state_code(self, state_code: Optional[str]) -> str:
        if not state_code:
            return "XX"
        code = str(state_code).strip().upper()
        if len(code) != 2 or not code.isalpha():
            return "XX"
        return code

    def _normalize_district_code(self, district_code: Optional[str]) -> str:
        if not district_code:
            return "XXX"
        code = str(district_code).strip().upper()
        code = "".join(ch for ch in code if ch.isalnum())
        if not code:
            return "XXX"
        if len(code) >= 3:
            return code[:3]
        return code.ljust(3, "X")

    def _normalize_category_code(self, category: Optional[str]) -> str:
        if not category:
            return "TR"

        raw = str(category).strip().lower()
        if raw in self.CATEGORIES:
            return self.CATEGORIES[raw]

        # Try substring matching for user-provided business type strings.
        for key, code in self.CATEGORIES.items():
            if key != "default" and key in raw:
                return code

        # Fall back to a stable 2-letter abbreviation.
        letters = "".join(ch for ch in raw if ch.isalpha()).upper()
        if not letters:
            return "TR"
        return letters[:2] if len(letters) >= 2 else letters.ljust(2, "X")

    def _normalize_sequence(self, sequence: Any) -> int:
        try:
            seq = int(sequence)
        except Exception:
            return 1
        return max(1, seq)

    def format_ubid_for_display(self, ubid: str) -> Dict[str, Any]:
        """Parse a UBID into components for display."""
        if not ubid or not isinstance(ubid, str):
            return {"ubid": ubid, "error": "Invalid format"}

        parts = ubid.strip().split("-")
        if len(parts) != 4:
            return {"ubid": ubid, "error": "Invalid format"}

        state_code, district_code, category, sequence = parts
        if not (len(state_code) == 2 and len(district_code) == 3 and len(category) == 2 and sequence.isdigit()):
            return {"ubid": ubid, "error": "Invalid format"}

        return {
            "ubid": ubid,
            "state_code": state_code,
            "district_code": district_code,
            "category": category,
            "sequence": sequence,
        }

    def extract_state_from_ubid(self, ubid: str) -> Optional[str]:
        """Extract state code from UBID."""
        parts = self.format_ubid_for_display(ubid)
        return parts.get("state_code") if "error" not in parts else None

    def extract_district_from_ubid(self, ubid: str) -> Optional[str]:
        """Extract district code from UBID."""
        parts = self.format_ubid_for_display(ubid)
        return parts.get("district_code") if "error" not in parts else None

    def extract_category_from_ubid(self, ubid: str) -> Optional[str]:
        """Extract category code from UBID."""
        parts = self.format_ubid_for_display(ubid)
        return parts.get("category") if "error" not in parts else None

    def extract_sequence_from_ubid(self, ubid: str) -> Optional[int]:
        """Extract numeric sequence from UBID."""
        parts = self.format_ubid_for_display(ubid)
        if "error" in parts:
            return None
        try:
            return int(parts["sequence"])
        except Exception:
            return None

    def assign_ubids(
        self,
        df: pd.DataFrame,
        match_groups: List[List[int]],
        matches: Optional[List[Any]],
    ) -> Dict[int, Dict[str, Any]]:
        """Assign UBIDs to all records based on match groups.

        Returns a mapping:
            row_index -> {
                'ubid', 'is_master', 'confidence', 'tier',
                'matched_fields', 'decision', 'group_indices'
            }
        """
        logger.info("Starting UBID assignment")

        if df is None:
            raise ValueError("df cannot be None")

        if df.empty:
            logger.warning("Empty dataframe in assign_ubids")
            return {}

        if matches is None:
            matches = []

        ubid_assignments: Dict[int, Dict[str, Any]] = {}
        grouped_records: set[int] = set()

        # Assign UBIDs to matched groups first.
        for group in match_groups or []:
            if not group or not isinstance(group, (list, tuple)):
                continue

            valid_group = [idx for idx in group if isinstance(idx, int) and 0 <= idx < len(df)]
            if not valid_group:
                continue

            try:
                rep_idx = valid_group[0]
                rep_record = df.iloc[rep_idx]

                state_code = self._fallback_state_code(rep_record.get("state_code"), rep_record.get("state"))
                district_code = self._fallback_district_code(rep_record.get("district_code"), rep_record.get("district"))
                category_code = self._fallback_category_code(rep_record)

                ubid = self.generate_ubid(state_code, district_code, category_code)

                from .matching_engine import MatchingEngine

                engine = MatchingEngine()
                confidence, tier, matched_fields = engine.calculate_group_confidence(valid_group, matches)

                if confidence >= 90:
                    decision = "AutoMerge"
                elif confidence >= 70:
                    decision = "NeedsReview"
                else:
                    decision = "KeepSeparate"

                for idx in valid_group:
                    ubid_assignments[idx] = {
                        "ubid": ubid,
                        "is_master": idx == rep_idx,
                        "confidence": confidence,
                        "tier": tier,
                        "matched_fields": matched_fields,
                        "decision": decision,
                        "group_indices": list(valid_group),
                    }
                    grouped_records.add(idx)
            except Exception as exc:
                logger.error("Error processing group %s: %s", group, exc)
                continue

        # Assign new UBIDs to everything else.
        for idx in range(len(df)):
            if idx in grouped_records:
                continue

            try:
                record = df.iloc[idx]
                state_code = self._fallback_state_code(record.get("state_code"), record.get("state"))
                district_code = self._fallback_district_code(record.get("district_code"), record.get("district"))
                category_code = self._fallback_category_code(record)

                ubid = self.generate_ubid(state_code, district_code, category_code)
                ubid_assignments[idx] = {
                    "ubid": ubid,
                    "is_master": True,
                    "confidence": 100.0,
                    "tier": "New",
                    "matched_fields": [],
                    "decision": "New",
                    "group_indices": [idx],
                }
            except Exception as exc:
                logger.error("Error assigning UBID to record %s: %s", idx, exc)
                ubid_assignments[idx] = {
                    "ubid": self.generate_ubid("XX", "XXX", "TR"),
                    "is_master": True,
                    "confidence": 100.0,
                    "tier": "New",
                    "matched_fields": [],
                    "decision": "New",
                    "group_indices": [idx],
                }

        logger.info("Assigned %s UBIDs", len(ubid_assignments))
        return ubid_assignments

    def _fallback_state_code(self, state_code: Optional[str], state_name: Optional[str]) -> str:
        if state_code and isinstance(state_code, str) and len(state_code.strip()) == 2:
            return state_code.strip().upper()

        if state_name:
            from .data_cleaner import DataCleaner
            cleaner = DataCleaner()
            resolved = cleaner.get_state_code(state_name)
            if resolved:
                return resolved

        return "XX"

    def _fallback_district_code(self, district_code: Optional[str], district_name: Optional[str]) -> str:
        if district_code and isinstance(district_code, str) and len(district_code.strip()) == 3:
            return district_code.strip().upper()

        if district_name:
            from .data_cleaner import DataCleaner
            cleaner = DataCleaner()
            resolved = cleaner.get_district_code(district_name)
            if resolved:
                return resolved

        return "XXX"

    def _fallback_category_code(self, record: Any) -> str:
        category_value = None
        for key in ("business_type", "category", "industry", "segment"):
            try:
                category_value = record.get(key)
            except Exception:
                category_value = None
            if category_value:
                break

        return self._normalize_category_code(category_value)

    def assign_single_ubid(
        self,
        state_code: Optional[str] = None,
        district_code: Optional[str] = None,
        category: str = "TR",
        sequence: Optional[int] = None,
    ) -> str:
        """Convenience wrapper for a single UBID."""
        return self.generate_ubid(state_code, district_code, category, sequence)

    def get_sequence_snapshot(self) -> Dict[str, int]:
        """Return the current sequence cache."""
        return dict(self.sequence_cache)

    def get_generated_ubids(self) -> List[str]:
        """Return a copy of generated UBIDs."""
        return list(self.generated_ubids)

    def reset_state(self) -> None:
        """Reset generated UBIDs and sequence cache."""
        self.sequence_cache.clear()
        self.generated_ubids.clear()


__all__ = ["UBIDGenerator", "UBIDParts"]
