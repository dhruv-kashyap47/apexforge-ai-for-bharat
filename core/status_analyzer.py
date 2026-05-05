"""Business status determination module.

This version is designed for production-style data pipelines:
- safe handling of missing or invalid dates
- predictable status categories
- dataframe-friendly output
- summary statistics for dashboards and reports

Status logic:
- Active: last activity within ACTIVE_THRESHOLD months
- Dormant: last activity between ACTIVE_THRESHOLD and DORMANT_THRESHOLD months
- Closed: no activity beyond DORMANT_THRESHOLD months, or no usable activity info
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Any

import pandas as pd


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StatusResult:
    status: str
    reason: str
    days_inactive: Optional[int]
    months_inactive: Optional[float]


class StatusAnalyzer:
    """Analyzes business activity status based on dates."""

    # Status thresholds (in months)
    ACTIVE_THRESHOLD = 12
    DORMANT_THRESHOLD = 18

    # Status codes
    STATUS_ACTIVE = "Active"
    STATUS_DORMANT = "Dormant"
    STATUS_CLOSED = "Closed"

    def __init__(self, reference_date: Optional[datetime] = None):
        """Initialize status analyzer."""
        self.reference_date = self._coerce_datetime(reference_date) if reference_date else datetime.now()
        self.status_stats = {
            "active": 0,
            "dormant": 0,
            "closed": 0,
        }

    def _coerce_datetime(self, value: Any) -> Optional[datetime]:
        """Convert input into datetime if possible."""
        if value is None or pd.isna(value):
            return None
        if isinstance(value, datetime):
            return value
        try:
            ts = pd.to_datetime(value, errors="coerce", dayfirst=True)
            if pd.isna(ts):
                return None
            return ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        except Exception:
            return None

    def determine_status(
        self,
        last_activity_date: Optional[datetime],
        registration_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Determine business status based on activity and registration dates."""
        last_activity_date = self._coerce_datetime(last_activity_date)
        registration_date = self._coerce_datetime(registration_date)

        # If we do not have last activity, fall back to registration date.
        if last_activity_date is None:
            if registration_date is not None:
                months_since_reg = self._months_between(registration_date, self.reference_date)
                days_since_reg = max(0, (self.reference_date - registration_date).days)

                if months_since_reg > self.DORMANT_THRESHOLD:
                    return {
                        "status": self.STATUS_CLOSED,
                        "reason": f"No activity recorded since registration ({months_since_reg:.1f} months ago)",
                        "days_inactive": days_since_reg,
                        "months_inactive": months_since_reg,
                    }

                return {
                    "status": self.STATUS_DORMANT,
                    "reason": f"No activity recorded, registered {months_since_reg:.1f} months ago",
                    "days_inactive": days_since_reg,
                    "months_inactive": months_since_reg,
                }

            return {
                "status": self.STATUS_CLOSED,
                "reason": "No activity or registration information available",
                "days_inactive": None,
                "months_inactive": None,
            }

        # If activity date exists, base status on inactivity duration.
        months_inactive = self._months_between(last_activity_date, self.reference_date)
        days_inactive = max(0, (self.reference_date - last_activity_date).days)

        if months_inactive <= self.ACTIVE_THRESHOLD:
            status = self.STATUS_ACTIVE
            reason = f"Activity recorded within last {self.ACTIVE_THRESHOLD} months"
        elif months_inactive <= self.DORMANT_THRESHOLD:
            status = self.STATUS_DORMANT
            reason = (
                f"No activity for {months_inactive:.1f} months "
                f"(between {self.ACTIVE_THRESHOLD}-{self.DORMANT_THRESHOLD} months)"
            )
        else:
            status = self.STATUS_CLOSED
            reason = f"No activity for {months_inactive:.1f} months (exceeds {self.DORMANT_THRESHOLD} months threshold)"

        return {
            "status": status,
            "reason": reason,
            "days_inactive": days_inactive,
            "months_inactive": months_inactive,
        }

    def _months_between(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate months between two dates."""
        if start_date is None or end_date is None:
            return 0.0
        days = (end_date - start_date).days
        return max(0.0, days / 30.44)  # average days per month

    def analyze_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze status for all records in a dataframe."""
        if df is None:
            raise ValueError("df cannot be None")

        logger.info("Analyzing business status for %s records", len(df))
        self.status_stats = {"active": 0, "dormant": 0, "closed": 0}

        df_result = df.copy()

        # Ensure output columns exist.
        if "business_status" not in df_result.columns:
            df_result["business_status"] = self.STATUS_CLOSED
        if "status_reason" not in df_result.columns:
            df_result["status_reason"] = ""
        if "days_inactive" not in df_result.columns:
            df_result["days_inactive"] = None
        if "months_inactive" not in df_result.columns:
            df_result["months_inactive"] = None

        for idx, row in df_result.iterrows():
            last_activity = row.get("last_activity_date")
            registration_date = row.get("registration_date")

            status_info = self.determine_status(last_activity, registration_date)

            df_result.at[idx, "business_status"] = status_info["status"]
            df_result.at[idx, "status_reason"] = status_info["reason"]
            df_result.at[idx, "days_inactive"] = status_info["days_inactive"]
            df_result.at[idx, "months_inactive"] = status_info["months_inactive"]

            status_lower = status_info["status"].lower()
            if status_lower in self.status_stats:
                self.status_stats[status_lower] += 1

        logger.info("Status analysis complete: %s", self.status_stats)
        return df_result

    def get_summary(self) -> Dict[str, Any]:
        """Get status summary statistics."""
        total = sum(self.status_stats.values())
        if total == 0:
            return {
                "counts": self.status_stats.copy(),
                "percentages": {"active": 0.0, "dormant": 0.0, "closed": 0.0},
                "total": 0,
            }

        return {
            "counts": self.status_stats.copy(),
            "percentages": {k: (v / total * 100.0) for k, v in self.status_stats.items()},
            "total": total,
        }

    def get_status_color(self, status: str) -> str:
        """Get color code for status (for visualization)."""
        colors = {
            self.STATUS_ACTIVE: "#28a745",   # Green
            self.STATUS_DORMANT: "#ffc107",  # Yellow/Orange
            self.STATUS_CLOSED: "#dc3545",   # Red
        }
        return colors.get(status, "#6c757d")

    def get_status_badge_class(self, status: str) -> str:
        """Get badge class for status (for UI)."""
        classes = {
            self.STATUS_ACTIVE: "success",
            self.STATUS_DORMANT: "warning",
            self.STATUS_CLOSED: "danger",
        }
        return classes.get(status, "secondary")

    def reset_stats(self) -> None:
        """Reset internal counters."""
        self.status_stats = {"active": 0, "dormant": 0, "closed": 0}


__all__ = ["StatusAnalyzer", "StatusResult"]
