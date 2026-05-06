"""Business matching engine with tiered duplicate detection.

This module is designed to work with the accompanying DataCleaner and UBIDGenerator.
It focuses on being deterministic, safe, and easy to reason about:
- Tier 1: exact identifier matches (PAN / GSTIN)
- Tier 2: strong business-name similarity + shared location
- Tier 3: moderate business-name similarity + shared location
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from rapidfuzz import fuzz


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MatchResult:
    """Represents a match between two records."""

    record1_id: int
    record2_id: int
    score: float
    tier: str
    matched_fields: List[str]
    reason: str
    decision: str  # AutoMerge, NeedsReview, KeepSeparate


class MatchingEngine:
    """Engine for matching duplicate business records."""

    # Exact match tier
    TIER1_EXACT_MATCH = 100.0

    # Name similarity thresholds
    TIER2_NAME_THRESHOLD = 85.0
    TIER3_NAME_MIN = 70.0
    TIER3_NAME_MAX = 85.0

    # Confidence thresholds for final decision
    AUTO_MERGE_MIN = 90.0
    NEEDS_REVIEW_MIN = 70.0

    # Candidate limits keep runtime sane on larger files
    MAX_CANDIDATES_PER_RECORD = 500

    def __init__(self):
        self.match_stats = {
            "total_records": 0,
            "total_comparisons": 0,
            "tier1_matches": 0,
            "tier2_matches": 0,
            "tier3_matches": 0,
            "auto_merge": 0,
            "needs_review": 0,
            "keep_separate": 0,
        }

    def find_matches(self, df: pd.DataFrame) -> List[MatchResult]:
        """Find all potential matches in the dataset."""
        if df is None:
            raise ValueError("df cannot be None")

        logger.info("Starting match detection for %s records", len(df))
        self.match_stats = {
            "total_records": len(df),
            "total_comparisons": 0,
            "tier1_matches": 0,
            "tier2_matches": 0,
            "tier3_matches": 0,
            "auto_merge": 0,
            "needs_review": 0,
            "keep_separate": 0,
        }

        if df.empty:
            logger.warning("Empty dataframe provided for matching")
            return []

        records = df.to_dict("records")
        matches: List[MatchResult] = []
        processed_pairs: Set[Tuple[int, int]] = set()

        # Build indexes for efficient candidate retrieval.
        pan_index = self._build_index(df, "cleaned_pan")
        gstin_index = self._build_index(df, "cleaned_gstin")
        pincode_index = self._build_index(df, "normalized_pincode")
        district_index = self._build_index(df, "district")
        name_index = self._build_name_index(df)

        logger.info(
            "Indices built: PAN=%s, GSTIN=%s, PIN=%s, DIST=%s, NAME_BUCKETS=%s",
            len(pan_index), len(gstin_index), len(pincode_index), len(district_index), len(name_index),
        )

        for i, record1 in enumerate(records):
            if i % 100 == 0:
                logger.info("Processed %s/%s records", i, len(records))

            tier1_candidates = self._find_tier1_candidates(record1, pan_index, gstin_index)
            tier2_candidates = self._find_tier2_candidates(record1, pincode_index, district_index, name_index)

            # Tier 1 first: exact identifiers are authoritative.
            for j in tier1_candidates:
                if j == i:
                    continue
                pair_key = self._pair_key(i, j)
                if pair_key in processed_pairs:
                    continue

                try:
                    record2 = records[j]
                    match = self._create_tier1_match(record1, record2, i, j)
                    if match:
                        matches.append(match)
                        processed_pairs.add(pair_key)
                        self._increment_decision(match.decision)
                        self.match_stats["tier1_matches"] += 1
                except Exception as exc:
                    logger.warning("Tier 1 match failed for %s,%s: %s", i, j, exc)

            # Tier 2 / Tier 3: name + location.
            for j in tier2_candidates:
                if j == i:
                    continue
                pair_key = self._pair_key(i, j)
                if pair_key in processed_pairs:
                    continue

                try:
                    record2 = records[j]
                    match = self._create_name_location_match(record1, record2, i, j)
                    if match:
                        matches.append(match)
                        processed_pairs.add(pair_key)
                        self._increment_decision(match.decision)
                        if match.tier == "Tier2":
                            self.match_stats["tier2_matches"] += 1
                        elif match.tier == "Tier3":
                            self.match_stats["tier3_matches"] += 1
                except Exception as exc:
                    logger.warning("Tier 2/3 match failed for %s,%s: %s", i, j, exc)

        self.match_stats["total_comparisons"] = len(processed_pairs)
        logger.info("Match detection completed. Found %s matches", len(matches))
        return matches

    def _pair_key(self, i: int, j: int) -> Tuple[int, int]:
        return (i, j) if i < j else (j, i)

    def _increment_decision(self, decision: str) -> None:
        if decision == "AutoMerge":
            self.match_stats["auto_merge"] += 1
        elif decision == "NeedsReview":
            self.match_stats["needs_review"] += 1
        else:
            self.match_stats["keep_separate"] += 1

    def _build_index(self, df: pd.DataFrame, column: str) -> Dict[str, List[int]]:
        """Build a value -> row indices index."""
        index: Dict[str, List[int]] = defaultdict(list)
        if column not in df.columns:
            return index

        for idx, value in df[column].items():
            if pd.notna(value) and value != "":
                key = str(value).strip()
                index[key].append(idx)
        return index

    def _build_name_index(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """Build a phonetic / cleaned-name bucket index for faster lookups."""
        index: Dict[str, List[int]] = defaultdict(list)
        if "cleaned_name" not in df.columns:
            return index

        for idx, value in df["cleaned_name"].items():
            if pd.notna(value) and value:
                name = str(value).strip()
                bucket = self._name_bucket(name)
                index[bucket].append(idx)
        return index

    def _name_bucket(self, name: str) -> str:
        """Create a conservative bucket key for candidate generation."""
        tokens = [t for t in name.lower().split() if len(t) >= 3]
        if not tokens:
            return "_empty"
        # Prefer first meaningful token + length signature.
        return f"{tokens[0][:6]}::{len(tokens)}"

    def _find_tier1_candidates(
        self,
        record: Dict,
        pan_index: Dict[str, List[int]],
        gstin_index: Dict[str, List[int]],
    ) -> List[int]:
        """Find candidates for exact PAN/GSTIN matching."""
        candidates: Set[int] = set()

        pan = record.get("cleaned_pan")
        if pan and pan in pan_index:
            candidates.update(pan_index[pan])

        gstin = record.get("cleaned_gstin")
        if gstin and gstin in gstin_index:
            candidates.update(gstin_index[gstin])

        return self._cap_candidates(sorted(candidates))

    def _find_tier2_candidates(
        self,
        record: Dict,
        pincode_index: Dict[str, List[int]],
        district_index: Dict[str, List[int]],
        name_index: Dict[str, List[int]],
    ) -> List[int]:
        """Find candidates for name/location matching."""
        candidates: Set[int] = set()

        pincode = record.get("normalized_pincode")
        if pincode and str(pincode) in pincode_index:
            candidates.update(pincode_index[str(pincode)])

        district = record.get("district")
        if district and str(district).strip() in district_index:
            candidates.update(district_index[str(district).strip()])

        cleaned_name = record.get("cleaned_name")
        if cleaned_name:
            bucket = self._name_bucket(str(cleaned_name))
            if bucket in name_index:
                candidates.update(name_index[bucket])

        return self._cap_candidates(sorted(candidates))

    def _cap_candidates(self, candidates: List[int]) -> List[int]:
        if len(candidates) <= self.MAX_CANDIDATES_PER_RECORD:
            return candidates
        return candidates[: self.MAX_CANDIDATES_PER_RECORD]

    def _create_tier1_match(
        self,
        record1: Dict,
        record2: Dict,
        idx1: int,
        idx2: int,
    ) -> Optional[MatchResult]:
        """Create a Tier 1 exact identifier match."""
        pan1, pan2 = record1.get("cleaned_pan"), record2.get("cleaned_pan")
        gstin1, gstin2 = record1.get("cleaned_gstin"), record2.get("cleaned_gstin")

        matched_fields: List[str] = []
        reasons: List[str] = []

        if pan1 and pan2 and pan1 == pan2:
            matched_fields.append("PAN")
            reasons.append(f"PAN exact match: {pan1}")

        if gstin1 and gstin2 and gstin1 == gstin2:
            matched_fields.append("GSTIN")
            reasons.append(f"GSTIN exact match: {gstin1}")

        if not matched_fields:
            return None

        return MatchResult(
            record1_id=idx1,
            record2_id=idx2,
            score=100.0,
            tier="Tier1",
            matched_fields=matched_fields,
            reason="; ".join(reasons),
            decision="AutoMerge",
        )

    def _create_name_location_match(
        self,
        record1: Dict,
        record2: Dict,
        idx1: int,
        idx2: int,
    ) -> Optional[MatchResult]:
        """Create Tier 2 / Tier 3 match based on name and location."""
        name1 = record1.get("cleaned_name")
        name2 = record2.get("cleaned_name")

        if not name1 or not name2:
            return None

        name_score = self._calculate_name_similarity(str(name1), str(name2))
        pincode_match = self._same_non_null(record1.get("normalized_pincode"), record2.get("normalized_pincode"))
        district_match = self._same_non_null(record1.get("district"), record2.get("district"))
        state_match = self._same_non_null(record1.get("state_code"), record2.get("state_code"))

        location_score = 0
        location_fields: List[str] = []

        if pincode_match:
            location_score += 25
            location_fields.append("pincode")
        if district_match:
            location_score += 15
            location_fields.append("district")
        if state_match:
            location_score += 10
            location_fields.append("state")

        combined_score = min(100.0, 0.80 * name_score + location_score)

        # Strong enough to auto merge.
        if name_score >= self.TIER2_NAME_THRESHOLD and (pincode_match or district_match or state_match):
            matched_fields = ["business_name"] + location_fields
            return MatchResult(
                record1_id=idx1,
                record2_id=idx2,
                score=float(combined_score),
                tier="Tier2",
                matched_fields=matched_fields,
                reason=self._build_reason(name_score, location_fields, record1, record2),
                decision="AutoMerge" if combined_score >= self.AUTO_MERGE_MIN else "NeedsReview",
            )

        # Moderate similarity, keep for review only.
        if self.TIER3_NAME_MIN <= name_score < self.TIER3_NAME_MAX and (pincode_match or district_match or state_match):
            matched_fields = ["business_name"] + location_fields
            return MatchResult(
                record1_id=idx1,
                record2_id=idx2,
                score=float(combined_score),
                tier="Tier3",
                matched_fields=matched_fields,
                reason=self._build_reason(name_score, location_fields, record1, record2, review=True),
                decision="NeedsReview",
            )

        return None

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate robust name similarity."""
        # Best of several similarity measures.
        scores = [
            fuzz.token_sort_ratio(name1, name2),
            fuzz.token_set_ratio(name1, name2),
            fuzz.partial_ratio(name1, name2),
        ]
        return float(max(scores))

    @staticmethod
    def _same_non_null(a, b) -> bool:
        return a is not None and b is not None and str(a).strip() != "" and str(a).strip() == str(b).strip()

    def _build_reason(
        self,
        name_score: float,
        location_fields: List[str],
        record1: Dict,
        record2: Dict,
        review: bool = False,
    ) -> str:
        location_text = ", ".join(location_fields) if location_fields else "no shared location"
        suffix = " - manual review suggested" if review else ""
        return f"Name similarity: {name_score:.1f}% with {location_text}{suffix}"

    def group_matches(self, matches: List[MatchResult], total_records: int) -> List[List[int]]:
        """Group matched records into clusters using Union-Find."""
        if total_records <= 0:
            return []

        parent = list(range(total_records))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

        for match in matches:
            if match.decision in {"AutoMerge", "Approved"}:
                if 0 <= match.record1_id < total_records and 0 <= match.record2_id < total_records:
                    union(match.record1_id, match.record2_id)

        groups: Dict[int, List[int]] = defaultdict(list)
        for i in range(total_records):
            groups[find(i)].append(i)

        return [group for group in groups.values() if len(group) > 1]

    def calculate_group_confidence(
        self,
        group: List[int],
        matches: List[MatchResult],
    ) -> Tuple[float, str, List[str]]:
        """Calculate overall confidence for a match group."""
        try:
            if not group or not isinstance(group, (list, tuple)):
                return 50.0, "Tier3", ["business_name"]

            if not matches:
                return 50.0, "Tier3", ["business_name"]

            group_set = set(group)
            group_matches = [
                m for m in matches
                if m.record1_id in group_set and m.record2_id in group_set
            ]

            if not group_matches:
                return 50.0, "Tier3", ["business_name"]

            scores = [float(m.score) for m in group_matches if m.score is not None]
            if not scores:
                return 50.0, "Tier3", ["business_name"]

            avg_score = sum(scores) / len(scores)
            avg_score = max(0.0, min(100.0, avg_score))

            tiers = [m.tier for m in group_matches]
            if "Tier1" in tiers:
                tier = "Tier1"
            elif "Tier2" in tiers:
                tier = "Tier2"
            else:
                tier = "Tier3"

            all_fields: Set[str] = set()
            for match in group_matches:
                all_fields.update(match.matched_fields)

            return avg_score, tier, sorted(all_fields) if all_fields else ["business_name"]
        except Exception as exc:
            logger.error("Error calculating group confidence: %s", exc)
            return 50.0, "Tier3", ["business_name"]

    def get_match_stats(self) -> Dict[str, int]:
        """Return matching statistics."""
        return dict(self.match_stats)

    def reset_stats(self) -> None:
        """Reset internal counters."""
        self.match_stats = {
            "total_records": 0,
            "total_comparisons": 0,
            "tier1_matches": 0,
            "tier2_matches": 0,
            "tier3_matches": 0,
            "auto_merge": 0,
            "needs_review": 0,
            "keep_separate": 0,
        }


__all__ = ["MatchResult", "MatchingEngine"]
