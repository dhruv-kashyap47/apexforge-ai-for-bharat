"""ApexForge AI - Unified Business Identity System

Streamlit main application with a polished UX.

Highlights:
- smoother upload flow
- clearer dashboard cards and empty states
- safer optional database handling
- local-first processing path
- cleaner results, explorer, review queue, analytics, and network graph views
- better visual hierarchy and reduced clutter
"""

from __future__ import annotations

import csv
import io
import logging
import os
import tempfile
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from core.data_cleaner import DataCleaner
from core.matching_engine import MatchingEngine, MatchResult
from core.status_analyzer import StatusAnalyzer
from core.ubid_generator import UBIDGenerator

try:
    from db.connection import get_db_manager
except Exception:  # pragma: no cover
    get_db_manager = None

try:
    from pyvis.network import Network
except Exception:  # pragma: no cover
    Network = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ApexForge AI",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()


REQUIRED_COLUMNS = [
    "business_name",
    "pan",
    "gstin",
    "address",
    "pincode",
    "district",
    "state",
    "registration_date",
    "last_activity_date",
    "department",
]

COLUMN_SYNONYMS = {
    "business_name": ["businessname", "name", "company", "companyname", "entity_name", "legal_name"],
    "pan": ["pancard", "pan_no", "pan_number", "taxpan"],
    "gstin": ["gst", "gst_no", "gst_number", "gstin_no"],
    "address": ["addr", "full_address", "location", "registered_address"],
    "pincode": ["pin", "pin_code", "zipcode", "postalcode", "postal_code"],
    "district": ["city", "town", "district_name"],
    "state": ["state_name", "province", "statecode"],
    "registration_date": ["reg_date", "registrationdate", "date_of_registration"],
    "last_activity_date": ["activity_date", "lastactive", "last_active_date", "updated_at"],
    "department": ["dept", "business_type", "category", "industry"],
}

SAMPLE_ROWS = [
    ["Tech Solutions Pvt Ltd", "ABCPE1234F", "27ABCPE1234F1Z5", "123 Main Road Mumbai", "400001", "Mumbai", "Maharashtra", "2020-01-15", "2024-01-10", "GST"],
    ["Global Traders", "XYZPK5678L", "29XYZPK5678L1Z8", "456 Market Street Bangalore", "560001", "Bangalore", "Karnataka", "2019-06-20", "2023-12-01", "Income Tax"],
]


CSS = """
<style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }
    .hero {
        padding: 1.25rem 1.4rem;
        border-radius: 24px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #312e81 100%);
        color: white;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.22);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2rem;
        line-height: 1.15;
        font-weight: 800;
    }
    .hero p {
        margin: 0.35rem 0 0 0;
        opacity: 0.9;
        font-size: 0.98rem;
    }
    .surface {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }
    .muted {
        color: #6b7280;
        font-size: 0.95rem;
    }
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        margin: 0.2rem 0.25rem 0.2rem 0;
    }
    .pill-green { background: #dcfce7; color: #166534; }
    .pill-amber { background: #fef3c7; color: #92400e; }
    .pill-red { background: #fee2e2; color: #991b1b; }
    .pill-blue { background: #dbeafe; color: #1d4ed8; }
    .pill-purple { background: #ede9fe; color: #6d28d9; }
    .small-note {
        font-size: 0.83rem;
        color: #6b7280;
        line-height: 1.45;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .section-subtitle {
        color: #6b7280;
        margin-bottom: 0.8rem;
    }
</style>
"""


if "db_initialized" not in st.session_state:
    st.session_state.db_initialized = False
if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False
if "batch_id" not in st.session_state:
    st.session_state.batch_id = None
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "df_processed" not in st.session_state:
    st.session_state.df_processed = None
if "matches" not in st.session_state:
    st.session_state.matches = []
if "match_groups" not in st.session_state:
    st.session_state.match_groups = []
if "ubid_assignments" not in st.session_state:
    st.session_state.ubid_assignments = {}
if "status_summary" not in st.session_state:
    st.session_state.status_summary = {}
if "local_mode" not in st.session_state:
    st.session_state.local_mode = True
