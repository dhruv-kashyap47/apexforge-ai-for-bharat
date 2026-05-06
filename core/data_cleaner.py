"""Data cleaning and normalization module for business records.

Designed to work cleanly with the matching engine and UBID generator:
- cleans business names, PAN, GSTIN, addresses, pincodes
- normalizes state/district fields
- parses date columns safely
- exposes simple cleaning stats
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

try:
    from phonetics import metaphone as _metaphone
except Exception:
    _metaphone = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CleaningStats:
    total_records: int = 0
    cleaned_names: int = 0
    cleaned_pans: int = 0
    cleaned_gstins: int = 0
    cleaned_addresses: int = 0
    normalized_pincodes: int = 0
    normalized_states: int = 0
    normalized_districts: int = 0
    parsed_dates: int = 0
    invalid_pans: int = 0
    invalid_gstins: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "total_records": self.total_records,
            "cleaned_names": self.cleaned_names,
            "cleaned_pans": self.cleaned_pans,
            "cleaned_gstins": self.cleaned_gstins,
            "cleaned_addresses": self.cleaned_addresses,
            "normalized_pincodes": self.normalized_pincodes,
            "normalized_states": self.normalized_states,
            "normalized_districts": self.normalized_districts,
            "parsed_dates": self.parsed_dates,
            "invalid_pans": self.invalid_pans,
            "invalid_gstins": self.invalid_gstins,
        }


class DataCleaner:
    """Cleans and normalizes business data for matching and UBID assignment."""

    BUSINESS_SUFFIXES = {
        "ltd", "limited", "pvt", "private", "public", "corp", "corporation",
        "inc", "incorporated", "llc", "llp", "co", "company", "enterprise",
        "enterprises", "solutions", "services", "group", "holdings", "trading",
        "industries", "industry", "international", "global", "india",
        "technologies", "tech", "consultancy", "consultants", "associates",
        "partners", "manufacturing", "exports", "import", "impex",
    }

    STATE_CODES = {
        "andhra pradesh": "AP",
        "arunachal pradesh": "AR",
        "assam": "AS",
        "bihar": "BR",
        "chhattisgarh": "CG",
        "goa": "GA",
        "gujarat": "GJ",
        "haryana": "HR",
        "himachal pradesh": "HP",
        "jharkhand": "JH",
        "karnataka": "KA",
        "kerala": "KL",
        "madhya pradesh": "MP",
        "maharashtra": "MH",
        "manipur": "MN",
        "meghalaya": "ML",
        "mizoram": "MZ",
        "nagaland": "NL",
        "odisha": "OD",
        "orissa": "OD",
        "punjab": "PB",
        "rajasthan": "RJ",
        "sikkim": "SK",
        "tamil nadu": "TN",
        "telangana": "TG",
        "tripura": "TR",
        "uttar pradesh": "UP",
        "uttarakhand": "UK",
        "west bengal": "WB",
        "andaman and nicobar islands": "AN",
        "andaman & nicobar islands": "AN",
        "chandigarh": "CH",
        "dadra and nagar haveli": "DN",
        "dadra and nagar haveli and daman and diu": "DH",
        "daman and diu": "DD",
        "delhi": "DL",
        "new delhi": "DL",
        "jammu and kashmir": "JK",
        "jammu & kashmir": "JK",
        "ladakh": "LA",
        "lakshadweep": "LD",
        "puducherry": "PY",
    }

    STATE_CODE_LOOKUP = {v: v for v in STATE_CODES.values()}

    CATEGORY_CODES = {
        "trading": "TR",
        "manufacturing": "MF",
        "service": "SV",
        "services": "SV",
        "consultancy": "CS",
        "retail": "RT",
        "wholesale": "WS",
        "export": "EX",
        "import": "IM",
        "logistics": "LG",
    }

    DATE_COLUMNS_DEFAULT = ("registration_date", "last_activity_date")

    def __init__(self, keep_original: bool = True):
        self.keep_original = keep_original
        self.stats = CleaningStats()

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize an entire dataframe."""
        if df is None:
            raise ValueError("df cannot be None")

        logger.info("Starting data cleaning for %s records", len(df))
        self.stats = CleaningStats(total_records=len(df))

        df_clean = df.copy()

        if "business_name" in df_clean.columns:
            df_clean["cleaned_name"] = df_clean["business_name"].apply(self.clean_business_name)
            df_clean["name_phonetic"] = df_clean["cleaned_name"].apply(self.generate_phonetic)
            self.stats.cleaned_names = int(df_clean["cleaned_name"].notna().sum())

        if "pan" in df_clean.columns:
            df_clean["cleaned_pan"] = df_clean["pan"].apply(self.clean_pan)
            self.stats.cleaned_pans = int(df_clean["cleaned_pan"].notna().sum())
            self.stats.invalid_pans = int(df_clean["pan"].notna().sum() - df_clean["cleaned_pan"].notna().sum())

        if "gstin" in df_clean.columns:
            df_clean["cleaned_gstin"] = df_clean["gstin"].apply(self.clean_gstin)
            self.stats.cleaned_gstins = int(df_clean["cleaned_gstin"].notna().sum())
            self.stats.invalid_gstins = int(df_clean["gstin"].notna().sum() - df_clean["cleaned_gstin"].notna().sum())

        if "address" in df_clean.columns:
            df_clean["cleaned_address"] = df_clean["address"].apply(self.clean_address)
            self.stats.cleaned_addresses = int(df_clean["cleaned_address"].notna().sum())

        if "pincode" in df_clean.columns:
            df_clean["normalized_pincode"] = df_clean["pincode"].apply(self.normalize_pincode)
            self.stats.normalized_pincodes = int(df_clean["normalized_pincode"].notna().sum())

        if "state" in df_clean.columns:
            df_clean["state_code"] = df_clean["state"].apply(self.get_state_code)
            self.stats.normalized_states = int(df_clean["state_code"].notna().sum())

        if "district" in df_clean.columns:
            df_clean["district_code"] = df_clean["district"].apply(self.get_district_code)
            self.stats.normalized_districts = int(df_clean["district_code"].notna().sum())

        for col in self.DATE_COLUMNS_DEFAULT:
            if col in df_clean.columns:
                df_clean[col] = pd.to_datetime(df_clean[col], errors="coerce", dayfirst=True)
                self.stats.parsed_dates += int(df_clean[col].notna().sum())

        logger.info("Data cleaning completed")
        return df_clean

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value)

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def clean_business_name(self, name: Optional[str]) -> Optional[str]:
        """Clean and normalize business name for matching."""
        if self._is_missing(name):
            return None

        cleaned = str(name).lower()
        cleaned = cleaned.replace("&", " and ")
        cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
        cleaned = self._normalize_spaces(cleaned)

        words = [w for w in cleaned.split() if w not in self.BUSINESS_SUFFIXES]
        cleaned = self._normalize_spaces(" ".join(words))

        return cleaned or None

    def generate_phonetic(self, name: Optional[str]) -> Optional[str]:
        """Generate a phonetic code for fuzzy name matching."""
        if self._is_missing(name):
            return None

        try:
            if _metaphone is None:
                return None
            return _metaphone(str(name))
        except Exception as exc:  # pragma: no cover - safety
            logger.debug("Phonetic generation failed: %s", exc)
            return None

    def clean_pan(self, pan: Optional[str]) -> Optional[str]:
        """Clean and validate PAN number (AAAAA9999A)."""
        if self._is_missing(pan):
            return None

        cleaned = re.sub(r"\s+", "", str(pan)).upper()
        if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", cleaned):
            return cleaned
        return None

    def clean_gstin(self, gstin: Optional[str]) -> Optional[str]:
        """Clean and validate GSTIN number."""
        if self._is_missing(gstin):
            return None

        cleaned = re.sub(r"\s+", "", str(gstin)).upper()
        # GSTIN structure: 2-digit state + PAN + entity + Z + checksum
        if re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", cleaned):
            return cleaned
        return None

    def clean_address(self, address: Optional[str]) -> Optional[str]:
        """Clean and normalize address text."""
        if self._is_missing(address):
            return None

        cleaned = str(address).lower()
        cleaned = cleaned.replace("&", " and ")
        cleaned = re.sub(r"[^a-z0-9\s,/-]", " ", cleaned)
        cleaned = re.sub(r"[,/\\-]", " ", cleaned)
        cleaned = self._normalize_spaces(cleaned)
        return cleaned or None

    def normalize_pincode(self, pincode: Optional[str]) -> Optional[str]:
        """Normalize Indian pincode to exactly 6 digits."""
        if self._is_missing(pincode):
            return None

        digits = re.sub(r"\D", "", str(pincode))
        if len(digits) == 6:
            return digits
        return None

    def get_state_code(self, state: Optional[str]) -> Optional[str]:
        """Return the 2-letter state/UT code."""
        if self._is_missing(state):
            return None

        value = str(state).strip().lower()
        value = value.replace("&", "and")
        value = self._normalize_spaces(value)

        # Direct lookup by full name
        if value in self.STATE_CODES:
            return self.STATE_CODES[value]

        # Already a code?
        upper = value.upper()
        if upper in self.STATE_CODE_LOOKUP:
            return upper

        return None

    def get_district_code(self, district: Optional[str]) -> Optional[str]:
        """Generate a stable 3-character district code."""
        if self._is_missing(district):
            return None

        cleaned = str(district).upper()
        cleaned = re.sub(r"[^A-Z0-9]", "", cleaned)
        if not cleaned:
            return None

        if len(cleaned) >= 3:
            return cleaned[:3]
        return cleaned.ljust(3, "X")

    def get_category_code(self, business_type: Optional[str] = None) -> str:
        """Return a 2-letter business category code."""
        if self._is_missing(business_type):
            return "TR"

        text = str(business_type).lower()
        for key, code in self.CATEGORY_CODES.items():
            if key in text:
                return code

        # Fall back to a sensible two-letter uppercase abbreviation.
        raw = re.sub(r"[^a-z]", "", text)
        return (raw[:2].upper() if raw else "TR")

    def add_missing_columns(self, df: pd.DataFrame, required_columns: Optional[Iterable[str]] = None) -> pd.DataFrame:
        """Ensure downstream-safe columns exist even when input data is sparse."""
        required_columns = required_columns or (
            "cleaned_name",
            "name_phonetic",
            "cleaned_pan",
            "cleaned_gstin",
            "cleaned_address",
            "normalized_pincode",
            "state_code",
            "district_code",
        )

        result = df.copy()
        for col in required_columns:
            if col not in result.columns:
                result[col] = None
        return result

    def get_stats(self) -> Dict[str, int]:
        """Return cleaning statistics."""
        return self.stats.as_dict()

    def reset_stats(self) -> None:
        """Reset internal counters."""
        self.stats = CleaningStats()


__all__ = ["DataCleaner", "CleaningStats"]
