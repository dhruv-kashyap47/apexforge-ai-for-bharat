import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import pandas as pd

try:
    import gravis as gv
except Exception:
    gv = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MatchEdge:
    record1_id: int
    record2_id: int
    score: float = 0.0
    reason: str = ""


_GRAPH_KWARGS = dict(
    graph_height=780,
    background_color="#07111f",
    node_label_color="#e5eefb",
    node_label_size=11,
    edge_label_color="#64748b",
    show_details=True,
    show_menu=True,
    zoom_factor=0.92,
    use_node_size_normalization=True,
    node_size_normalization_min=12,
    node_size_normalization_max=42,
    use_edge_size_normalization=True,
    edge_size_normalization_min=1,
    edge_size_normalization_max=5,
    gravitational_constant=-10000,
    spring_length=150,
    spring_constant=0.04,
    damping=0.86,
)


class VisualizationService:
    """
    Epic-grade graph visualizer for UBID / entity-resolution workflows.

    What this version improves:
    - deterministic color system for clusters
    - much safer data handling
    - better graph density control
    - node sizing based on confidence + connectivity
    - stronger labels/tooltips
    - fallback-safe graph construction
    - cleaner app integration
    """

    COLORS = {
        "tier1": "#00ff87",
        "tier2": "#3b82f6",
        "tier3": "#f59e0b",
        "new": "#a855f7",
        "active": "#00ff87",
        "dormant": "#f59e0b",
        "closed": "#ef4444",
        "default": "#64748b",
        "master": "#ffffff",
        "link": "#1e3a5f",
        "missing": "#94a3b8",
        "shadow": "#0f172a",
    }

    def __init__(self) -> None:
        self.logger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_match_network(
        self,
        df: pd.DataFrame,
        ubid_assignments: Dict[int, Dict],
        matches: List,
        height: str = "780px",
        layout: str = "spring",
    ):
        """Render the full resolution network."""
        if gv is None:
            self.logger.warning("gravis is not installed; cannot render graph.")
            return None
        if df is None or df.empty:
            return None

        G = nx.Graph()
        ubid_assignments = ubid_assignments or {}
        matches = matches or []

        # Build UBID groups first so color assignment stays deterministic.
        ubid_groups: Dict[str, List[int]] = {}
        for idx, a in ubid_assignments.items():
            ubid = self._safe_str(a.get("ubid"), default="UNK")
            ubid_groups.setdefault(ubid, []).append(idx)

        group_colors = self._generate_group_colors(ubid_groups)
        node_degrees: Dict[int, int] = {}

        for m in matches:
            r1 = getattr(m, "record1_id", None)
            r2 = getattr(m, "record2_id", None)
            if r1 is None or r2 is None:
                continue
            node_degrees[r1] = node_degrees.get(r1, 0) + 1
            node_degrees[r2] = node_degrees.get(r2, 0) + 1

        # --- Nodes ---
        for idx in range(len(df)):
            row = df.iloc[idx]
            a = ubid_assignments.get(idx, {}) or {}

            tier = self._normalize_text(a.get("tier", "new"))
            ubid = self._safe_str(a.get("ubid"), default="UNK")
            is_master = bool(a.get("is_master", False))
            confidence = self._safe_float(a.get("confidence", 0.0))
            degree = float(node_degrees.get(idx, 0))

            status = self._normalize_text(row.get("business_status", ""))
            color = self.COLORS["master"] if is_master else self._resolve_node_color(tier, ubid, group_colors)
            border_color = "#ffffff" if is_master else color
            size = 32 if is_master else self._node_size(confidence=confidence, degree=degree)

            label = self._truncate(self._safe_str(row.get("business_name"), default=str(idx)), 30)
            hover = self._tooltip(row=row, a=a, idx=idx, tier=tier, status=status, degree=degree)

            G.add_node(
                idx,
                label=label,
                color=color,
                size=size,
                hover=hover,
                border_color=border_color,
                border_size=2 if is_master else 1,
            )

        # --- Match edges ---
        added_edges: set[Tuple[int, int]] = set()
        for m in matches:
            r1 = getattr(m, "record1_id", None)
            r2 = getattr(m, "record2_id", None)
            if r1 is None or r2 is None:
                continue
            if r1 not in G.nodes or r2 not in G.nodes:
                continue

            key = tuple(sorted((int(r1), int(r2))))
            if key in added_edges:
                continue

            score = self._safe_float(getattr(m, "score", 0.0))
            ec, ew, dashed = self._edge_style(score)

            G.add_edge(
                r1,
                r2,
                color=ec,
                size=ew,
                hover=self._safe_str(getattr(m, "reason", ""), default=f"Match score: {score:.2f}"),
                label="",
                dashed=dashed,
            )
            added_edges.add(key)

        # --- UBID grouping edges ---
        for ubid, indices in ubid_groups.items():
            if len(indices) <= 1:
                continue
            root = indices[0]
            for idx in indices[1:]:
                if root not in G.nodes or idx not in G.nodes:
                    continue
                key = tuple(sorted((int(root), int(idx))))
                if key in added_edges:
                    continue
                G.add_edge(
                    root,
                    idx,
                    color=self.COLORS["link"],
                    size=0.8,
                    hover=f"Same UBID: {ubid}",
                    label="",
                    dashed=True,
                )
                added_edges.add(key)

        kwargs = dict(_GRAPH_KWARGS)
        kwargs["graph_height"] = self._parse_height(height, fallback=780)
        kwargs.update(self._layout_kwargs(layout))
        return gv.d3(G, **kwargs)

    def create_ubid_cluster_view(self, ubid: str, df: pd.DataFrame, matches: List):
        """Focused cluster view for a single UBID group."""
        if gv is None:
            self.logger.warning("gravis is not installed; cannot render graph.")
            return None
        if df is None or df.empty:
            return None

        G = nx.Graph()
        matches = matches or []
        cluster_nodes = set(df.index.tolist())

        for idx, row in df.iterrows():
            status = self._normalize_text(row.get("business_status", ""))
            color = self.COLORS.get(status, self.COLORS["default"])
            G.add_node(
                idx,
                label=self._truncate(self._safe_str(row.get("business_name"), default=str(idx)), 26),
                color=color,
                size=18,
                hover=self._cluster_tooltip(row=row, ubid=ubid, status=status),
                border_color=color,
                border_size=1,
            )

        added_edges: set[Tuple[int, int]] = set()
        for m in matches:
            r1 = getattr(m, "record1_id", None)
            r2 = getattr(m, "record2_id", None)
            if r1 not in cluster_nodes or r2 not in cluster_nodes:
                continue
            key = tuple(sorted((int(r1), int(r2))))
            if key in added_edges:
                continue
            score = self._safe_float(getattr(m, "score", 0.0))
            ec, ew, dashed = self._edge_style(score)
            G.add_edge(
                r1,
                r2,
                color=ec,
                size=ew,
                hover=self._safe_str(getattr(m, "reason", ""), default=f"Match score: {score:.2f}"),
                label="",
                dashed=dashed,
            )
            added_edges.add(key)

        kwargs = dict(_GRAPH_KWARGS)
        kwargs["graph_height"] = 560
        kwargs["spring_length"] = 120
        kwargs["gravitational_constant"] = -6500
        return gv.d3(G, **kwargs)

    # ------------------------------------------------------------------
    # Analytics helpers
    # ------------------------------------------------------------------

    def create_status_distribution_chart(self, df: pd.DataFrame) -> Dict:
        if df is None or df.empty or "business_status" not in df.columns:
            return {}
        counts = (
            df["business_status"]
            .fillna("unknown")
            .astype(str)
            .str.lower()
            .value_counts()
            .to_dict()
        )
        return {"labels": list(counts.keys()), "data": list(counts.values())}

    def create_confidence_distribution(self, assignments: Dict[int, Dict]) -> Dict:
        buckets = {"90+": 0, "70-89": 0, "50-69": 0, "<50": 0}
        seen: Dict[str, float] = {}

        for a in (assignments or {}).values():
            ubid = self._safe_str(a.get("ubid"), default="")
            if ubid and ubid not in seen:
                seen[ubid] = self._safe_float(a.get("confidence", 0.0))

        for c in seen.values():
            if c >= 90:
                buckets["90+"] += 1
            elif c >= 70:
                buckets["70-89"] += 1
            elif c >= 50:
                buckets["50-69"] += 1
            else:
                buckets["<50"] += 1

        return {"labels": list(buckets.keys()), "data": list(buckets.values())}

    def create_cluster_summary(self, df: pd.DataFrame, ubid_assignments: Dict[int, Dict]) -> Dict[str, Any]:
        """Useful for dashboard cards and KPI panels."""
        if df is None or df.empty:
            return {}

        total = len(df)
        assigned = len({self._safe_str(v.get("ubid"), default="") for v in (ubid_assignments or {}).values() if v.get("ubid")})
        masters = sum(1 for v in (ubid_assignments or {}).values() if bool(v.get("is_master", False)))

        return {
            "total_records": total,
            "assigned_records": len(ubid_assignments or {}),
            "unique_ubids": assigned,
            "master_records": masters,
            "assignment_rate": round((len(ubid_assignments or {}) / total) * 100, 2) if total else 0.0,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _layout_kwargs(self, layout: str) -> Dict[str, Any]:
        layout = self._normalize_text(layout)
        if layout == "force":
            return {"spring_length": 130, "gravitational_constant": -12000, "damping": 0.88}
        if layout == "dense":
            return {"spring_length": 95, "gravitational_constant": -7000, "damping": 0.84}
        if layout == "spread":
            return {"spring_length": 180, "gravitational_constant": -9500, "damping": 0.89}
        return {}

    def _resolve_node_color(self, tier: str, ubid: str, group_colors: Dict[str, str]) -> str:
        tier = self._normalize_text(tier)
        if tier == "tier1":
            return self.COLORS["tier1"]
        if tier == "tier2":
            return self.COLORS["tier2"]
        if tier == "tier3":
            return self.COLORS["tier3"]
        return group_colors.get(ubid, self.COLORS["new"])

    def _edge_style(self, score: float):
        score = self._safe_float(score)
        if score >= 90:
            return self.COLORS["tier1"], 4, False
        if score >= 75:
            return self.COLORS["tier1"], 3, False
        if score >= 60:
            return self.COLORS["tier2"], 2.5, False
        if score >= 45:
            return self.COLORS["tier2"], 2, True
        return self.COLORS["tier3"], 1, True

    def _tooltip(self, row: pd.Series, a: Dict, idx: int, tier: str, status: str, degree: float) -> str:
        name = self._safe_str(row.get("business_name"), default=f"Record {idx}")
        ubid = self._safe_str(a.get("ubid"), default="UNK")
        confidence = self._safe_float(a.get("confidence", 0.0))
        source = self._safe_str(row.get("source"), default="unknown")
        city = self._safe_str(row.get("city"), default="")
        state = self._safe_str(row.get("state"), default="")

        bits = [
            f"{name}",
            f"UBID: {ubid}",
            f"Tier: {tier or 'new'}",
            f"Confidence: {confidence:.2f}",
            f"Status: {status or 'unknown'}",
            f"Degree: {int(degree)}",
        ]

        loc = ", ".join([x for x in [city, state] if x])
        if loc:
            bits.append(f"Location: {loc}")
        if source:
            bits.append(f"Source: {source}")

        return " | ".join(bits)

    def _cluster_tooltip(self, row: pd.Series, ubid: str, status: str) -> str:
        name = self._safe_str(row.get("business_name"), default="Unnamed")
        return f"{name} | UBID: {ubid} | Status: {status or 'unknown'}"

    def _generate_group_colors(self, groups: Dict[str, List[int]]) -> Dict[str, str]:
        colors: Dict[str, str] = {}
        for i, k in enumerate(groups.keys()):
            hue = (i * 137.50776405003785) % 360
            colors[k] = self._hsl_to_hex(hue, 72, 52)
        return colors

    def _node_size(self, confidence: float = 0.0, degree: float = 0.0) -> int:
        confidence = max(0.0, min(100.0, confidence))
        degree = max(0.0, degree)
        base = 14 + (confidence / 100.0) * 10
        boost = min(10.0, math.log1p(degree) * 2.4)
        return int(round(base + boost))

    def _normalize_text(self, value: Any) -> str:
        return self._safe_str(value, default="").strip().lower()

    def _safe_str(self, value: Any, default: str = "") -> str:
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except Exception:
            pass
        text = str(value).strip()
        return text if text else default

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            if isinstance(value, str) and not value.strip():
                return default
            out = float(value)
            if math.isnan(out) or math.isinf(out):
                return default
            return out
        except Exception:
            return default

    def _truncate(self, text: str, limit: int) -> str:
        text = text or ""
        return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"

    def _parse_height(self, height: Any, fallback: int = 780) -> int:
        if isinstance(height, int):
            return height
        if isinstance(height, str):
            try:
                return int(height.lower().replace("px", "").strip())
            except Exception:
                return fallback
        return fallback

    def _hsl_to_hex(self, h: float, s: float, l: float) -> str:
        s /= 100.0
        l /= 100.0

        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60.0) % 2 - 1))
        m = l - c / 2

        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        r, g, b = (int((v + m) * 255) for v in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"