if "db_manager" not in st.session_state:
    st.session_state.db_manager = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None

st.markdown(CSS, unsafe_allow_html=True)


def normalize_col(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def safe_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return str(value)


def format_confidence(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "N/A"


def auto_map_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], List[str]]:
    mapped = df.copy()
    detected: List[str] = []
    missing: List[str] = []

    normalized_to_original = {normalize_col(c): c for c in mapped.columns}

    for canonical, aliases in COLUMN_SYNONYMS.items():
        if canonical in mapped.columns:
            continue
        found = None
        for candidate in [canonical] + aliases:
            key = normalize_col(candidate)
            if key in normalized_to_original:
                found = normalized_to_original[key]
                break
        if found:
            mapped = mapped.rename(columns={found: canonical})
            detected.append(f"{found} → {canonical}")
        else:
            missing.append(canonical)

    for col in REQUIRED_COLUMNS:
        if col not in mapped.columns:
            mapped[col] = None

    return mapped, detected, missing


def generate_sample_csv(num_rows: int, include_duplicates: bool) -> str:
    rows: List[List[str]] = []
    for i in range(num_rows):
        seed = SAMPLE_ROWS[i % len(SAMPLE_ROWS)]
        row = seed.copy()
        row[0] = f"{seed[0].replace(' Pvt Ltd', '')} {i + 1}"
        row[1] = f"ABCDE{i % 10}{i % 10}{i % 10}F"
        row[2] = f"27ABCDE{i % 10}{i % 10}{i % 10}F1Z5"
        row[4] = f"{400000 + (i % 1000):06d}"[-6:]
        rows.append(row)

    if include_duplicates and rows:
        for i in range(min(5, len(rows))):
            dup = rows[i].copy()
            dup[0] = dup[0].replace("1", "I")
            rows.append(dup)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(REQUIRED_COLUMNS)
    writer.writerows(rows)
    return output.getvalue()


def reset_processing_state() -> None:
    st.session_state.processing_complete = False
    st.session_state.batch_id = None
    st.session_state.raw_df = None
    st.session_state.df_processed = None
    st.session_state.matches = []
    st.session_state.match_groups = []
    st.session_state.ubid_assignments = {}
    st.session_state.status_summary = {}
    st.session_state.last_error = None


def init_database() -> Optional[Any]:
    if get_db_manager is None:
        st.session_state.db_initialized = False
        st.session_state.local_mode = True
        st.session_state.db_manager = None
        st.toast("Database support not available. Using local mode.")
        return None

    try:
        db_manager = get_db_manager()
        if hasattr(db_manager, "initialize_schema"):
            db_manager.initialize_schema()
        st.session_state.db_initialized = True
        st.session_state.local_mode = False
        st.session_state.db_manager = db_manager
        st.toast("Database connected successfully.")
        return db_manager
    except Exception as exc:
        st.session_state.db_initialized = False
        st.session_state.local_mode = True
        st.session_state.db_manager = None
        st.warning(f"Database unavailable. Running in local mode: {exc}")
        return None


def compute_local_stats(df: Optional[pd.DataFrame], matches: List[MatchResult], groups: List[List[int]], assignments: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "total_records": 0,
            "ubids_generated": 0,
            "matches_found": 0,
            "pending_reviews": 0,
            "active_count": 0,
            "dormant_count": 0,
            "closed_count": 0,
            "match_groups": 0,
            "auto_merge": 0,
            "needs_review": 0,
            "new_records": 0,
        }

    status_counts = df["business_status"].value_counts(dropna=False).to_dict() if "business_status" in df.columns else {}
    decisions = df["match_decision"].value_counts(dropna=False).to_dict() if "match_decision" in df.columns else {}

    return {
        "total_records": int(len(df)),
        "ubids_generated": int(df["ubid"].nunique()) if "ubid" in df.columns else int(len(df)),
        "matches_found": int(len(matches)),
        "pending_reviews": int(sum(1 for m in matches if getattr(m, "decision", "") == "NeedsReview")),
        "active_count": int(status_counts.get("Active", 0)),
        "dormant_count": int(status_counts.get("Dormant", 0)),
        "closed_count": int(status_counts.get("Closed", 0)),
        "match_groups": int(len(groups)),
        "auto_merge": int(decisions.get("AutoMerge", 0)),
        "needs_review": int(decisions.get("NeedsReview", 0)),
        "new_records": int(decisions.get("New", 0)),
    }


