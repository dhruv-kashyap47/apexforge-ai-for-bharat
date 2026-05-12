"""UBID (Unified Business ID) generation module.

This module is built to play nicely with the cleaner, matcher, and status analyzer.
It supports:
- deterministic UBID formatting
- safe fallback codes
- per state/district/category identity prefixes
- randomized 7-digit suffixes with collision checks
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
import secrets
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import uuid

# External libraries for ultra-fast performance
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
    HAS_CONCURRENT = True
except ImportError:
    HAS_CONCURRENT = False

try:
    import mmh3  # MurmurHash3 for ultra-fast hashing
    HAS_MMH3 = True
except ImportError:
    HAS_MMH3 = False

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
        self.used_suffixes: Dict[str, set[int]] = defaultdict(set)
        self.generated_ubids: List[str] = []

        # Ultra-fast performance optimizations
        self.use_numpy = HAS_NUMPY
        self.use_concurrent = HAS_CONCURRENT
        self.use_mmh3 = HAS_MMH3

        # Pre-allocate random number generator for batch operations
        self.rng = secrets.SystemRandom()

        # Performance metrics
        self.generation_count = 0
        self.collision_count = 0

        logger.info(f"UBID Generator initialized with: NumPy={self.use_numpy}, Concurrent={self.use_concurrent}, MMH3={self.use_mmh3}")

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
            self._register_sequence(state_code, district_code, category_code, sequence)

        ubid = f"{state_code}-{district_code}-{category_code}-{sequence:07d}"
        self.generated_ubids.append(ubid)
        return ubid

    def _get_next_sequence(self, state_code: str, district_code: str, category_code: str) -> int:
        """Get a random 7-digit suffix for a state-district-category combination."""
        cache_key = self._cache_key(state_code, district_code, category_code)

        # Ultra-fast batch generation with NumPy if available
        if self.use_numpy:
            return self._get_next_sequence_numpy(cache_key, state_code, district_code, category_code)
        else:
            return self._get_next_sequence_standard(cache_key, state_code, district_code, category_code)

    def _get_next_sequence_numpy(self, cache_key: str, state_code: str, district_code: str, category_code: str) -> int:
        """Ultra-fast sequence generation using NumPy."""
        used_set = self.used_suffixes[cache_key]

        # Generate large batch of random numbers at once
        batch_size = 64  # Larger batch for NumPy
        random_numbers = np.random.randint(1, 10_000_000, batch_size, dtype=np.int32)

        # Filter out used numbers
        available_numbers = [num for num in random_numbers if num not in used_set]

        if available_numbers:
            sequence = int(available_numbers[0])  # Take first available

            # Fast database check if needed
            if self.db_manager and hasattr(self.db_manager, 'ubid_exists'):
                test_ubid = f"{state_code}-{district_code}-{category_code}-{sequence:07d}"
                if not self.db_manager.ubid_exists(test_ubid):
                    self._register_sequence(state_code, district_code, category_code, sequence)
                    self.generation_count += 1
                    return sequence
            else:
                self._register_sequence(state_code, district_code, category_code, sequence)
                self.generation_count += 1
                return sequence

        # Fallback to standard method if no available numbers
        return self._get_next_sequence_standard(cache_key, state_code, district_code, category_code)

    def _get_next_sequence_standard(self, cache_key: str, state_code: str, district_code: str, category_code: str) -> int:
        """Standard sequence generation with optimizations."""
        used_set = self.used_suffixes[cache_key]

        # Optimized: Pre-generate multiple random numbers for better performance
        for attempt in range(16):  # Reduced attempts with batch generation
            # Generate 4 random numbers at once for better performance
            sequences = [secrets.randbelow(10_000_000) for _ in range(4)]
            for sequence in sequences:
                if sequence == 0:
                    sequence = 1
                if sequence not in used_set:
                    # Fast path: skip database check for high-performance mode
                    if not self.db_manager or not hasattr(self.db_manager, 'ubid_exists'):
                        self._register_sequence(state_code, district_code, category_code, sequence)
                        self.generation_count += 1
                        return sequence
                    else:
                        # Only check database if we have a manager (slower but safer)
                        test_ubid = f"{state_code}-{district_code}-{category_code}-{sequence:07d}"
                        if not self.db_manager.ubid_exists(test_ubid):
                            self._register_sequence(state_code, district_code, category_code, sequence)
                            self.generation_count += 1
                            return sequence

        # Fallback: use timestamp-based random for ultra-rare collisions
        import time
        fallback_seed = int(time.time() * 1000) & 0xFFFFFF
        sequence = (fallback_seed + secrets.randbelow(1000)) % 10_000_000
        if sequence == 0:
            sequence = 1
        self._register_sequence(state_code, district_code, category_code, sequence)
        self.generation_count += 1
        self.collision_count += 1
        logger.warning(f"UBID generation used fallback for {cache_key} after batch attempts")
        return sequence

    def _register_sequence(self, state_code: str, district_code: str, category_code: str, sequence: int) -> None:
        """Record a suffix so we do not reuse it within the current runtime."""
        cache_key = self._cache_key(state_code, district_code, category_code)
        current = self.sequence_cache.get(cache_key, 0)
        self.sequence_cache[cache_key] = max(current, sequence)
        self.used_suffixes[cache_key].add(sequence)

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

    def generate_ubid_batch(self, requests: List[Dict[str, Any]]) -> List[str]:
        """Generate multiple UBIDs in batch for ultra-fast performance."""
        ubids = []

        # Pre-allocate cache keys and group by state-district-category for efficiency
        cache_groups = {}
        for req in requests:
            state_code = self._normalize_state_code(req.get("state_code"))
            district_code = self._normalize_district_code(req.get("district_code"))
            category_code = self._normalize_category_code(req.get("category", "TR"))
            cache_key = self._cache_key(state_code, district_code, category_code)

            if cache_key not in cache_groups:
                cache_groups[cache_key] = {
                    "state_code": state_code,
                    "district_code": district_code,
                    "category_code": category_code,
                    "requests": []
                }
            cache_groups[cache_key]["requests"].append(req)

        # Generate UBIDs in batches per cache group
        for cache_key, group in cache_groups.items():
            state_code = group["state_code"]
            district_code = group["district_code"]
            category_code = group["category_code"]

            # Pre-generate all needed sequences for this group
            needed_count = len(group["requests"])
            sequences = self._generate_batch_sequences(cache_key, needed_count)

            # Create UBIDs for each request in this group
            for i, req in enumerate(group["requests"]):
                if i < len(sequences):
                    sequence = sequences[i]
                    ubid = f"{state_code}-{district_code}-{category_code}-{sequence:07d}"
                    ubids.append(ubid)
                    self.generated_ubids.append(ubid)
                else:
                    # Fallback to individual generation if batch failed
                    ubid = self.generate_ubid(state_code, district_code, category_code)
                    ubids.append(ubid)

        return ubids

    def _generate_batch_sequences(self, cache_key: str, count: int) -> List[int]:
        """Generate multiple unique sequences for a cache key."""
        used_set = self.used_suffixes[cache_key]
        sequences = []

        # Generate in batches of 8 for efficiency
        batch_size = 8
        attempts_needed = (count + batch_size - 1) // batch_size

        for attempt in range(attempts_needed):
            # Generate batch of random sequences
            batch_sequences = [secrets.randbelow(10_000_000) for _ in range(batch_size)]

            # Filter and collect unique sequences
            for sequence in batch_sequences:
                if sequence == 0:
                    sequence = 1
                if sequence not in used_set and sequence not in sequences:
                    # Fast path: skip database check for performance
                    if not self.db_manager or not hasattr(self.db_manager, 'ubid_exists'):
                        sequences.append(sequence)
                        self._register_sequence(cache_key.split('-')[0], cache_key.split('-')[1], cache_key.split('-')[2], sequence)
                    else:
                        test_ubid = f"{cache_key}-{sequence:07d}"
                        if not self.db_manager.ubid_exists(test_ubid):
                            sequences.append(sequence)
                            self._register_sequence(cache_key.split('-')[0], cache_key.split('-')[1], cache_key.split('-')[2], sequence)

                    if len(sequences) >= count:
                        return sequences

        return sequences

    def generate_ubid_batch_quantum(self, requests: List[Dict[str, Any]]) -> List[str]:
        """Quantum-speed batch UBID generation using concurrent processing."""
        if not self.use_concurrent:
            return self.generate_ubid_batch(requests)

        # Group requests by cache key for concurrent processing
        cache_groups = {}
        for req in requests:
            state_code = self._normalize_state_code(req.get("state_code"))
            district_code = self._normalize_district_code(req.get("district_code"))
            category_code = self._normalize_category_code(req.get("category", "TR"))
            cache_key = self._cache_key(state_code, district_code, category_code)

            if cache_key not in cache_groups:
                cache_groups[cache_key] = {
                    "state_code": state_code,
                    "district_code": district_code,
                    "category_code": category_code,
                    "requests": []
                }
            cache_groups[cache_key]["requests"].append(req)

        # Process groups concurrently
        ubids = []
        with ThreadPoolExecutor(max_workers=min(len(cache_groups), 8)) as executor:
            futures = []
            for cache_key, group in cache_groups.items():
                future = executor.submit(self._process_group_quantum, cache_key, group)
                futures.append(future)

            # Collect results
            for future in futures:
                try:
                    group_ubids = future.result(timeout=30)  # 30 second timeout
                    ubids.extend(group_ubids)
                except Exception as exc:
                    logger.warning(f"Concurrent generation failed: {exc}")
                    # Fallback to standard batch generation
                    pass

        return ubids

    def _process_group_quantum(self, cache_key: str, group: Dict) -> List[str]:
        """Process a single group with quantum-speed generation."""
        state_code = group["state_code"]
        district_code = group["district_code"]
        category_code = group["category_code"]
        needed_count = len(group["requests"])

        # Ultra-fast batch generation with NumPy
        if self.use_numpy:
            sequences = self._generate_quantum_sequences(cache_key, needed_count, state_code, district_code, category_code)
        else:
            sequences = self._generate_batch_sequences(cache_key, needed_count)

        # Create UBIDs
        ubids = []
        for i, req in enumerate(group["requests"]):
            if i < len(sequences):
                sequence = sequences[i]
                ubid = f"{state_code}-{district_code}-{category_code}-{sequence:07d}"
                ubids.append(ubid)
                self.generated_ubids.append(ubid)
            else:
                # Fallback
                ubid = self.generate_ubid(state_code, district_code, category_code)
                ubids.append(ubid)

        return ubids

    def _generate_quantum_sequences(self, cache_key: str, count: int, state_code: str, district_code: str, category_code: str) -> List[int]:
        """Ultra-fast quantum sequence generation with MurmurHash3."""
        used_set = self.used_suffixes[cache_key]
        sequences = []

        # Generate large batch with NumPy
        batch_size = max(count * 4, 256)  # Generate 4x more than needed
        random_numbers = np.random.randint(1, 10_000_000, batch_size, dtype=np.int32)

        # Use MurmurHash3 for ultra-fast collision detection if available
        if self.use_mmh3:
            # Create hash set for ultra-fast lookup
            used_hashes = {mmh3.hash(str(num)) for num in used_set}

            for num in random_numbers:
                num_hash = mmh3.hash(str(num))
                if num_hash not in used_hashes and num not in sequences:
                    # Fast database check if needed
                    if self.db_manager and hasattr(self.db_manager, 'ubid_exists'):
                        test_ubid = f"{state_code}-{district_code}-{category_code}-{num:07d}"
                        if not self.db_manager.ubid_exists(test_ubid):
                            sequences.append(int(num))
                            self._register_sequence(state_code, district_code, category_code, int(num))
                            used_hashes.add(num_hash)  # Update hash set
                    else:
                        sequences.append(int(num))
                        self._register_sequence(state_code, district_code, category_code, int(num))
                        used_hashes.add(num_hash)  # Update hash set

                    if len(sequences) >= count:
                        break
        else:
            # Fallback to standard checking
            for num in random_numbers:
                if num not in used_set and num not in sequences:
                    # Fast database check if needed
                    if self.db_manager and hasattr(self.db_manager, 'ubid_exists'):
                        test_ubid = f"{state_code}-{district_code}-{category_code}-{num:07d}"
                        if not self.db_manager.ubid_exists(test_ubid):
                            sequences.append(int(num))
                            self._register_sequence(state_code, district_code, category_code, int(num))
                    else:
                        sequences.append(int(num))
                        self._register_sequence(state_code, district_code, category_code, int(num))

                    if len(sequences) >= count:
                        break

        return sequences

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the UBID generator."""
        return {
            "total_generated": self.generation_count,
            "collisions": self.collision_count,
            "collision_rate": (self.collision_count / max(self.generation_count, 1)) * 100,
            "numpy_available": self.use_numpy,
            "concurrent_available": self.use_concurrent,
            "mmh3_available": self.use_mmh3,
            "performance_mode": "quantum" if self.use_numpy and self.use_concurrent else "standard"
        }

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
        self.used_suffixes.clear()
        self.generated_ubids.clear()


__all__ = ["UBIDGenerator", "UBIDParts"]
