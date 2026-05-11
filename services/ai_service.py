"""Lightweight Gemini-based review assistance for match explanations.

This module keeps generative AI strictly advisory:
- it never changes match decisions
- it only sees two compact record snapshots plus match metadata
- it caches responses locally to minimize API usage
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

import pandas as pd

from core.matching_engine import MatchResult


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIReviewService:
    """Gemini-backed helper for concise match explanations."""

    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_TIMEOUT_SECONDS = 12
    DEFAULT_MAX_OUTPUT_TOKENS = 160
    DEFAULT_MIN_CALL_GAP_SECONDS = 1.2
    DEFAULT_CACHE_TTL_SECONDS = 7 * 24 * 3600
    DEFAULT_QUALITY_MODEL_OUTPUT_TOKENS = 180

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
        self.model = (model or os.getenv("GEMINI_MODEL") or self.DEFAULT_MODEL).strip()
        self.timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", str(self.DEFAULT_TIMEOUT_SECONDS)))
        self.max_output_tokens = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", str(self.DEFAULT_MAX_OUTPUT_TOKENS)))
        self.min_call_gap_seconds = float(os.getenv("GEMINI_MIN_CALL_GAP_SECONDS", str(self.DEFAULT_MIN_CALL_GAP_SECONDS)))
        self.cache_ttl_seconds = int(os.getenv("GEMINI_CACHE_TTL_SECONDS", str(self.DEFAULT_CACHE_TTL_SECONDS)))
        self.quality_max_output_tokens = int(
            os.getenv("GEMINI_QUALITY_MAX_OUTPUT_TOKENS", str(self.DEFAULT_QUALITY_MODEL_OUTPUT_TOKENS))
        )
        self.enabled = bool(self.api_key)

        base_dir = Path(cache_dir or os.getenv("GEMINI_CACHE_DIR") or Path(tempfile.gettempdir()) / "apexforge_ai")
        self.cache_dir = base_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / "gemini_match_explanations.json"

        self._lock = threading.Lock()
        self._memory_cache: Dict[str, Dict[str, Any]] = self._load_cache_file()
        self._last_call_at = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        return self.enabled

    def should_offer_explanation(self, match: MatchResult, explicit: bool = False) -> bool:
        if explicit:
            return True
        if match.decision == "NeedsReview":
            return True
        try:
            score = float(match.score or 0.0)
        except Exception:
            score = 0.0
        return 70.0 <= score < 90.0

    def get_status_snapshot(self) -> Dict[str, Any]:
        """Return a small operational snapshot for the UI."""
        return {
            "available": self.enabled,
            "model": self.model,
            "cache_items": len(self._memory_cache),
            "cache_file": str(self.cache_path),
        }

    def get_cached_explanation(
        self,
        match: MatchResult,
        record1: pd.Series,
        record2: pd.Series,
    ) -> Optional[Dict[str, Any]]:
        key = self._cache_key(match, record1, record2)
        cached = self._memory_cache.get(key)
        if not cached:
            return None
        if self._is_expired(cached):
            return None
        result = dict(cached.get("result", {}))
        if result:
            result["cached"] = True
            return result
        return None

    def explain_match(
        self,
        match: MatchResult,
        record1: pd.Series,
        record2: pd.Series,
        explicit: bool = False,
    ) -> Dict[str, Any]:
        """Return a compact, auditable explanation.

        The service falls back to deterministic text if Gemini is unavailable or fails.
        """
        cached = self.get_cached_explanation(match, record1, record2)
        if cached is not None:
            return cached

        if not self.should_offer_explanation(match, explicit=explicit):
            return self._deterministic_fallback(
                match,
                record1,
                record2,
                reason="not_eligible",
            )

        if not self.enabled:
            return self._deterministic_fallback(match, record1, record2, reason="gemini_disabled")

        payload = self._build_request_payload(match, record1, record2)
        result = self._call_gemini(payload, match, record1, record2)
        self._store_cache(result["cache_key"], result)
        return result

    def analyze_data_quality(
        self,
        profile: Dict[str, Any],
        explicit: bool = False,
    ) -> Dict[str, Any]:
        """Summarize aggregated dataset quality without inspecting raw rows."""
        normalized_profile = self._normalize_quality_profile(profile)
        cache_key = self._quality_cache_key(normalized_profile)
        cached = self._memory_cache.get(cache_key)
        if cached and not self._is_expired(cached):
            result = dict(cached.get("result", {}))
            if result:
                result["cached"] = True
                return result

        fallback = self._deterministic_quality_fallback(normalized_profile)
        if not self.enabled or not explicit:
            self._store_cache(cache_key, fallback)
            return fallback

        payload = self._build_quality_payload(normalized_profile)
        result = self._call_gemini_quality(payload, normalized_profile, cache_key)
        self._store_cache(cache_key, result)
        return result

    def parse_search_query(self, query: str) -> Dict[str, Any]:
        """Translate a short natural-language query into deterministic filters."""
        raw_query = (query or "").strip()
        if not raw_query:
            return {
                "ok": False,
                "query": "",
                "filters": {},
                "description": "Enter a search phrase to filter the current batch.",
            }

        q = raw_query.lower()
        filters: Dict[str, Any] = {}
        notes: List[str] = []
        search_terms: List[str] = []

        state_map = {
            "odisha": "Odisha",
            "orissa": "Odisha",
            "karnataka": "Karnataka",
            "maharashtra": "Maharashtra",
            "tamil nadu": "Tamil Nadu",
            "telangana": "Telangana",
            "gujarat": "Gujarat",
            "west bengal": "West Bengal",
            "delhi": "Delhi",
            "uttar pradesh": "Uttar Pradesh",
            "rajasthan": "Rajasthan",
            "madhya pradesh": "Madhya Pradesh",
        }
        for key, value in state_map.items():
            if key in q:
                filters["state"] = value
                notes.append(f"state={value}")
                break

        district_match = re.search(r"\b(?:district|dist)\s*[:=]?\s*([a-z][a-z .&/-]{1,40})", raw_query, flags=re.IGNORECASE)
        if district_match:
            district_value = district_match.group(1).strip().rstrip(".,")
            if district_value:
                filters["district"] = district_value
                notes.append(f"district={district_value}")

        tier_map = {
            "tier1": "Tier1",
            "tier 1": "Tier1",
            "tier2": "Tier2",
            "tier 2": "Tier2",
            "tier3": "Tier3",
            "tier 3": "Tier3",
            "new": "New",
        }
        for key, value in tier_map.items():
            if key in q:
                filters["match_tier"] = value
                notes.append(f"tier={value}")
                break

        if any(token in q for token in ["dormant", "inactive", "sleeping"]):
            filters["business_status"] = "Dormant"
            notes.append("status=Dormant")
        elif any(token in q for token in ["closed", "inactive business", "shut"]):
            filters["business_status"] = "Closed"
            notes.append("status=Closed")
        elif any(token in q for token in ["active", "live", "operating"]):
            filters["business_status"] = "Active"
            notes.append("status=Active")

        if any(token in q for token in ["needs review", "review queue", "manual review", "flagged"]):
            filters["match_decision"] = "NeedsReview"
            notes.append("decision=NeedsReview")

        if any(token in q for token in ["duplicate", "duplicates", "matched", "same business"]):
            filters["group_only"] = True
            notes.append("duplicates_only")

        score_match = re.search(r"\b(?:confidence|score)\s*(?:above|over|at least|>=|greater than)\s*(\d{1,3})", q)
        if score_match:
            filters["min_confidence"] = min(100, max(0, int(score_match.group(1))))
            notes.append(f"confidence>={filters['min_confidence']}")
        elif any(token in q for token in ["high confidence", "auto merge", "certain", "strong match"]):
            filters["min_confidence"] = 90
            notes.append("confidence>=90")
        elif any(token in q for token in ["medium confidence", "maybe", "review"]):
            filters["min_confidence"] = 70
            notes.append("confidence>=70")

        low_match = re.search(r"\b(?:confidence|score)\s*(?:below|under|<=|less than)\s*(\d{1,3})", q)
        if low_match:
            filters["max_confidence"] = min(100, max(0, int(low_match.group(1))))
            notes.append(f"confidence<={filters['max_confidence']}")
        elif any(token in q for token in ["low confidence", "keep separate"]):
            filters["max_confidence"] = 69
            notes.append("confidence<=69")

        limit_match = re.search(r"\b(?:top|first|show)\s+(\d{1,3})\b", q)
        if limit_match:
            filters["limit"] = min(100, max(1, int(limit_match.group(1))))
            notes.append(f"limit={filters['limit']}")
        elif any(token in q for token in ["all results", "everything", "show all"]):
            filters["limit"] = None

        if any(token in q for token in ["highest confidence", "top confidence", "best match"]):
            filters["sort_by_confidence"] = "desc"
            notes.append("sort=confidence_desc")
        elif any(token in q for token in ["lowest confidence", "weakest match"]):
            filters["sort_by_confidence"] = "asc"
            notes.append("sort=confidence_asc")

        stop_words = {
            "show", "find", "list", "give", "me", "all", "any", "the", "a", "an", "and", "or",
            "with", "for", "in", "of", "to", "from", "records", "record", "rows", "business",
            "businesses", "firms", "items", "results", "apexforge", "ai", "data", "this", "that",
            "these", "those", "top", "first", "high", "low", "confidence", "score", "duplicate",
            "duplicates", "matched", "same", "review", "queue", "inactive", "active", "closed",
        }
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9&/.-]{1,}", raw_query)
        for token in tokens:
            cleaned = token.strip().lower()
            if cleaned in stop_words:
                continue
            if cleaned.isdigit():
                continue
            if cleaned not in search_terms:
                search_terms.append(cleaned)

        if search_terms:
            filters["search_terms"] = search_terms[:6]
            notes.append("free_text_search")

        if any(token in q for token in ["pan", "gstin", "ubid"]):
            notes.append("identifier search")

        return {
            "ok": True,
            "query": raw_query,
            "filters": filters,
            "description": ", ".join(notes) if notes else "Applied a conservative filter based on the query.",
        }

    # ------------------------------------------------------------------
    # Request / response handling
    # ------------------------------------------------------------------

    def _build_request_payload(
        self,
        match: MatchResult,
        record1: pd.Series,
        record2: pd.Series,
    ) -> Dict[str, Any]:
        r1 = self._compact_record(record1)
        r2 = self._compact_record(record2)

        prompt = {
            "task": "Explain why these two business records were matched or flagged for review.",
            "rules": [
                "Use only the provided fields.",
                "Do not invent missing data.",
                "Return JSON only.",
                "Maximum 3 bullets.",
                "Keep the tone concise, audit-friendly, and neutral.",
            ],
            "match": {
                "score": round(float(match.score or 0.0), 1),
                "tier": match.tier,
                "decision": match.decision,
                "matched_fields": list(match.matched_fields or []),
                "reason": self._clip_text(match.reason, 180),
            },
            "record_1": r1,
            "record_2": r2,
            "output": {
                "bullets": ["string", "string", "string"],
                "recommendation": "Merge | Review | KeepSeparate | Unknown",
                "confidence_summary": "short sentence",
                "uncertainty": "short sentence",
                "evidence": ["field names only"],
            },
        }

        return {
            "system_instruction": {
                "parts": [
                    {
                        "text": (
                            "You are a conservative enterprise review assistant for business entity matching. "
                            "Use only the supplied fields. If a value is missing, say unknown. "
                            "Do not speculate. Output valid JSON only."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(prompt, ensure_ascii=True, separators=(",", ":")),
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.2,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": {
                    "type": "object",
                    "properties": {
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3,
                        },
                        "recommendation": {"type": "string"},
                        "confidence_summary": {"type": "string"},
                        "uncertainty": {"type": "string"},
                        "evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3,
                        },
                    },
                    "required": [
                        "bullets",
                        "recommendation",
                        "confidence_summary",
                        "uncertainty",
                        "evidence",
                    ],
                },
            },
        }

    def _build_quality_payload(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        prompt = {
            "task": "Summarize dataset quality from aggregated metrics only.",
            "rules": [
                "Use only the supplied aggregates.",
                "Do not invent missing values.",
                "Return JSON only.",
                "Maximum 3 bullets.",
                "Keep the tone concise and audit-friendly.",
            ],
            "profile": profile,
            "output": {
                "bullets": ["string", "string", "string"],
                "quality_score": 0,
                "summary": "short sentence",
                "risks": ["string", "string", "string"],
                "recommendations": ["string", "string", "string"],
                "flagged_regions": ["string", "string", "string"],
            },
        }

        return {
            "system_instruction": {
                "parts": [
                    {
                        "text": (
                            "You are a conservative data quality analyst. "
                            "Use only aggregated counts. Do not infer row-level facts. "
                            "Output valid JSON only."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(prompt, ensure_ascii=True, separators=(",", ":")),
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.2,
                "maxOutputTokens": self.quality_max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": {
                    "type": "object",
                    "properties": {
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3,
                        },
                        "quality_score": {"type": "number"},
                        "summary": {"type": "string"},
                        "risks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3,
                        },
                        "recommendations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3,
                        },
                        "flagged_regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3,
                        },
                    },
                    "required": [
                        "bullets",
                        "quality_score",
                        "summary",
                        "risks",
                        "recommendations",
                        "flagged_regions",
                    ],
                },
            },
        }

    def _call_gemini_quality(
        self,
        payload: Dict[str, Any],
        profile: Dict[str, Any],
        cache_key: str,
    ) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error_message: Optional[str] = None
        transient_codes = {429, 500, 502, 503, 504}

        for attempt in range(2):
            self._throttle()
            try:
                with urlrequest.urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
            except urlerror.HTTPError as exc:
                last_error_message = self._extract_http_error(exc)
                if exc.code in transient_codes and attempt == 0:
                    time.sleep(1.0 + attempt)
                    continue
                return self._deterministic_quality_fallback(profile, cache_key=cache_key, reason=f"http_{exc.code}", error_message=last_error_message)
            except (urlerror.URLError, TimeoutError, OSError) as exc:
                last_error_message = str(exc)
                if attempt == 0:
                    time.sleep(1.0 + attempt)
                    continue
                return self._deterministic_quality_fallback(profile, cache_key=cache_key, reason="request_failed", error_message=last_error_message)
            except Exception as exc:
                return self._deterministic_quality_fallback(profile, cache_key=cache_key, reason="request_failed", error_message=str(exc))

            parsed = self._parse_response(raw)
            if parsed is None:
                last_error_message = "Gemini returned an invalid or empty JSON payload"
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                return self._deterministic_quality_fallback(profile, cache_key=cache_key, reason="invalid_json", error_message=last_error_message)

            normalized = self._normalize_quality_response(parsed, profile)
            normalized["source"] = "gemini"
            normalized["cached"] = False
            normalized["cache_key"] = cache_key
            normalized["model"] = self.model
            return normalized

        return self._deterministic_quality_fallback(profile, cache_key=cache_key, reason="request_failed", error_message=last_error_message or "Gemini request failed")

    def _normalize_quality_response(self, parsed: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        bullets = [self._clip_text(item, 180) for item in (parsed.get("bullets") or []) if self._clip_text(item, 180)]
        risks = [self._clip_text(item, 140) for item in (parsed.get("risks") or []) if self._clip_text(item, 140)]
        recommendations = [self._clip_text(item, 140) for item in (parsed.get("recommendations") or []) if self._clip_text(item, 140)]
        flagged_regions = [self._clip_text(item, 80) for item in (parsed.get("flagged_regions") or []) if self._clip_text(item, 80)]

        quality_score = parsed.get("quality_score")
        try:
            quality_score = max(0, min(100, int(float(quality_score))))
        except Exception:
            quality_score = self._deterministic_quality_score(profile)

        summary = self._clip_text(parsed.get("summary"), 220) or self._deterministic_quality_summary(profile)

        return {
            "ok": True,
            "source": "gemini",
            "cached": False,
            "quality_score": quality_score,
            "summary": summary,
            "bullets": bullets[:3] or self._quality_bullets(profile),
            "risks": risks[:3] or self._quality_risks(profile),
            "recommendations": recommendations[:3] or self._quality_recommendations(profile),
            "flagged_regions": flagged_regions[:3] or self._quality_flagged_regions(profile),
        }

    def _deterministic_quality_fallback(
        self,
        profile: Dict[str, Any],
        cache_key: Optional[str] = None,
        reason: str = "fallback",
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        if cache_key is None:
            cache_key = self._quality_cache_key(profile)

        result = {
            "ok": False,
            "source": "fallback",
            "cached": False,
            "quality_score": self._deterministic_quality_score(profile),
            "summary": self._deterministic_quality_summary(profile),
            "bullets": self._quality_bullets(profile),
            "risks": self._quality_risks(profile),
            "recommendations": self._quality_recommendations(profile),
            "flagged_regions": self._quality_flagged_regions(profile),
            "reason_code": reason,
            "error": self._clip_text(error_message, 220) if error_message else None,
            "cache_key": cache_key,
            "model": self.model,
        }
        self._store_cache(cache_key, result)
        return result

    def _normalize_quality_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            "total_rows": int(profile.get("total_rows") or 0),
            "total_columns": int(profile.get("total_columns") or 0),
            "missing_values": int(profile.get("missing_values") or 0),
            "missing_pct": round(float(profile.get("missing_pct") or 0.0), 2),
            "invalid_pan_count": int(profile.get("invalid_pan_count") or 0),
            "invalid_gstin_count": int(profile.get("invalid_gstin_count") or 0),
            "probable_duplicate_density": round(float(profile.get("probable_duplicate_density") or 0.0), 2),
            "suspicious_regions": [str(item) for item in (profile.get("suspicious_regions") or [])][:3],
            "top_missing_fields": [str(item) for item in (profile.get("top_missing_fields") or [])][:3],
            "district_counts": profile.get("district_counts") or {},
            "status_counts": profile.get("status_counts") or {},
            "state_counts": profile.get("state_counts") or {},
            "high_confidence_pairs": int(profile.get("high_confidence_pairs") or 0),
            "needs_review_pairs": int(profile.get("needs_review_pairs") or 0),
        }
        return normalized

    def _deterministic_quality_score(self, profile: Dict[str, Any]) -> int:
        rows = max(1, int(profile.get("total_rows") or 0))
        missing_pct = float(profile.get("missing_pct") or 0.0)
        invalid_pan_count = int(profile.get("invalid_pan_count") or 0)
        invalid_gstin_count = int(profile.get("invalid_gstin_count") or 0)
        duplicate_density = float(profile.get("probable_duplicate_density") or 0.0)

        penalty = min(40.0, missing_pct * 0.4)
        penalty += min(20.0, (invalid_pan_count / rows) * 100.0 * 0.15)
        penalty += min(20.0, (invalid_gstin_count / rows) * 100.0 * 0.15)
        penalty += min(20.0, duplicate_density * 0.5)
        return int(max(0, min(100, 100 - penalty)))

    def _deterministic_quality_summary(self, profile: Dict[str, Any]) -> str:
        score = self._deterministic_quality_score(profile)
        total_rows = int(profile.get("total_rows") or 0)
        missing_pct = float(profile.get("missing_pct") or 0.0)
        invalid_pan_count = int(profile.get("invalid_pan_count") or 0)
        invalid_gstin_count = int(profile.get("invalid_gstin_count") or 0)
        return (
            f"Quality score {score}/100 for {total_rows:,} rows. "
            f"Missing data {missing_pct:.1f}%, invalid PAN {invalid_pan_count:,}, invalid GSTIN {invalid_gstin_count:,}."
        )

    def _quality_bullets(self, profile: Dict[str, Any]) -> list[str]:
        return [
            f"Rows analyzed: {int(profile.get('total_rows') or 0):,}.",
            f"Missing fields: {float(profile.get('missing_pct') or 0.0):.1f}%.",
            f"Probable duplicate density: {float(profile.get('probable_duplicate_density') or 0.0):.1f}%.",
        ]

    def _quality_risks(self, profile: Dict[str, Any]) -> list[str]:
        risks = []
        if int(profile.get("invalid_pan_count") or 0) > 0:
            risks.append("PAN validation errors may reduce match accuracy.")
        if int(profile.get("invalid_gstin_count") or 0) > 0:
            risks.append("GSTIN validation errors may hide duplicate entities.")
        if float(profile.get("missing_pct") or 0.0) > 10.0:
            risks.append("High missing-value rate may weaken deterministic matching.")
        if not risks:
            risks.append("No major structural risks detected from aggregate metrics.")
        return risks[:3]

    def _quality_recommendations(self, profile: Dict[str, Any]) -> list[str]:
        recs = []
        if int(profile.get("invalid_pan_count") or 0) > 0:
            recs.append("Review PAN formatting and source-system validation.")
        if int(profile.get("invalid_gstin_count") or 0) > 0:
            recs.append("Normalize GSTIN capture before re-uploading batches.")
        if float(profile.get("missing_pct") or 0.0) > 10.0:
            recs.append("Fill key fields before relying on auto-merge decisions.")
        if not recs:
            recs.append("Proceed with deterministic matching and monitor review queue.")
        return recs[:3]

    def _quality_flagged_regions(self, profile: Dict[str, Any]) -> list[str]:
        regions = [str(item) for item in (profile.get("suspicious_regions") or []) if str(item).strip()]
        if regions:
            return regions[:3]
        state_counts = profile.get("state_counts") or {}
        if isinstance(state_counts, dict) and state_counts:
            top_state = max(state_counts.items(), key=lambda item: item[1])[0]
            return [str(top_state)]
        return []

    def _quality_cache_key(self, profile: Dict[str, Any]) -> str:
        payload = {
            "kind": "quality",
            "profile": profile,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return digest

    def _call_gemini(
        self,
        payload: Dict[str, Any],
        match: MatchResult,
        record1: pd.Series,
        record2: pd.Series,
    ) -> Dict[str, Any]:
        cache_key = self._cache_key(match, record1, record2)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error_message: Optional[str] = None
        transient_codes = {429, 500, 502, 503, 504}

        for attempt in range(2):
            self._throttle()
            try:
                with urlrequest.urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
            except urlerror.HTTPError as exc:
                last_error_message = self._extract_http_error(exc)
                if exc.code in transient_codes and attempt == 0:
                    time.sleep(1.0 + attempt)
                    continue
                return self._deterministic_fallback(
                    match,
                    record1,
                    record2,
                    reason=f"http_{exc.code}",
                    cache_key=cache_key,
                    error_message=last_error_message,
                )
            except (urlerror.URLError, TimeoutError, OSError) as exc:
                last_error_message = str(exc)
                if attempt == 0:
                    time.sleep(1.0 + attempt)
                    continue
                return self._deterministic_fallback(
                    match,
                    record1,
                    record2,
                    reason="request_failed",
                    cache_key=cache_key,
                    error_message=last_error_message,
                )
            except Exception as exc:
                return self._deterministic_fallback(
                    match,
                    record1,
                    record2,
                    reason="request_failed",
                    cache_key=cache_key,
                    error_message=str(exc),
                )

            parsed = self._parse_response(raw)
            if parsed is None:
                last_error_message = "Gemini returned an invalid or empty JSON payload"
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                return self._deterministic_fallback(
                    match,
                    record1,
                    record2,
                    reason="invalid_json",
                    cache_key=cache_key,
                    error_message=last_error_message,
                )

            normalized = self._normalize_response(parsed, match, record1, record2)
            normalized["source"] = "gemini"
            normalized["cached"] = False
            normalized["cache_key"] = cache_key
            normalized["model"] = self.model
            return normalized

        return self._deterministic_fallback(
            match,
            record1,
            record2,
            reason="request_failed",
            cache_key=cache_key,
            error_message=last_error_message or "Gemini request failed",
        )

    def _parse_response(self, raw: str) -> Optional[Dict[str, Any]]:
        if not raw:
            return None

        try:
            data = json.loads(raw)
        except Exception:
            return None

        candidates = data.get("candidates") or []
        if not candidates:
            return None

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        if not parts:
            return None

        text = parts[0].get("text")
        if not text:
            return None

        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

    def _normalize_response(
        self,
        parsed: Dict[str, Any],
        match: MatchResult,
        record1: pd.Series,
        record2: pd.Series,
    ) -> Dict[str, Any]:
        bullets = parsed.get("bullets") or []
        evidence = parsed.get("evidence") or []
        recommendation = str(parsed.get("recommendation") or "").strip() or "Unknown"
        confidence_summary = self._clip_text(parsed.get("confidence_summary"), 220) or self._default_confidence_summary(match)
        uncertainty = self._clip_text(parsed.get("uncertainty"), 220) or self._default_uncertainty(match)

        bullets = [self._clip_text(item, 180) for item in bullets if self._clip_text(item, 180)]
        evidence = [self._clip_text(item, 60) for item in evidence if self._clip_text(item, 60)]

        if len(bullets) > 3:
            bullets = bullets[:3]
        if len(evidence) > 3:
            evidence = evidence[:3]

        if recommendation.lower() not in {"merge", "review", "keepseparate", "unknown"}:
            recommendation = self._default_recommendation(match)

        return {
            "ok": True,
            "source": "gemini",
            "cached": False,
            "recommendation": recommendation,
            "confidence_summary": confidence_summary,
            "uncertainty": uncertainty,
            "bullets": bullets or self._fallback_bullets(match, record1, record2),
            "evidence": evidence or self._fallback_evidence(match),
            "match_score": round(float(match.score or 0.0), 1),
            "tier": match.tier,
            "decision": match.decision,
        }

    # ------------------------------------------------------------------
    # Fallbacks and cache
    # ------------------------------------------------------------------

    def _deterministic_fallback(
        self,
        match: MatchResult,
        record1: pd.Series,
        record2: pd.Series,
        reason: str,
        cache_key: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        if cache_key is None:
            cache_key = self._cache_key(match, record1, record2)

        recommendation = self._default_recommendation(match)
        bullets = self._fallback_bullets(match, record1, record2)
        evidence = self._fallback_evidence(match)

        result = {
            "ok": False,
            "source": "fallback",
            "cached": False,
            "recommendation": recommendation,
            "confidence_summary": self._default_confidence_summary(match),
            "uncertainty": self._default_uncertainty(match, error_message),
            "bullets": bullets,
            "evidence": evidence,
            "match_score": round(float(match.score or 0.0), 1),
            "tier": match.tier,
            "decision": match.decision,
            "reason_code": reason,
            "cache_key": cache_key,
            "model": self.model,
        }
        self._store_cache(cache_key, result)
        return result

    def _fallback_bullets(
        self,
        match: MatchResult,
        record1: pd.Series,
        record2: pd.Series,
    ) -> list[str]:
        bullets = []
        bullets.append(f"Score is {float(match.score or 0.0):.1f}% and decision is {match.decision}.")
        bullets.append(self._pair_field_summary(record1, record2))
        bullets.append(self._default_recommendation_sentence(match))
        return bullets[:3]

    def _fallback_evidence(self, match: MatchResult) -> list[str]:
        fields = list(match.matched_fields or [])
        if not fields:
            fields = ["business_name"]
        return fields[:3]

    def _default_confidence_summary(self, match: MatchResult) -> str:
        return f"Deterministic score {float(match.score or 0.0):.1f}% with {match.tier} classification."

    def _default_uncertainty(self, match: MatchResult, error_message: Optional[str] = None) -> str:
        if error_message:
            return self._clip_text(error_message, 220)
        if match.decision == "NeedsReview":
            return "The matcher considered this borderline and flagged it for human review."
        return "No material uncertainty detected."

    def _default_recommendation(self, match: MatchResult) -> str:
        if match.decision == "AutoMerge":
            return "Merge"
        if match.decision == "NeedsReview":
            return "Review"
        return "KeepSeparate"

    def _default_recommendation_sentence(self, match: MatchResult) -> str:
        recommendation = self._default_recommendation(match)
        if recommendation == "Merge":
            return "Advisory recommendation: merge if no conflicting identifiers are found."
        if recommendation == "Review":
            return "Advisory recommendation: keep under review before merging."
        return "Advisory recommendation: keep separate unless new evidence appears."

    def _pair_field_summary(self, record1: pd.Series, record2: pd.Series) -> str:
        name1 = self._clip_text(self._series_value(record1, "business_name"), 60) or "unknown"
        name2 = self._clip_text(self._series_value(record2, "business_name"), 60) or "unknown"
        district1 = self._clip_text(self._series_value(record1, "district"), 30) or "unknown"
        district2 = self._clip_text(self._series_value(record2, "district"), 30) or "unknown"
        return f"Names: {name1} vs {name2}; districts: {district1} vs {district2}."

    def _compact_record(self, record: pd.Series) -> Dict[str, Any]:
        return {
            "business_name": self._clip_text(self._series_value(record, "business_name"), 90),
            "cleaned_name": self._clip_text(self._series_value(record, "cleaned_name"), 90),
            "pan": self._clip_text(self._series_value(record, "pan"), 20),
            "gstin": self._clip_text(self._series_value(record, "gstin"), 24),
            "district": self._clip_text(self._series_value(record, "district"), 40),
            "state": self._clip_text(self._series_value(record, "state"), 40),
            "pincode": self._clip_text(self._series_value(record, "pincode"), 12),
            "business_status": self._clip_text(self._series_value(record, "business_status"), 20),
            "match_tier": self._clip_text(self._series_value(record, "match_tier"), 20),
            "match_decision": self._clip_text(self._series_value(record, "match_decision"), 20),
            "match_confidence": self._series_value(record, "match_confidence"),
        }

    def _series_value(self, record: pd.Series, key: str) -> Any:
        try:
            value = record.get(key)
        except Exception:
            return None
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime().isoformat()
        return value

    def _cache_key(self, match: MatchResult, record1: pd.Series, record2: pd.Series) -> str:
        payload = {
            "match": {
                "record1_id": match.record1_id,
                "record2_id": match.record2_id,
                "score": round(float(match.score or 0.0), 1),
                "tier": match.tier,
                "decision": match.decision,
                "matched_fields": list(match.matched_fields or []),
                "reason": self._clip_text(match.reason, 180),
            },
            "record1": self._compact_record(record1),
            "record2": self._compact_record(record2),
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return digest

    def _store_cache(self, key: str, result: Dict[str, Any]) -> None:
        if not key:
            return
        entry = {
            "created_at": time.time(),
            "result": result,
        }
        with self._lock:
            self._memory_cache[key] = entry
            self._save_cache_file()

    def _load_cache_file(self) -> Dict[str, Dict[str, Any]]:
        if not self.cache_path.exists():
            return {}

        try:
            with self.cache_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            return {}

        if not isinstance(data, dict):
            return {}

        return {str(key): value for key, value in data.items() if isinstance(value, dict)}

    def _save_cache_file(self) -> None:
        try:
            tmp_path = self.cache_path.with_suffix(".tmp")
            with tmp_path.open("w", encoding="utf-8") as fh:
                json.dump(self._memory_cache, fh, ensure_ascii=True)
            tmp_path.replace(self.cache_path)
        except Exception as exc:
            logger.debug("AI cache save skipped: %s", exc)

    def _is_expired(self, cached: Dict[str, Any]) -> bool:
        created_at = cached.get("created_at")
        if not created_at:
            return True
        try:
            return (time.time() - float(created_at)) > self.cache_ttl_seconds
        except Exception:
            return True

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_call_at
        if elapsed < self.min_call_gap_seconds:
            time.sleep(self.min_call_gap_seconds - elapsed)
        self._last_call_at = time.time()

    def _extract_http_error(self, exc: urlerror.HTTPError) -> str:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        if not raw:
            return f"Gemini request failed with HTTP {exc.code}"

        try:
            data = json.loads(raw)
            message = data.get("error", {}).get("message")
            status = data.get("error", {}).get("status")
            if message and status:
                return f"{status}: {message}"
            if message:
                return message
        except Exception:
            pass
        return raw[:240]

    def _clip_text(self, value: Any, max_len: int) -> Optional[str]:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        text = str(value).strip()
        if not text:
            return None
        if len(text) > max_len:
            return text[: max_len - 1].rstrip() + "…"
        return text


__all__ = ["AIReviewService"]