def attach_assignments(df: pd.DataFrame, assignments: Dict[int, Dict[str, Any]]) -> pd.DataFrame:
    out = df.copy()
    out["ubid"] = ""
    out["match_confidence"] = 0.0
    out["match_tier"] = ""
    out["match_decision"] = ""
    out["is_master"] = False

    for idx, item in assignments.items():
        if 0 <= idx < len(out) and isinstance(item, dict):
            out.at[idx, "ubid"] = item.get("ubid", "")
            out.at[idx, "match_confidence"] = float(item.get("confidence", 0.0) or 0.0)
            out.at[idx, "match_tier"] = item.get("tier", "")
            out.at[idx, "match_decision"] = item.get("decision", "")
            out.at[idx, "is_master"] = bool(item.get("is_master", False))

    return out


def attach_group_summary(df: pd.DataFrame, groups: List[List[int]]) -> pd.DataFrame:
    out = df.copy()
    out["group_id"] = None
    out["group_size"] = 1
    out["group_role"] = "Solo"

    group_map: Dict[int, Tuple[int, int]] = {}
    for gid, group in enumerate(groups, start=1):
        valid = [idx for idx in group if 0 <= idx < len(out)]
        for idx in valid:
            group_map[idx] = (gid, len(valid))

    for idx in range(len(out)):
        if idx in group_map:
            gid, gsize = group_map[idx]
            out.at[idx, "group_id"] = gid
            out.at[idx, "group_size"] = gsize
            out.at[idx, "group_role"] = "Master" if bool(out.at[idx, "is_master"]) else "Member"

    return out


