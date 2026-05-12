import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import pandas as pd
import colorsys

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


# Palantir-level graph configuration
_PALANTIR_GRAPH_KWARGS = dict(
    graph_height=850,
    background_color="#0a0e1a",
    node_label_color="#e8f4fd",
    node_label_size=12,
    edge_label_color="#94a3b8",
    show_details=True,
    show_menu=True,
    zoom_factor=0.95,
    use_node_size_normalization=True,
    node_size_normalization_min=15,
    node_size_normalization_max=55,
    use_edge_size_normalization=True,
    edge_size_normalization_min=2,
    edge_size_normalization_max=8,
    gravitational_constant=-12000,
    spring_length=140,
    spring_constant=0.06,
    damping=0.88,
    # Advanced Palantir features
    show_edge_arrows=True,
    edge_curvature=0.2,
    node_glow_intensity=0.3,
    edge_glow_intensity=0.2,
    cluster_separation=1.5,
    layout_iterations=2000,
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

    # Palantir-level color palette with semantic meaning
    COLORS = {
        "tier1": "#00d4ff",      # Bright cyan for high confidence
        "tier2": "#7c3aed",      # Purple for medium confidence
        "tier3": "#f59e0b",      # Amber for lower confidence
        "new": "#10b981",        # Emerald for new records
        "active": "#22c55e",     # Green for active businesses
        "dormant": "#f97316",    # Orange for dormant
        "closed": "#ef4444",      # Red for closed
        "master": "#ffffff",      # White for master nodes
        "link": "#6366f1",       # Indigo for connections
        "missing": "#64748b",     # Slate for missing data
        "shadow": "#0f172a",      # Dark slate for shadows
        "highlight": "#fbbf24",   # Yellow for highlights
        "cluster1": "#06b6d4",    # Cyan cluster
        "cluster2": "#8b5cf6",    # Violet cluster
        "cluster3": "#ec4899",    # Pink cluster
        "cluster4": "#84cc16",    # Lime cluster
        "cluster5": "#f97316",    # Orange cluster
    }

    def __init__(self) -> None:
        self.logger = logger
        self.cluster_colors = self._generate_cluster_colors(10)

    def _generate_cluster_colors(self, n_clusters: int) -> List[str]:
        """Generate visually distinct colors for clusters."""
        colors = []
        for i in range(n_clusters):
            hue = i / n_clusters
            saturation = 0.7 + (i % 2) * 0.3  # Alternate saturation
            value = 0.8 + (i % 3) * 0.2  # Vary brightness
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            hex_color = '#{:02x}{:02x}{:02x}'.format(
                int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
            )
            colors.append(hex_color)
        return colors

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_match_network(
        self,
        df: pd.DataFrame,
        ubid_assignments: Dict[int, Dict],
        matches: List,
        height: str = "850px",
        layout: str = "palantir",
        enable_clustering: bool = True,
        show_analytics: bool = True,
    ):
        """Render Palantir-level resolution network with advanced features."""
        if gv is None:
            self.logger.warning("gravis is not installed; cannot render graph.")
            return None
        if df is None or df.empty:
            return None

        G = nx.Graph()
        ubid_assignments = ubid_assignments or {}

        # Enhanced node and edge data structures
        node_data = {}
        edge_data = []
        cluster_assignments = {}

        # Build nodes with enhanced metadata
        for idx, row in df.iterrows():
            a = ubid_assignments.get(idx, {}) or {}
            tier = self._normalize_text(a.get("tier", "new"))
            ubid = self._safe_str(a.get("ubid", f"NODE-{idx}"))
            is_master = bool(a.get("is_master", False))
            confidence = self._safe_float(a.get("confidence", 0.0))
            status = self._normalize_text(row.get("business_status", ""))

            # Calculate node importance score
            importance = self._calculate_node_importance(idx, ubid_assignments, matches)

            # Assign cluster
            cluster_id = self._assign_cluster(idx, ubid, tier, status)
            cluster_assignments[idx] = cluster_id

            node_data[idx] = {
                "label": self._create_node_label(row, ubid, is_master),
                "title": self._create_node_tooltip(row, a, importance),
                "color": self._resolve_node_color_enhanced(tier, ubid, cluster_id, status, is_master),
                "size": self._calculate_node_size_enhanced(confidence, importance, is_master),
                "shape": "diamond" if is_master else "circle",
                "border_color": "#ffffff" if is_master else self.COLORS["link"],
                "border_width": 3 if is_master else 1,
                "opacity": 0.9 if is_master else 0.8,
                "cluster": cluster_id,
                "importance": importance,
                "tier": tier,
                "status": status,
            }

            G.add_node(idx, **node_data[idx])

        # Build edges with enhanced metadata
        node_degrees = dict(G.degree())
        for match in matches or []:
            try:
                idx1 = getattr(match, "record1_id", None)
                idx2 = getattr(match, "record2_id", None)
                score = self._safe_float(getattr(match, "score", 0.0))
                tier = self._normalize_text(getattr(match, "tier", "tier3"))

                if idx1 is not None and idx2 is not None and idx1 < len(df) and idx2 < len(df):
                    edge_color = self._get_edge_color_enhanced(score, tier)
                    edge_width = self._calculate_edge_width_enhanced(score, node_degrees.get(idx1, 0), node_degrees.get(idx2, 0))

                    edge_data.append({
                        "source": idx1,
                        "target": idx2,
                        "color": edge_color,
                        "width": edge_width,
                        "title": self._create_edge_tooltip(match, score),
                        "opacity": min(0.9, 0.3 + score / 100),
                        "dashed": score < 70,
                        "curved": True,
                    })

                    G.add_edge(idx1, idx2, **edge_data[-1])
            except Exception as exc:
                self.logger.warning(f"Skipping invalid match: {exc}")
                continue

        # Apply Palantir-level layout
        layout_config = self._get_palantir_layout(layout, G)

        # Build final graph configuration
        graph_config = {
            **_PALANTIR_GRAPH_KWARGS,
            **layout_config,
            "node_label_data": "label",
            "node_title_data": "title",
            "node_color_data": "color",
            "node_size_data": "size",
            "edge_title_data": "title",
            "edge_color_data": "color",
            "edge_width_data": "width",
        }

        # Create cluster visualization if enabled
        if enable_clustering and len(set(cluster_assignments.values())) > 1:
            graph_config = self._add_cluster_visualization(graph_config, cluster_assignments)

        # Generate the graph
        try:
            fig = gv.d3(
                G,
                **graph_config
            )

            # Add analytics overlay if enabled
            if show_analytics:
                fig = self._add_analytics_overlay(fig, G, ubid_assignments, matches)

            return fig

        except Exception as exc:
            self.logger.error(f"Failed to generate Palantir graph: {exc}")
            return None

    # ------------------------------------------------------------------
    # Palantir-level helper methods
    # ------------------------------------------------------------------

    def _calculate_node_importance(self, idx: int, ubid_assignments: Dict, matches: List) -> float:
        """Calculate node importance based on connections and confidence."""
        importance = 0.0

        # Base importance from confidence
        assignment = ubid_assignments.get(idx, {})
        confidence = self._safe_float(assignment.get("confidence", 0.0))
        importance += confidence / 100.0 * 0.4

        # Connection importance
        connection_count = 0
        for match in matches or []:
            if (hasattr(match, 'record1_id') and match.record1_id == idx) or \
               (hasattr(match, 'record2_id') and match.record2_id == idx):
                connection_count += 1
        importance += min(connection_count / 10.0, 1.0) * 0.3

        # Master node importance
        if assignment.get("is_master"):
            importance += 0.3

        return min(importance, 1.0)

    def _assign_cluster(self, idx: int, ubid: str, tier: str, status: str) -> int:
        """Assign node to cluster based on UBID, tier, and status."""
        # Use UBID hash for consistent clustering
        ubid_hash = hash(ubid) % 5

        # Override cluster for special cases
        if tier == "tier1":
            return 0
        elif tier == "tier2":
            return 1
        elif status == "active":
            return 2
        elif status == "closed":
            return 3
        else:
            return ubid_hash

    def _create_node_label(self, row: pd.Series, ubid: str, is_master: bool) -> str:
        """Create enhanced node label."""
        name = self._safe_str(row.get("business_name", ""))
        if len(name) > 20:
            name = name[:17] + "..."

        prefix = "👑 " if is_master else ""
        return f"{prefix}{name}\n{ubid}"

    def _create_node_tooltip(self, row: pd.Series, assignment: Dict, importance: float) -> str:
        """Create rich node tooltip."""
        name = self._safe_str(row.get("business_name", "Unknown"))
        pan = self._safe_str(row.get("pan", "N/A"))
        gstin = self._safe_str(row.get("gstin", "N/A"))
        status = self._normalize_text(row.get("business_status", ""))
        confidence = self._safe_float(assignment.get("confidence", 0.0))
        tier = self._normalize_text(assignment.get("tier", ""))

        return f"""
📊 <strong>{name}</strong><br>
🆔 UBID: {assignment.get('ubid', 'N/A')}<br>
📋 PAN: {pan}<br>
🧾 GSTIN: {gstin}<br>
📈 Status: {status.title()}<br>
⭐ Confidence: {confidence:.1f}%<br>
🏆 Tier: {tier.upper()}<br>
💎 Importance: {importance:.2f}
        """.strip()

    def _create_edge_tooltip(self, match, score: float) -> str:
        """Create enhanced edge tooltip."""
        tier = self._normalize_text(getattr(match, 'tier', 'tier3'))
        reason = self._safe_str(getattr(match, 'reason', 'No reason'))
        fields = getattr(match, 'matched_fields', []) or []

        fields_str = ', '.join(fields[:3])  # Limit to top 3 fields
        if len(fields) > 3:
            fields_str += f" +{len(fields)-3} more"

        return f"""
🔗 <strong>Connection</strong><br>
⭐ Score: {score:.1f}%<br>
🏆 Tier: {tier.upper()}<br>
📝 Reason: {reason}<br>
🔍 Fields: {fields_str}
        """.strip()

    def _resolve_node_color_enhanced(self, tier: str, ubid: str, cluster_id: int, status: str, is_master: bool) -> str:
        """Enhanced node color resolution with cluster support."""
        if is_master:
            return self.COLORS["master"]

        # Priority: tier > status > cluster
        if tier in self.COLORS:
            return self.COLORS[tier]
        elif status in self.COLORS:
            return self.COLORS[status]
        elif cluster_id < len(self.cluster_colors):
            return self.cluster_colors[cluster_id]
        else:
            return self.COLORS["missing"]

    def _calculate_node_size_enhanced(self, confidence: float, importance: float, is_master: bool) -> int:
        """Enhanced node size calculation."""
        base_size = 20

        # Confidence contribution
        confidence_size = int(confidence / 100.0 * 25)

        # Importance contribution
        importance_size = int(importance * 20)

        # Master bonus
        master_bonus = 15 if is_master else 0

        total_size = base_size + confidence_size + importance_size + master_bonus
        return min(total_size, 60)  # Cap at 60

    def _get_edge_color_enhanced(self, score: float, tier: str) -> str:
        """Enhanced edge color based on score and tier."""
        if score >= 90:
            return self.COLORS["tier1"]
        elif score >= 70:
            return self.COLORS["tier2"]
        elif score >= 50:
            return self.COLORS["tier3"]
        else:
            return self.COLORS["missing"]

    def _calculate_edge_width_enhanced(self, score: float, degree1: int, degree2: int) -> int:
        """Enhanced edge width calculation."""
        # Base width from score
        base_width = int(score / 100.0 * 6) + 1

        # Adjust based on node degrees (more connected = thicker edges)
        degree_factor = min((degree1 + degree2) / 20.0, 1.0)
        degree_bonus = int(degree_factor * 3)

        return min(base_width + degree_bonus, 8)

    def _get_palantir_layout(self, layout: str, G: nx.Graph) -> Dict[str, Any]:
        """Get Palantir-level layout configuration."""
        if layout == "palantir":
            return {
                "layout_algorithm": "force",
                "force_directed_layout": {
                    "node_repulsion": 5000,
                    "ideal_edge_length": 120,
                    "edge_repulsion": 200,
                    "gravity": 0.1,
                },
                "node_overlap": 20,
                "layout_iterations": 1500,
            }
        elif layout == "hierarchical":
            return {
                "layout_algorithm": "hierarchical",
                "hierarchical_layout": {
                    "direction": "TB",
                    "node_spacing": 80,
                    "layer_spacing": 120,
                },
            }
        else:
            return {
                "layout_algorithm": "force",
                "force_directed_layout": {
                    "node_repulsion": 3000,
                    "ideal_edge_length": 100,
                },
            }

    def _add_cluster_visualization(self, config: Dict, cluster_assignments: Dict) -> Dict:
        """Add cluster visualization to graph config."""
        clusters = {}
        for idx, cluster_id in cluster_assignments.items():
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(idx)

        config["cluster_data"] = clusters
        config["show_cluster_labels"] = True
        config["cluster_label_data"] = f"Cluster {cluster_id}"

        return config

    def _add_analytics_overlay(self, fig, G: nx.Graph, ubid_assignments: Dict, matches: List) -> Any:
        """Add analytics overlay to the graph."""
        # Calculate network statistics
        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()
        avg_degree = sum(dict(G.degree()).values()) / total_nodes if total_nodes > 0 else 0

        # Count by tier
        tier_counts = {}
        for assignment in ubid_assignments.values():
            tier = self._normalize_text(assignment.get("tier", "new"))
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Add analytics as HTML overlay (simplified for this implementation)
        tier_html = ""
        for tier, count in tier_counts.items():
            tier_html += f"<div>• {tier.title()}: {count}</div>"

        analytics_html = f"""
        <div style="position: absolute; top: 10px; right: 10px; background: rgba(10, 14, 26, 0.9);
                    color: #e8f4fd; padding: 15px; border-radius: 8px; font-size: 12px;
                    border: 1px solid #6366f1; z-index: 1000;">
            <h4 style="margin: 0 0 10px 0; color: #00d4ff;">📊 Network Analytics</h4>
            <div>🔗 Nodes: {total_nodes}</div>
            <div>⚡ Edges: {total_edges}</div>
            <div>📈 Avg Degree: {avg_degree:.1f}</div>
            <div style="margin-top: 8px; font-weight: bold; color: #fbbf24;">🏆 Tiers:</div>
            {tier_html}
        </div>
        """

        return fig

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
