import logging
from typing import Dict, List, Optional, Any

import networkx as nx
import pandas as pd

try:
    import gravis as gv
except Exception:
    gv = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Palantir-esque dark theme constants
_GRAPH_KWARGS = dict(
    graph_height=700,
    background_color="#0a0e1a",
    node_label_color="#e2e8f0",
    node_label_size=11,
    edge_label_color="#64748b",
    show_details=True,
    show_menu=True,
    zoom_factor=0.9,
    use_node_size_normalization=True,
    node_size_normalization_min=12,
    node_size_normalization_max=40,
    use_edge_size_normalization=True,
    edge_size_normalization_min=1,
    edge_size_normalization_max=4,
    gravitational_constant=-8000,
    spring_length=160,
    spring_constant=0.04,
    damping=0.85,
)


class VisualizationService:

    COLORS = {
        "tier1":   "#00ff87",   # neon green  — Palantir "confirmed"
        "tier2":   "#3b82f6",   # electric blue
        "tier3":   "#f59e0b",   # amber
        "new":     "#a855f7",   # violet
        "active":  "#00ff87",
        "dormant": "#f59e0b",
        "closed":  "#ef4444",
        "default": "#475569",
        "master":  "#ffffff",
        "link":    "#1e3a5f",   # muted dark blue for grouping edges
    }

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_match_network(
        self,
        df: pd.DataFrame,
        ubid_assignments: Dict[int, Dict],
        matches: List,
        height: str = "700px",
    ):
        """Full entity-resolution match network rendered with gravis d3."""
        if gv is None or df is None or df.empty:
            return None

        G = nx.Graph()

        ubid_groups: Dict[str, List[int]] = {}
        for idx, a in ubid_assignments.items():
            ubid_groups.setdefault(a.get("ubid", "UNK"), []).append(idx)

        group_colors = self._generate_group_colors(ubid_groups)

        # --- nodes ---
        for idx in range(len(df)):
            row = df.iloc[idx]
            a = ubid_assignments.get(idx, {})
            tier = a.get("tier", "New")
            ubid = a.get("ubid", "UNK")
            is_master = a.get("is_master", False)

            color = self.COLORS["master"] if is_master else self._resolve_node_color(tier, ubid, group_colors)
            size = 28 if is_master else 16
            label = str(row.get("business_name", str(idx)))[:28]
            tooltip = self._tooltip(row, a)

            G.add_node(idx, label=label, color=color, size=size, hover=tooltip,
                       border_color=color, border_size=2 if is_master else 1)

        # --- match edges ---
        added: set = set()
        for m in matches:
            key = tuple(sorted([m.record1_id, m.record2_id]))
            if key in added:
                continue
            ec, ew, _ = self._edge_style(m.score)
            G.add_edge(m.record1_id, m.record2_id,
                       color=ec, size=ew, hover=m.reason, label="")
            added.add(key)

        # --- UBID grouping edges (faint) ---
        for ubid, indices in ubid_groups.items():
            if len(indices) <= 1:
                continue
            root = indices[0]
            for idx in indices[1:]:
                key = tuple(sorted([root, idx]))
                if key in added:
                    continue
                G.add_edge(root, idx, color=self.COLORS["link"], size=0.8,
                           hover=f"Same UBID: {ubid}", label="")
                added.add(key)

        kwargs = dict(_GRAPH_KWARGS)
        kwargs["graph_height"] = int(height.replace("px", ""))
        return gv.d3(G, **kwargs)

    def create_ubid_cluster_view(self, ubid: str, df: pd.DataFrame, matches: List):
        """Focused cluster view for a single UBID group."""
        if gv is None or df is None or df.empty:
            return None

        G = nx.Graph()

        for idx, row in df.iterrows():
            status = str(row.get("business_status", "")).lower()
            color = self.COLORS.get(status, self.COLORS["default"])
            G.add_node(idx,
                       label=str(row.get("business_name", ""))[:25],
                       color=color,
                       size=18,
                       hover=f"UBID: {ubid} | status: {status}")

        for m in matches:
            if m.record1_id in df.index and m.record2_id in df.index:
                ec, ew, _ = self._edge_style(getattr(m, "score", 75))
                G.add_edge(m.record1_id, m.record2_id, color=ec, size=ew, label="")

        kwargs = dict(_GRAPH_KWARGS)
        kwargs["graph_height"] = 500
        return gv.d3(G, **kwargs)

    # ------------------------------------------------------------------
    # Chart helpers (no pyvis dependency — plain dicts, unchanged)
    # ------------------------------------------------------------------

    def create_status_distribution_chart(self, df: pd.DataFrame) -> Dict:
        if df is None or "business_status" not in df:
            return {}
        counts = df["business_status"].value_counts().to_dict()
        return {"labels": list(counts.keys()), "data": list(counts.values())}

    def create_confidence_distribution(self, assignments: Dict[int, Dict]) -> Dict:
        buckets = {"90+": 0, "70-89": 0, "50-69": 0, "<50": 0}
        seen: Dict[str, float] = {}
        for a in assignments.values():
            ubid = a.get("ubid")
            if ubid and ubid not in seen:
                seen[ubid] = float(a.get("confidence", 0))
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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_node_color(self, tier: str, ubid: str, group_colors: Dict[str, str]) -> str:
        return {
            "Tier1": self.COLORS["tier1"],
            "Tier2": self.COLORS["tier2"],
            "Tier3": self.COLORS["tier3"],
        }.get(tier, group_colors.get(ubid, self.COLORS["new"]))

    def _edge_style(self, score: float):
        """Returns (color, width, dashes) — gravis uses color+size on edges."""
        if score >= 85:
            return self.COLORS["tier1"], 3, False
        if score >= 50:
            return self.COLORS["tier2"], 2, False
        return self.COLORS["tier3"], 1, True

    def _tooltip(self, r: pd.Series, a: Dict) -> str:
        return (
            f"{r.get('business_name')} | "
            f"UBID: {a.get('ubid')} | "
            f"Confidence: {a.get('confidence')}"
        )

    def _generate_group_colors(self, groups: Dict[str, List[int]]) -> Dict[str, str]:
        colors = {}
        for i, k in enumerate(groups.keys()):
            hue = (i * 137.5) % 360
            colors[k] = self._hsl_to_hex(hue, 72, 52)
        return colors

    def _hsl_to_hex(self, h: float, s: float, l: float) -> str:
        s /= 100; l /= 100
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2
        if   0   <= h < 60:  r, g, b = c, x, 0
        elif 60  <= h < 120: r, g, b = x, c, 0
        elif 120 <= h < 180: r, g, b = 0, c, x
        elif 180 <= h < 240: r, g, b = 0, x, c
        elif 240 <= h < 300: r, g, b = x, 0, c
        else:                r, g, b = c, 0, x
        r, g, b = (int((v + m) * 255) for v in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"