def pipeline_process(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        raise ValueError("No data provided")

    batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    progress = st.progress(0)
    status_text = st.empty()

    cleaner = DataCleaner()
    matcher = MatchingEngine()
    analyzer = StatusAnalyzer()
    ubid_gen = UBIDGenerator(db_manager=st.session_state.get("db_manager"))

    status_text.write("Cleaning data...")
    df_clean = cleaner.clean_dataframe(df)
    progress.progress(20)

    status_text.write("Analyzing business status...")
    df_status = analyzer.analyze_dataframe(df_clean)
    progress.progress(40)

    status_text.write("Finding matches...")
    matches = matcher.find_matches(df_status)
    groups = matcher.group_matches(matches, len(df_status))
    progress.progress(60)

    status_text.write("Assigning UBIDs...")
    try:
        assignments = ubid_gen.assign_ubids(df_status, groups, matches)
    except Exception as exc:
        logger.warning("UBID assignment fallback used: %s", exc)
        assignments = {}
        for idx in range(len(df_status)):
            row = df_status.iloc[idx]
            state_code = row.get("state_code") or "XX"
            district_code = row.get("district_code") or "XXX"
            category = row.get("department") or "TR"
            ubid = ubid_gen.generate_ubid(state_code, district_code, category)
            assignments[idx] = {
                "ubid": ubid,
                "is_master": True,
                "confidence": 100.0,
                "tier": "New",
                "matched_fields": [],
                "decision": "New",
                "group_indices": [idx],
            }
    progress.progress(80)

    status_text.write("Finalizing results...")
    df_final = attach_assignments(df_status, assignments)
    df_final = attach_group_summary(df_final, groups)

    st.session_state.batch_id = batch_id
    st.session_state.raw_df = df.copy()
    st.session_state.df_processed = df_final
    st.session_state.matches = matches
    st.session_state.match_groups = groups
    st.session_state.ubid_assignments = assignments
    st.session_state.status_summary = analyzer.get_summary()
    st.session_state.processing_complete = True
    st.session_state.last_error = None

    progress.progress(100)
    status_text.empty()
    st.success(f"Processing complete. Batch ID: {batch_id}")


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>🏢 ApexForge AI</h1>
            <p>Unified Business Identity System for clean uploads, smart matching, and fast UBID exploration.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("### ApexForge AI")
        st.caption("Business identity pipeline")
        st.divider()

        db_col1, db_col2 = st.columns([1, 1])
        with db_col1:
            if st.button("Connect DB", use_container_width=True):
                init_database()
        with db_col2:
            if st.button("Reset", use_container_width=True):
                reset_processing_state()
                st.rerun()

        if st.session_state.db_initialized:
            st.markdown("<span class='stat-pill pill-green'>Database connected</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='stat-pill pill-amber'>Local mode</span>", unsafe_allow_html=True)

        if st.session_state.processing_complete:
            st.markdown(f"<span class='stat-pill pill-blue'>Batch ready</span>", unsafe_allow_html=True)

        st.divider()
        page = st.radio(
            "Navigate",
            ["Upload", "Dashboard", "Results", "Network Graph", "UBID Explorer", "Review Queue", "Analytics"],
            index=0 if not st.session_state.processing_complete else 1,
        )

        st.divider()
        st.markdown(
            """
            <div class="small-note">
                Drop a CSV, process it once, then inspect matches, clusters, reviews, and UBIDs without leaving the app.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return page


def render_upload_page() -> None:
    st.markdown("<div class='section-title'>Upload business data</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Clean. Match. Assign. Review. Export.</div>", unsafe_allow_html=True)

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        st.markdown("<div class='surface'>", unsafe_allow_html=True)
        st.markdown("**Drop your CSV here**")
        uploaded_file = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            label_visibility="collapsed",
            help="The app will auto-map common column variations when possible.",
        )

        if uploaded_file is not None:
            df = None
            parse_errors: List[str] = []

            strategies = [
                {"sep": ",", "quotechar": '"', "quoting": csv.QUOTE_MINIMAL, "encoding": "utf-8", "on_bad_lines": "skip"},
                {"sep": ",", "quotechar": '"', "quoting": csv.QUOTE_MINIMAL, "encoding": "latin-1", "on_bad_lines": "skip"},
                {"sep": "\t", "encoding": "utf-8", "on_bad_lines": "skip"},
                {"sep": ";", "encoding": "utf-8", "on_bad_lines": "skip"},
            ]

            for i, strategy in enumerate(strategies, start=1):
                try:
                    uploaded_file.seek(0)
                    candidate = pd.read_csv(uploaded_file, **strategy)
                    if len(candidate.columns) >= 3:
                        df = candidate
                        break
                    parse_errors.append(f"Parser #{i}: only {len(candidate.columns)} columns found")
                except Exception as exc:
                    parse_errors.append(f"Parser #{i}: {str(exc)[:120]}")

            if df is None:
                st.error("Could not parse the uploaded file.")
                with st.expander("Parser errors"):
                    for err in parse_errors:
                        st.write(err)
                st.markdown("</div>", unsafe_allow_html=True)
                return

            mapped, detected, missing = auto_map_columns(df)

            top1, top2, top3, top4 = st.columns(4)
            top1.metric("Rows", len(mapped))
            top2.metric("Columns", len(mapped.columns))
            top3.metric("Mapped", len(detected))
            top4.metric("Missing", len(missing))

            if detected:
                with st.expander("Auto-mapped columns", expanded=False):
                    for item in detected:
                        st.write(f"• {item}")

            if missing:
                st.info(f"Blank columns created for: {', '.join(missing)}")

            with st.expander("Preview data", expanded=True):
                st.dataframe(mapped.head(10), use_container_width=True)

            st.markdown("---")
            if st.button("Process file now", type="primary", use_container_width=True):
                pipeline_process(mapped)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='surface'>", unsafe_allow_html=True)
        st.markdown("**Sample file**")
        rows = st.slider("Rows", 10, 200, 50)
        dups = st.checkbox("Include duplicates", value=True)
        sample_csv = generate_sample_csv(rows, dups)
        st.download_button(
            "Download sample CSV",
            sample_csv,
            file_name=f"apexforge_sample_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("---")
        st.markdown("**Expected structure**")
        st.code(",".join(REQUIRED_COLUMNS))
        st.markdown(
            "<div class='small-note'>The app will tolerate missing columns, but the best results come from the full schema.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard() -> None:
    st.markdown("<div class='section-title'>Dashboard</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.info("Process a file first to unlock the dashboard.")
        return

    df = st.session_state.df_processed
    stats = compute_local_stats(df, st.session_state.matches, st.session_state.match_groups, st.session_state.ubid_assignments)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Records", stats["total_records"])
    c2.metric("UBIDs", stats["ubids_generated"])
    c3.metric("Matches", stats["matches_found"])
    c4.metric("Reviews", stats["pending_reviews"])

    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("**Business status**")
        st.bar_chart(pd.Series({"Active": stats["active_count"], "Dormant": stats["dormant_count"], "Closed": stats["closed_count"]}))
        st.markdown(
            f"<span class='stat-pill pill-green'>Active {stats['active_count']}</span>"
            f"<span class='stat-pill pill-amber'>Dormant {stats['dormant_count']}</span>"
            f"<span class='stat-pill pill-red'>Closed {stats['closed_count']}</span>",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("**Match summary**")
        st.metric("Match groups", stats["match_groups"])
        st.metric("Auto merge", stats["auto_merge"])
        st.metric("Needs review", stats["needs_review"])
        st.metric("New records", stats["new_records"])

    st.markdown("---")
    summary_df = pd.DataFrame(
        [
            ["Batch ID", st.session_state.batch_id],
            ["Total Records", stats["total_records"]],
            ["UBIDs Generated", stats["ubids_generated"]],
            ["Matches Found", stats["matches_found"]],
            ["Active", stats["active_count"]],
            ["Dormant", stats["dormant_count"]],
            ["Closed", stats["closed_count"]],
        ],
        columns=["Metric", "Value"],
    )
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_results_page() -> None:
    st.markdown("<div class='section-title'>Results</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.info("Process a file first to see results.")
        return

    df = st.session_state.df_processed.copy()

    c1, c2, c3, c4 = st.columns(4)
    status_filter = c1.selectbox("Status", ["All", "Active", "Dormant", "Closed"])
    tier_filter = c2.selectbox("Tier", ["All", "Tier1", "Tier2", "Tier3", "New"])
    confidence_min = c3.slider("Min confidence", 0, 100, 0)
    search_term = c4.text_input("Search")

    filtered = df.copy()
    if status_filter != "All" and "business_status" in filtered.columns:
        filtered = filtered[filtered["business_status"] == status_filter]
    if tier_filter != "All" and "match_tier" in filtered.columns:
        filtered = filtered[filtered["match_tier"] == tier_filter]
    if "match_confidence" in filtered.columns:
        filtered = filtered[filtered["match_confidence"] >= confidence_min]
    if search_term:
        term = search_term.strip().lower()
        mask = False
        for col in ["business_name", "pan", "gstin", "ubid", "district", "state"]:
            if col in filtered.columns:
                mask = mask | filtered[col].astype(str).str.lower().str.contains(term, na=False)
        filtered = filtered[mask]

    st.caption(f"Showing {len(filtered)} of {len(df)} records")

    display_cols = [
        c for c in [
            "ubid", "business_name", "pan", "gstin", "district", "state",
            "business_status", "match_tier", "match_confidence", "match_decision",
        ] if c in filtered.columns
    ]
    show_df = filtered[display_cols].copy() if display_cols else filtered.copy()
    if "match_confidence" in show_df.columns:
        show_df["match_confidence"] = show_df["match_confidence"].apply(format_confidence)
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    st.download_button(
        "Download filtered CSV",
        filtered.to_csv(index=False),
        file_name=f"apexforge_results_{st.session_state.batch_id}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def build_pyvis_network(df: pd.DataFrame, matches: List[MatchResult]) -> Optional[Any]:
    if Network is None or df is None or df.empty:
        return None

    net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#111827", directed=False)
    net.barnes_hut()

    for idx, row in df.iterrows():
        name = safe_text(row.get("business_name"), f"Record {idx}")
        ubid = safe_text(row.get("ubid"), f"ROW-{idx}")
        title = (
            f"<b>{name}</b><br>UBID: {ubid}<br>Status: {safe_text(row.get('business_status'))}"
            f"<br>Tier: {safe_text(row.get('match_tier'))}<br>Confidence: {safe_text(row.get('match_confidence'))}"
        )
        tier = row.get("match_tier")
        color = {
            "Tier1": "#16a34a",
            "Tier2": "#2563eb",
            "Tier3": "#f59e0b",
            "New": "#7c3aed",
        }.get(tier, "#6b7280")
        if row.get("is_master", False):
            color = "#111827"
        net.add_node(int(idx), label=name[:30], title=title, color=color, size=24 if row.get("is_master", False) else 14)

    for m in matches:
        if 0 <= m.record1_id < len(df) and 0 <= m.record2_id < len(df):
            color = "#16a34a" if m.tier == "Tier1" else "#2563eb" if m.tier == "Tier2" else "#f59e0b"
            width = 4 if m.decision == "AutoMerge" else 2
            net.add_edge(m.record1_id, m.record2_id, title=m.reason, color=color, width=width)

    return net


def render_network_graph() -> None:
    st.markdown("<div class='section-title'>Network graph</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.info("Process a file first to see the network.")
        return

    show_only_groups = st.checkbox("Show only matched groups", value=False)
    show_review = st.checkbox("Include review matches", value=True)

    df = st.session_state.df_processed.copy()
    matches = st.session_state.matches if show_review else [m for m in st.session_state.matches if m.decision == "AutoMerge"]

    if show_only_groups:
        group_indices = set()
        for grp in st.session_state.match_groups:
            if len(grp) > 1:
                group_indices.update(grp)
        if group_indices:
            sorted_indices = sorted(group_indices)
            df = df.iloc[sorted_indices]
            remap = {old: new for new, old in enumerate(sorted_indices)}
            remapped = []
            for m in matches:
                if m.record1_id in remap and m.record2_id in remap:
                    remapped.append(
                        MatchResult(
                            record1_id=remap[m.record1_id],
                            record2_id=remap[m.record2_id],
                            score=m.score,
                            tier=m.tier,
                            matched_fields=m.matched_fields,
                            reason=m.reason,
                            decision=m.decision,
                        )
                    )
            matches = remapped

    if Network is None:
        st.warning("pyvis is not installed. Network visualization is unavailable.")
        return

    with st.spinner("Building interactive network..."):
        net = build_pyvis_network(df.reset_index(drop=True), matches)
        if net is None:
            st.warning("Network could not be created.")
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, "r", encoding="utf-8") as fh:
                html = fh.read()

        st.components.v1.html(html, height=760, scrolling=True)

    st.markdown("### Legend")
    cols = st.columns(5)
    legend = [
        ("Tier 1", "pill-green"),
        ("Tier 2", "pill-blue"),
        ("Tier 3", "pill-amber"),
        ("New", "pill-purple"),
        ("Master", "pill-red"),
    ]
    for col, (label, cls) in zip(cols, legend):
        with col:
            st.markdown(f"<span class='stat-pill {cls}'>{label}</span>", unsafe_allow_html=True)


def render_ubid_explorer() -> None:
    st.markdown("<div class='section-title'>UBID explorer</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.info("Process a file first to explore UBIDs.")
        return

    df = st.session_state.df_processed.copy()
    query = st.text_input("Search by UBID, name, PAN, GSTIN, district, or state")

    if query:
        q = query.strip().lower()
        mask = False
        for col in ["ubid", "business_name", "pan", "gstin", "district", "state"]:
            if col in df.columns:
                mask = mask | df[col].astype(str).str.lower().str.contains(q, na=False)
        results = df[mask].copy()
    else:
        results = df.head(20).copy()

    if results.empty:
        st.warning("No results found")
        return

    st.dataframe(results, use_container_width=True, hide_index=True)

    if "ubid" in results.columns:
        selected = st.selectbox("Select UBID", results["ubid"].astype(str).tolist())
        if selected:
            row = results[results["ubid"].astype(str) == str(selected)].iloc[0]
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div class='surface'>", unsafe_allow_html=True)
                st.markdown("**UBID summary**")
                info = pd.DataFrame(
                    [
                        ["UBID", safe_text(row.get("ubid"))],
                        ["Business Name", safe_text(row.get("business_name"))],
                        ["Status", safe_text(row.get("business_status"))],
                        ["Tier", safe_text(row.get("match_tier"))],
                        ["Confidence", format_confidence(row.get("match_confidence"))],
                        ["Decision", safe_text(row.get("match_decision"))],
                        ["State", safe_text(row.get("state"))],
                        ["District", safe_text(row.get("district"))],
                    ],
                    columns=["Field", "Value"],
                )
                st.dataframe(info, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with col2:
                st.markdown("<div class='surface'>", unsafe_allow_html=True)
                st.markdown("**Raw row**")
                st.dataframe(pd.DataFrame([row.to_dict()]), use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)


def render_review_queue() -> None:
    st.markdown("<div class='section-title'>Review queue</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.info("Process a file first to see review items.")
        return

    matches = [m for m in st.session_state.matches if m.decision == "NeedsReview"]
    if not matches:
        st.success("No items need review.")
        return

    df = st.session_state.df_processed
    st.caption(f"{len(matches)} items need review")

    for i, m in enumerate(matches, start=1):
        r1 = df.iloc[m.record1_id]
        r2 = df.iloc[m.record2_id]
        with st.expander(f"Review {i}: {safe_text(r1.get('business_name'))} vs {safe_text(r2.get('business_name'))} | {m.tier} | {m.score:.1f}%"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Record 1**")
                st.write(safe_text(r1.get("business_name")))
                st.write(f"PAN: {safe_text(r1.get('pan'))}")
                st.write(f"GSTIN: {safe_text(r1.get('gstin'))}")
                st.write(f"UBID: {safe_text(r1.get('ubid'))}")
            with c2:
                st.markdown("**Record 2**")
                st.write(safe_text(r2.get("business_name")))
                st.write(f"PAN: {safe_text(r2.get('pan'))}")
                st.write(f"GSTIN: {safe_text(r2.get('gstin'))}")
                st.write(f"UBID: {safe_text(r2.get('ubid'))}")
            st.write(f"Reason: {m.reason}")
            st.write(f"Matched fields: {', '.join(m.matched_fields)}")


def render_analytics() -> None:
    st.markdown("<div class='section-title'>Analytics</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.info("Process a file first to see analytics.")
        return

    df = st.session_state.df_processed.copy()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records", len(df))
    c2.metric("UBIDs", df["ubid"].nunique() if "ubid" in df.columns else 0)
    c3.metric("Groups", len(st.session_state.match_groups))
    c4.metric("Review items", sum(1 for m in st.session_state.matches if m.decision == "NeedsReview"))

    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Status distribution**")
        if "business_status" in df.columns:
            st.bar_chart(df["business_status"].value_counts())
        else:
            st.info("No status data available")
    with right:
        st.markdown("**Match tier distribution**")
        if "match_tier" in df.columns:
            st.bar_chart(df["match_tier"].value_counts())
        else:
            st.info("No match data available")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Recent records")
    preview_cols = [c for c in ["ubid", "business_name", "business_status", "match_tier", "match_confidence"] if c in df.columns]
    st.dataframe(df[preview_cols].head(20), use_container_width=True, hide_index=True)


def main() -> None:
    render_header()
    page = render_sidebar()

    if page == "Upload":
        render_upload_page()
    elif page == "Dashboard":
        render_dashboard()
    elif page == "Results":
        render_results_page()
    elif page == "Network Graph":
        render_network_graph()
    elif page == "UBID Explorer":
        render_ubid_explorer()
    elif page == "Review Queue":
        render_review_queue()
    elif page == "Analytics":
        render_analytics()


if __name__ == "__main__":
    main()
