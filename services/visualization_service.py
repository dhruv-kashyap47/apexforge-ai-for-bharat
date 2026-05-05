import logging
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

try:
    from pyvis.network import Network
except Exception:
    Network = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisualizationService:

    COLORS = {
        "tier1": "#16a34a",
        "tier2": "#2563eb",
        "tier3": "#f59e0b",
        "new": "#7c3aed",
        "active": "#16a34a",
        "dormant": "#f59e0b",
        "closed": "#dc2626",
        "default": "#6b7280",
    }

    def __init__(self):
        pass

    def create_match_network(
        self,
        df: pd.DataFrame,
        ubid_assignments: Dict[int, Dict],
        matches: List,
        height: str = "700px",
    ):
        if Network is None or df is None or df.empty:
            return None

        net = Network(height=height, width="100%", bgcolor="#ffffff", font_color="#111827")
        net.barnes_hut()

        ubid_groups: Dict[str, List[int]] = {}
        for idx, a in ubid_assignments.items():
            ubid = a.get("ubid", "UNK")
            ubid_groups.setdefault(ubid, []).append(idx)

        group_colors = self._generate_group_colors(ubid_groups)

        for idx in range(len(df)):
            row = df.iloc[idx]
            a = ubid_assignments.get(idx, {})

            name = str(row.get("business_name", f"{idx}"))[:30]
            ubid = a.get("ubid", "UNK")
            tier = a.get("tier", "New")
            is_master = a.get("is_master", False)

            color = self._resolve_node_color(tier, ubid, group_colors)
            size = 26 if is_master else 14

            net.add_node(
                idx,
                label=name,
                title=self._tooltip(row, a),
                color="#111827" if is_master else color,
                size=size,
            )

        added = set()

        for m in matches:
            key = tuple(sorted([m.record1_id, m.record2_id]))
            if key in added:
                continue

            color, width, dashes = self._edge_style(m.score)

            net.add_edge(
                m.record1_id,
                m.record2_id,
                color=color,
                width=width,
                dashes=dashes,
                title=m.reason,
            )
            added.add(key)

        for ubid, indices in ubid_groups.items():
            if len(indices) <= 1:
                continue
            root = indices[0]
            for idx in indices[1:]:
                key = tuple(sorted([root, idx]))
                if key in added:
                    continue
                net.add_edge(root, idx, color="#d1d5db", width=1, dashes=True)
                added.add(key)

        return net

    def create_ubid_cluster_view(self, ubid: str, df: pd.DataFrame, matches: List):
        if Network is None or df is None or df.empty:
            return None

        net = Network(height="500px", width="100%")
        net.barnes_hut()

        for idx, row in df.iterrows():
            status = str(row.get("business_status", "")).lower()
            color = self.COLORS.get(status, self.COLORS["default"])

            net.add_node(
                idx,
                label=str(row.get("business_name", ""))[:25],
                color=color,
                title=f"UBID: {ubid}",
            )

        for m in matches:
            if m.record1_id in df.index and m.record2_id in df.index:
                net.add_edge(m.record1_id, m.record2_id, width=2)

        return net

    def create_status_distribution_chart(self, df: pd.DataFrame) -> Dict:
        if df is None or "business_status" not in df:
            return {}

        counts = df["business_status"].value_counts().to_dict()
        return {
            "labels": list(counts.keys()),
            "data": list(counts.values()),
        }

    def create_confidence_distribution(self, assignments: Dict[int, Dict]) -> Dict:
        buckets = {"90+": 0, "70-89": 0, "50-69": 0, "<50": 0}

        seen = {}
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

    def _resolve_node_color(self, tier: str, ubid: str, group_colors: Dict[str, str]):
        if tier == "Tier1":
            return self.COLORS["tier1"]
        if tier == "Tier2":
            return self.COLORS["tier2"]
        if tier == "Tier3":
            return self.COLORS["tier3"]
        return group_colors.get(ubid, self.COLORS["new"])

    def _edge_style(self, score: float):
        if score >= 85:
            return self.COLORS["tier1"], 3, False
        if score >= 50:
            return self.COLORS["tier2"], 2, False
        return self.COLORS["tier3"], 1, True

    def _tooltip(self, r: pd.Series, a: Dict) -> str:
        return f"{r.get('business_name')}\nUBID: {a.get('ubid')}\nConfidence: {a.get('confidence')}"

    def _generate_group_colors(self, groups: Dict[str, List[int]]) -> Dict[str, str]:
        colors = {}
        for i, k in enumerate(groups.keys()):
            hue = (i * 137.5) % 360
            colors[k] = self._hsl_to_hex(hue, 70, 55)
        return colors

    def _hsl_to_hex(self, h, s, l):
        s /= 100
        l /= 100
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
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
        r = int((r + m) * 255)
        g = int((g + m) * 255)
        b = int((b + m) * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
