"""ApexForge AI - Unified Business Identity System

Streamlit main application with award-winning, optimized UX.

Changes from original:
- Completely rewritten CSS: tighter proportions, fewer competing animations,
  sharper visual hierarchy, better typography, consistent spacing system
- Eliminated redundant/overlapping animations that cause visual noise
- Better empty states, cleaner metric cards, refined sidebar
- Faster perceived performance via simplified rendering
- All functional Python logic preserved exactly
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import logging
import os
import json
import tempfile
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
    from services.data_service import DataService
except Exception:
    DataService = None

try:
    from db.connection import get_db_manager
except Exception:
    get_db_manager = None

try:
    from pyvis.network import Network
except Exception:
    Network = None

try:
    from services.ai_service import AIReviewService
except Exception:
    AIReviewService = None

try:
    from services.visualization_service import VisualizationService
except Exception:
    VisualizationService = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ApexForge AI",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()


MAX_UPLOAD_SIZE_MB = 50

REQUIRED_COLUMNS = [
    "business_name", "pan", "gstin", "address", "pincode",
    "district", "state", "registration_date", "last_activity_date", "department",
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


# ─────────────────────────────────────────────────────────────────────────────
# CSS — "Neon Carnival" — rich, colorful, vibrant
# Full spectrum: coral, violet, cyan, lime, amber, sky, rose
# Each metric card, pill, and surface has its own distinct color
# Gradient meshes, colored borders, vivid text — high energy, readable
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  /* Backgrounds */
  --bg:    #0A0B10;
  --s1:    #10121A;
  --s2:    #161924;
  --s3:    #1D2130;

  /* Vivid palette */
  --cyan:   #00F0D0;
  --violet: #9B6DFF;
  --rose:   #FF5C8A;
  --amber:  #FFB140;
  --lime:   #8FE847;
  --sky:    #38BFFF;
  --coral:  #FF7A5C;
  --pink:   #FF5EE8;

  /* Text */
  --t1: #F0F2FF;
  --t2: #7C86A2;
  --t3: #3D4560;

  /* Edges */
  --e0: rgba(255,255,255,0.05);
  --e1: rgba(255,255,255,0.09);
  --e2: rgba(255,255,255,0.16);

  /* Radii */
  --r-sm: 8px;
  --r-md: 12px;
  --r-lg: 16px;
  --r-xl: 22px;

  --font-ui:   'Plus Jakarta Sans', system-ui, sans-serif;
  --font-data: 'JetBrains Mono', monospace;
}

*, *::before, *::after { box-sizing: border-box; }

.stApp {
  background: var(--bg) !important;
  font-family: var(--font-ui) !important;
  color: var(--t1) !important;
}
.main .block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 4rem !important;
  max-width: 1360px !important;
}

/* Colorful ambient mesh — static, no jank */
.stApp::before {
  content: '';
  position: fixed; inset: 0;
  background:
    radial-gradient(ellipse 55% 45% at 10% 15%, rgba(155,109,255,0.1) 0%, transparent 55%),
    radial-gradient(ellipse 45% 40% at 90% 20%, rgba(0,240,208,0.07) 0%, transparent 50%),
    radial-gradient(ellipse 50% 35% at 50% 90%, rgba(255,92,138,0.06) 0%, transparent 55%),
    radial-gradient(ellipse 40% 30% at 80% 60%, rgba(255,177,64,0.05) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

/* ── HERO ── */
.hero {
  position: relative;
  padding: 2.25rem 2.5rem 2rem;
  border-radius: var(--r-xl);
  background: linear-gradient(135deg, #12102A 0%, #0E1520 50%, #120E20 100%);
  border: 1px solid rgba(155,109,255,0.25);
  margin-bottom: 1.5rem;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--violet), var(--cyan), var(--rose), var(--amber), var(--lime));
  background-size: 200% 100%;
  animation: rainbowSlide 6s linear infinite;
}
@keyframes rainbowSlide {
  0%   { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
.hero::after {
  content: '';
  position: absolute;
  bottom: -60px; right: -60px;
  width: 280px; height: 280px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(155,109,255,0.12) 0%, transparent 70%);
  pointer-events: none;
}
.hero h1 {
  margin: 0;
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  background: linear-gradient(90deg, var(--cyan) 0%, var(--violet) 40%, var(--rose) 70%, var(--amber) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero p {
  margin: 0.6rem 0 0;
  color: var(--t2);
  font-size: 0.95rem;
  max-width: 560px;
  line-height: 1.6;
}
.hero-badges { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1.25rem; }

/* ── SECTION TITLE ── */
.section-title {
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--t1);
  margin: 0 0 0.25rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--e0);
}
.section-subtitle { font-size: 0.875rem; color: var(--t2); margin-bottom: 1.25rem; }

/* ── SURFACE ── */
.surface {
  background: var(--s1);
  border: 1px solid var(--e1);
  border-radius: var(--r-lg);
  padding: 1.25rem 1.5rem;
}
.surface + .surface { margin-top: 1rem; }

/* ── METRIC CARDS — each variant fully colored ── */
.metric-card {
  position: relative;
  border-radius: var(--r-lg);
  padding: 1.1rem 1.25rem 1rem;
  overflow: hidden;
  border: 1px solid var(--e1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(0,0,0,0.4); }

.metric-card.cyan   { background: linear-gradient(135deg, rgba(0,240,208,0.12) 0%, rgba(0,240,208,0.04) 100%); border-color: rgba(0,240,208,0.25); }
.metric-card.purple { background: linear-gradient(135deg, rgba(155,109,255,0.12) 0%, rgba(155,109,255,0.04) 100%); border-color: rgba(155,109,255,0.25); }
.metric-card.pink   { background: linear-gradient(135deg, rgba(255,92,138,0.12) 0%, rgba(255,92,138,0.04) 100%); border-color: rgba(255,92,138,0.25); }
.metric-card.orange { background: linear-gradient(135deg, rgba(255,177,64,0.12) 0%, rgba(255,177,64,0.04) 100%); border-color: rgba(255,177,64,0.25); }
.metric-card.lime   { background: linear-gradient(135deg, rgba(143,232,71,0.12) 0%, rgba(143,232,71,0.04) 100%); border-color: rgba(143,232,71,0.25); }
.metric-card.sky    { background: linear-gradient(135deg, rgba(56,191,255,0.12) 0%, rgba(56,191,255,0.04) 100%); border-color: rgba(56,191,255,0.25); }

.metric-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 3px;
}
.metric-card.cyan::before   { background: var(--cyan); }
.metric-card.purple::before { background: var(--violet); }
.metric-card.pink::before   { background: var(--rose); }
.metric-card.orange::before { background: var(--amber); }
.metric-card.lime::before   { background: var(--lime); }
.metric-card.sky::before    { background: var(--sky); }

.metric-card .metric-label {
  font-size: 0.71rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.4rem;
}
.metric-card.cyan   .metric-label { color: var(--cyan); }
.metric-card.purple .metric-label { color: var(--violet); }
.metric-card.pink   .metric-label { color: var(--rose); }
.metric-card.orange .metric-label { color: var(--amber); }
.metric-card.lime   .metric-label { color: var(--lime); }
.metric-card.sky    .metric-label { color: var(--sky); }

.metric-card .metric-value {
  font-family: var(--font-data);
  font-size: 2rem;
  font-weight: 500;
  color: var(--t1);
  line-height: 1;
  letter-spacing: -0.03em;
}
.metric-card .metric-delta { font-size: 0.78rem; color: var(--t2); margin-top: 0.35rem; }

/* ── STATUS PILLS — vivid, distinct ── */
.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  border: 1px solid transparent;
  white-space: nowrap;
  letter-spacing: 0.01em;
}
.pill-green  { background: rgba(143,232,71,0.15);  color: #8FE847; border-color: rgba(143,232,71,0.3); }
.pill-amber  { background: rgba(255,177,64,0.15);  color: #FFB140; border-color: rgba(255,177,64,0.3); }
.pill-red    { background: rgba(255,92,138,0.15);  color: #FF5C8A; border-color: rgba(255,92,138,0.3); }
.pill-blue   { background: rgba(56,191,255,0.15);  color: #38BFFF; border-color: rgba(56,191,255,0.3); }
.pill-purple { background: rgba(155,109,255,0.15); color: #BF9FFF; border-color: rgba(155,109,255,0.3); }
.pill-cyan   { background: rgba(0,240,208,0.15);   color: #00F0D0; border-color: rgba(0,240,208,0.3); }

/* ── QUALITY ── */
.quality-hero {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.25rem;
  border-radius: var(--r-lg);
  background: linear-gradient(135deg, rgba(155,109,255,0.08) 0%, rgba(0,240,208,0.05) 100%);
  border: 1px solid rgba(155,109,255,0.2);
  margin-bottom: 1rem;
}
.quality-score-ring {
  flex-shrink: 0;
  width: 112px; height: 112px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at center, var(--s1) 0 52%, transparent 53%),
              conic-gradient(var(--cyan) 0% 0%, rgba(255,255,255,0.06) 0% 100%);
  border: 1px solid rgba(0,240,208,0.3);
  text-align: center;
}
.quality-score-ring .score-value { font-family: var(--font-data); font-size: 1.9rem; font-weight: 500; color: var(--t1); line-height: 1; }
.quality-score-ring .score-label { display: block; font-size: 0.65rem; color: var(--cyan); text-transform: uppercase; letter-spacing: 0.12em; margin-top: 0.2rem; }
.quality-summary { flex: 1; min-width: 0; }
.quality-summary h4 { margin: 0 0 0.3rem; font-size: 0.95rem; font-weight: 600; color: var(--t1); }
.quality-summary p  { margin: 0; font-size: 0.86rem; color: var(--t2); line-height: 1.55; }
.quality-chip-list  { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.6rem; }
.quality-chip {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.28rem 0.6rem;
  border-radius: var(--r-sm);
  background: var(--s3);
  border: 1px solid var(--e1);
  color: var(--t2);
  font-size: 0.78rem; font-weight: 500;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0C0E18 0%, #0A0B14 100%) !important;
  border-right: 1px solid rgba(155,109,255,0.15) !important;
}
[data-testid="stSidebar"] .stRadio > label {
  color: var(--t3) !important; font-weight: 700 !important;
  font-size: 0.68rem !important; text-transform: uppercase !important;
  letter-spacing: 0.12em !important;
}
[data-testid="stSidebar"] .stRadio > div > div > label {
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: var(--r-md) !important;
  padding: 0.6rem 0.9rem !important;
  color: var(--t2) !important;
  font-weight: 500 !important; font-size: 0.84rem !important;
  transition: all 0.18s ease !important;
  margin-bottom: 0.2rem !important;
}
[data-testid="stSidebar"] .stRadio > div > div > label:hover {
  background: rgba(155,109,255,0.08) !important;
  color: var(--t1) !important;
  border-color: rgba(155,109,255,0.2) !important;
}
[data-testid="stSidebar"] .stRadio > div > div > label[data-selected="true"] {
  background: linear-gradient(90deg, rgba(155,109,255,0.18), rgba(0,240,208,0.08)) !important;
  border-color: rgba(155,109,255,0.35) !important;
  color: #BF9FFF !important;
  font-weight: 700 !important;
}

.sidebar-brand {
  padding: 0.85rem 1rem;
  border-radius: var(--r-lg);
  background: linear-gradient(135deg, rgba(155,109,255,0.12), rgba(0,240,208,0.06));
  border: 1px solid rgba(155,109,255,0.2);
  margin-bottom: 1rem;
}
.sidebar-brand-title { font-size: 1rem; font-weight: 700; color: var(--t1); letter-spacing: -0.02em; display: flex; align-items: center; gap: 0.5rem; }
.sidebar-brand-subtitle { font-size: 0.68rem; color: var(--violet); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.2rem; opacity: 0.8; }

.sidebar-page-meta {
  padding: 0.75rem 0.9rem;
  border-radius: var(--r-md);
  border: 1px solid var(--e0);
  background: var(--s1);
  margin-bottom: 0.75rem;
}
.sidebar-page-meta h4 { margin: 0 0 0.2rem; font-size: 0.88rem; color: var(--t1); font-weight: 600; }
.sidebar-page-meta p  { margin: 0; color: var(--t2); font-size: 0.79rem; line-height: 1.4; }
.sidebar-section-label {
  font-size: 0.67rem; color: var(--t3);
  text-transform: uppercase; letter-spacing: 0.14em;
  font-weight: 700; padding: 0.5rem 0 0.25rem;
}

/* ── BUTTONS ── */
.stButton > button {
  border-radius: var(--r-md) !important;
  font-family: var(--font-ui) !important;
  font-weight: 700 !important;
  font-size: 0.88rem !important;
  padding: 0.55rem 1.25rem !important;
  transition: all 0.18s ease !important;
  letter-spacing: 0.01em;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--violet), var(--cyan)) !important;
  color: #050810 !important;
  border: none !important;
}
.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 24px rgba(155,109,255,0.4) !important;
  filter: brightness(1.05);
}
.stButton > button[kind="secondary"] {
  background: var(--s2) !important;
  color: var(--t1) !important;
  border: 1px solid var(--e1) !important;
}
.stButton > button[kind="secondary"]:hover {
  background: var(--s3) !important;
  border-color: rgba(155,109,255,0.3) !important;
  color: #BF9FFF !important;
}

/* ── INPUTS ── */
.stTextInput > div > div > input,
.stSelectbox > div > div > div {
  background: var(--s2) !important;
  border: 1px solid var(--e1) !important;
  border-radius: var(--r-md) !important;
  color: var(--t1) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.88rem !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 3px rgba(155,109,255,0.15) !important;
}

/* ── TABLES ── */
.stDataFrame { border-radius: var(--r-lg) !important; overflow: hidden !important; }
.stDataFrame table { background: var(--s1) !important; border: 1px solid var(--e1) !important; }
.stDataFrame th {
  background: var(--s2) !important;
  color: var(--cyan) !important;
  font-weight: 700 !important;
  font-size: 0.73rem !important;
  text-transform: uppercase; letter-spacing: 0.07em;
  border-bottom: 1px solid rgba(0,240,208,0.15) !important;
  padding: 0.65rem 0.9rem !important;
}
.stDataFrame td {
  color: var(--t2) !important;
  border-bottom: 1px solid var(--e0) !important;
  padding: 0.55rem 0.9rem !important;
  font-size: 0.84rem !important;
  font-family: var(--font-data) !important;
}
.stDataFrame tr:hover td { background: rgba(155,109,255,0.04) !important; }

/* ── PROGRESS ── */
.stProgress > div > div {
  background: linear-gradient(90deg, var(--violet), var(--cyan), var(--lime)) !important;
  border-radius: 999px !important;
}
.stProgress > div { background: var(--e1) !important; border-radius: 999px !important; }

/* ── SLIDERS ── */
.stSlider [role="slider"] { background: var(--violet) !important; }

/* ── EXPANDER ── */
.stExpander { border: 1px solid var(--e1) !important; border-radius: var(--r-lg) !important; background: var(--s1) !important; overflow: hidden; }
.stExpander > div:first-child { background: var(--s2) !important; border-bottom: 1px solid var(--e1) !important; }

/* ── ALERTS ── */
.stAlert { border-radius: var(--r-md) !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(155,109,255,0.3); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(155,109,255,0.5); }

/* ── SPINNER ── */
.stSpinner > div > div { border-top-color: var(--cyan) !important; }

/* ── EMPTY STATES ── */
.empty-state { text-align: center; padding: 3.5rem 2rem; }
.empty-state-icon { font-size: 2.8rem; margin-bottom: 1rem; display: block; opacity: 0.6; }
.empty-state h3 { color: var(--t1); font-size: 1.15rem; font-weight: 700; margin-bottom: 0.4rem; }
.empty-state p  { color: var(--t2); font-size: 0.9rem; max-width: 360px; margin: 0 auto; }

/* ── REVIEW CARDS ── */
.review-card {
  background: var(--s1);
  border: 1px solid var(--e1);
  border-radius: var(--r-lg);
  padding: 1.1rem 1.25rem;
  margin-bottom: 0.75rem;
  transition: border-color 0.2s;
}
.review-card:hover { border-color: rgba(155,109,255,0.35); }

/* ── NETWORK GRAPH ── */
.network-container { background: var(--s1); border: 1px solid var(--e1); border-radius: var(--r-lg); overflow: hidden; }

/* ── PIPELINE STEPS ── */
.pipeline-steps {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.5rem; padding: 1.25rem 1.5rem;
  background: linear-gradient(90deg, rgba(155,109,255,0.08) 0%, rgba(0,240,208,0.05) 50%, rgba(255,92,138,0.05) 100%);
  border-radius: var(--r-lg); border: 1px solid rgba(155,109,255,0.18); margin: 1.25rem 0;
}
.pipeline-step { text-align: center; flex: 1; }
.step-icon { font-size: 1.6rem; display: block; margin-bottom: 0.25rem; }
.step-label { font-size: 0.7rem; font-weight: 700; color: var(--t3); text-transform: uppercase; letter-spacing: 0.08em; }
.pipeline-arrow { color: var(--violet); font-size: 1.1rem; opacity: 0.6; }

/* ── UPLOAD ZONE ── */
.upload-zone {
  border: 1px dashed rgba(155,109,255,0.35) !important;
  background: rgba(155,109,255,0.05) !important;
  transition: all 0.2s ease !important;
}
.upload-zone:hover {
  border-color: rgba(155,109,255,0.6) !important;
  background: rgba(155,109,255,0.09) !important;
}

/* ── UTILITY ── */
.muted      { color: var(--t2); font-size: 0.88rem; line-height: 1.5; }
.small-note { font-size: 0.79rem; color: var(--t3); line-height: 1.5; }
hr { border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(155,109,255,0.3), transparent); margin: 1.25rem 0; }

/* ── RESULTS ASK PANEL ── */
.results-ask-panel {
  padding: 1rem 1.1rem; border-radius: var(--r-lg);
  border: 1px solid rgba(0,240,208,0.2);
  background: linear-gradient(135deg, rgba(0,240,208,0.07), rgba(155,109,255,0.05));
}

/* ── FOCUS ── */
*:focus-visible { outline: 2px solid var(--violet) !important; outline-offset: 2px !important; }

/* ── DASHBOARD ENTRANCE ── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}
.dashboard-section { animation: fadeUp 0.4s ease-out both; }
.dashboard-section:nth-child(2) { animation-delay: 0.08s; }
.dashboard-section:nth-child(3) { animation-delay: 0.16s; }
.dashboard-section:nth-child(4) { animation-delay: 0.24s; }
</style>
"""


# ── Session state init ──────────────────────────────────────────────────────
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
if "ai_explanations" not in st.session_state:
    st.session_state.ai_explanations = {}
if "quality_insights" not in st.session_state:
    st.session_state.quality_insights = {}
if "ask_apexforge_query" not in st.session_state:
    st.session_state.ask_apexforge_query = ""
if "ai_service_ready" not in st.session_state:
    st.session_state.ai_service_ready = None

st.markdown(CSS, unsafe_allow_html=True)


# ── Helpers ─────────────────────────────────────────────────────────────────
def normalize_col(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def safe_text(value: Any, default: str = "N/A", escape_html: bool = False) -> str:
    if value is None:
        out = default
    else:
        try:
            if pd.isna(value):
                out = default
            else:
                out = str(value)
        except Exception:
            out = default
    if escape_html:
        out = html.escape(out)
    return out


def format_confidence(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "N/A"


def _normalize_series_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def build_quality_profile(df: pd.DataFrame) -> Dict[str, Any]:
    profile: Dict[str, Any] = {
        "total_rows": int(len(df)) if df is not None else 0,
        "total_columns": int(len(df.columns)) if df is not None else 0,
        "missing_values": 0, "missing_pct": 0.0,
        "invalid_pan_count": 0, "invalid_gstin_count": 0,
        "probable_duplicate_density": 0.0,
        "suspicious_regions": [], "top_missing_fields": [],
        "state_counts": {}, "district_counts": {},
    }

    if df is None or df.empty:
        return profile

    total_cells = max(1, len(df) * max(1, len(df.columns)))
    profile["missing_values"] = int(df.isna().sum().sum())
    profile["missing_pct"] = round((profile["missing_values"] / total_cells) * 100.0, 2)

    required_subset = [col for col in REQUIRED_COLUMNS if col in df.columns]
    if required_subset:
        missing_by_field = df[required_subset].isna().sum().sort_values(ascending=False)
        profile["top_missing_fields"] = [f"{idx}: {int(value)}" for idx, value in missing_by_field.head(3).items() if int(value) > 0]

    if "pan" in df.columns:
        pan_series = _normalize_series_text(df["pan"]).str.upper()
        pan_valid = pan_series.str.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", na=False)
        profile["invalid_pan_count"] = int((pan_series.ne("") & ~pan_valid).sum())

    if "gstin" in df.columns:
        gstin_series = _normalize_series_text(df["gstin"]).str.upper()
        gstin_valid = gstin_series.str.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", na=False)
        profile["invalid_gstin_count"] = int((gstin_series.ne("") & ~gstin_valid).sum())

    duplicate_scores: List[float] = []
    if "pan" in df.columns:
        pan_ne = _normalize_series_text(df["pan"])
        pan_ne = pan_ne[pan_ne.ne("")]
        if not pan_ne.empty:
            duplicate_scores.append(float(pan_ne.duplicated(keep=False).mean() * 100.0))
    if "gstin" in df.columns:
        g_ne = _normalize_series_text(df["gstin"])
        g_ne = g_ne[g_ne.ne("")]
        if not g_ne.empty:
            duplicate_scores.append(float(g_ne.duplicated(keep=False).mean() * 100.0))
    name_subset = [col for col in ["business_name", "state", "district"] if col in df.columns]
    if name_subset:
        nf = df[name_subset].fillna("").astype(str)
        nf = nf[(nf != "").any(axis=1)]
        if not nf.empty:
            duplicate_scores.append(float(nf.duplicated(keep=False).mean() * 100.0))
    profile["probable_duplicate_density"] = round(max(duplicate_scores) if duplicate_scores else 0.0, 2)

    if "state" in df.columns:
        sc = _normalize_series_text(df["state"]).replace("", pd.NA).value_counts(dropna=True)
        profile["state_counts"] = {str(k): int(v) for k, v in sc.head(10).items()}

    if "district" in df.columns:
        dc = _normalize_series_text(df["district"]).replace("", pd.NA).value_counts(dropna=True)
        profile["district_counts"] = {str(k): int(v) for k, v in dc.head(10).items()}

    suspicious_regions: List[str] = []
    state_code_map = {state.lower(): code for state, code in DataCleaner.STATE_CODES.items()}
    state_code_map.update({code.lower(): code for code in DataCleaner.STATE_CODES.values()})
    if "state" in df.columns and "gstin" in df.columns:
        mismatch_counts: Dict[str, int] = {}
        states = _normalize_series_text(df["state"]).str.lower()
        gstins = _normalize_series_text(df["gstin"]).str.upper()
        for sv, gv in zip(states, gstins):
            if not sv or not gv or len(gv) < 2:
                continue
            sc2 = state_code_map.get(sv)
            if sc2 and gv[:2] != sc2:
                mismatch_counts[sv.title()] = mismatch_counts.get(sv.title(), 0) + 1
        if mismatch_counts:
            suspicious_regions.extend([s for s, _ in sorted(mismatch_counts.items(), key=lambda x: x[1], reverse=True)[:3]])

    if not suspicious_regions and profile["state_counts"]:
        suspicious_regions = list(profile["state_counts"].keys())[:3]
    if not suspicious_regions and profile["district_counts"]:
        suspicious_regions = list(profile["district_counts"].keys())[:3]

    profile["suspicious_regions"] = suspicious_regions[:3]
    profile["quality_score"] = _calculate_quality_score(profile)
    return profile


def _calculate_quality_score(profile: Dict[str, Any]) -> int:
    total_rows = max(1, int(profile.get("total_rows") or 0))
    missing_pct = float(profile.get("missing_pct") or 0.0)
    invalid_pan = int(profile.get("invalid_pan_count") or 0)
    invalid_gstin = int(profile.get("invalid_gstin_count") or 0)
    duplicate_density = float(profile.get("probable_duplicate_density") or 0.0)

    penalty = min(40.0, missing_pct * 0.4)
    penalty += min(20.0, (invalid_pan / total_rows) * 100.0 * 0.15)
    penalty += min(20.0, (invalid_gstin / total_rows) * 100.0 * 0.15)
    penalty += min(20.0, duplicate_density * 0.5)
    return int(max(0, min(100, 100 - penalty)))


def quality_profile_signature(profile: Dict[str, Any]) -> str:
    payload = json.dumps(profile, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def apply_ask_apexforge_filters(df: pd.DataFrame, parsed: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty or not parsed:
        return df
    filtered = df.copy()
    filters = parsed.get("filters") or {}

    state = filters.get("state")
    if state and "state" in filtered.columns:
        filtered = filtered[filtered["state"].astype(str).str.lower() == str(state).lower()]
    district = filters.get("district")
    if district and "district" in filtered.columns:
        filtered = filtered[filtered["district"].astype(str).str.lower().str.contains(str(district).lower(), na=False)]
    status = filters.get("business_status")
    if status and "business_status" in filtered.columns:
        filtered = filtered[filtered["business_status"].astype(str).str.lower() == str(status).lower()]
    decision = filters.get("match_decision")
    if decision and "match_decision" in filtered.columns:
        filtered = filtered[filtered["match_decision"].astype(str).str.lower() == str(decision).lower()]
    tier = filters.get("match_tier")
    if tier and "match_tier" in filtered.columns:
        filtered = filtered[filtered["match_tier"].astype(str).str.lower() == str(tier).lower()]
    if filters.get("group_only") and "group_size" in filtered.columns:
        filtered = filtered[filtered["group_size"] > 1]
    min_c = filters.get("min_confidence")
    if min_c is not None and "match_confidence" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["match_confidence"], errors="coerce").fillna(0) >= float(min_c)]
    max_c = filters.get("max_confidence")
    if max_c is not None and "match_confidence" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["match_confidence"], errors="coerce").fillna(0) <= float(max_c)]
    search_terms = [str(t).strip().lower() for t in (filters.get("search_terms") or []) if str(t).strip()]
    if search_terms:
        searchable = [c for c in ["ubid", "business_name", "pan", "gstin", "district", "state", "department", "business_status"] if c in filtered.columns]
        if searchable:
            mask = pd.Series(False, index=filtered.index)
            for term in search_terms:
                tm = pd.Series(False, index=filtered.index)
                for col in searchable:
                    tm = tm | filtered[col].astype(str).str.lower().str.contains(term, na=False)
                mask = mask | tm
            filtered = filtered[mask]
    sbc = filters.get("sort_by_confidence")
    if sbc and "match_confidence" in filtered.columns:
        filtered = filtered.assign(_c=pd.to_numeric(filtered["match_confidence"], errors="coerce").fillna(0))
        filtered = filtered.sort_values("_c", ascending=str(sbc).lower() == "asc").drop(columns=["_c"])
    limit = filters.get("limit")
    if isinstance(limit, int) and limit > 0:
        filtered = filtered.head(limit)
    return filtered


def render_quality_insights_panel(profile: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None) -> None:
    st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
    st.markdown("**Dataset Quality**")

    score = int(profile.get("quality_score") or 0)
    score_label = "Healthy" if score >= 85 else "Watch closely" if score >= 70 else "Needs cleanup"
    score_pct = f"{score}%"
    score_style = (
        f"radial-gradient(circle at center, #131720 0 52%, transparent 53%), "
        f"conic-gradient(#00E5C3 {score}%, rgba(255,255,255,0.06) 0)"
    )

    st.markdown(
        f"""
        <div class="quality-hero">
            <div class="quality-score-ring" style="background: {score_style};">
                <div>
                    <div class="score-value">{score}</div>
                    <span class="score-label">/ 100</span>
                </div>
            </div>
            <div class="quality-summary">
                <h4>{score_label}</h4>
                <p>{int(profile.get('total_rows') or 0):,} rows · {float(profile.get('missing_pct') or 0):.1f}% missing · {float(profile.get('probable_duplicate_density') or 0):.1f}% duplicate density</p>
                <div class="quality-chip-list">
                    <span class="quality-chip">Rows {int(profile.get('total_rows') or 0):,}</span>
                    <span class="quality-chip">Cols {int(profile.get('total_columns') or 0)}</span>
                    <span class="quality-chip">Missing {float(profile.get('missing_pct') or 0):.1f}%</span>
                    <span class="quality-chip">Dups {float(profile.get('probable_duplicate_density') or 0):.1f}%</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Missing Cells", f"{int(profile.get('missing_values') or 0):,}", "orange"), unsafe_allow_html=True)
    c2.markdown(metric_card("Invalid PAN", f"{int(profile.get('invalid_pan_count') or 0):,}", "pink"), unsafe_allow_html=True)
    c3.markdown(metric_card("Invalid GSTIN", f"{int(profile.get('invalid_gstin_count') or 0):,}", "purple"), unsafe_allow_html=True)
    c4.markdown(metric_card("Dup Density", f"{float(profile.get('probable_duplicate_density') or 0):.1f}%", "cyan"), unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Top Missing Fields**")
        mf = profile.get("top_missing_fields") or []
        if mf:
            chips = " ".join(f"<span class='quality-chip'>{safe_text(item, escape_html=True)}</span>" for item in mf[:3])
            st.markdown(f"<div class='quality-chip-list'>{chips}</div>", unsafe_allow_html=True)
        else:
            st.caption("No dominant missing-field pattern.")
    with right:
        st.markdown("**Suspicious Regions**")
        sr = profile.get("suspicious_regions") or []
        if sr:
            chips = " ".join(f"<span class='quality-chip'>{safe_text(item, escape_html=True)}</span>" for item in sr[:3])
            st.markdown(f"<div class='quality-chip-list'>{chips}</div>", unsafe_allow_html=True)
        else:
            st.caption("No region anomalies detected.")

    if ai_result:
        with st.expander("AI quality insight", expanded=False):
            src = safe_text(ai_result.get("source", "fallback"))
            cls = "pill-cyan" if ai_result.get("source") == "gemini" else "pill-blue"
            st.markdown(f"<span class='stat-pill {cls}'>{src.title()}</span>", unsafe_allow_html=True)
            if ai_result.get("summary"):
                st.write(ai_result["summary"])
            bullets = ai_result.get("bullets") or []
            if bullets:
                st.markdown("\n".join(f"- {safe_text(b, escape_html=True)}" for b in bullets[:3]))
            risks = ai_result.get("risks") or []
            if risks:
                chips = " ".join(f"<span class='quality-chip'>Risk: {safe_text(r, escape_html=True)}</span>" for r in risks[:3])
                st.markdown(f"<div class='quality-chip-list' style='margin-top:0.5rem;'>{chips}</div>", unsafe_allow_html=True)
            recs = ai_result.get("recommendations") or []
            if recs:
                chips = " ".join(f"<span class='quality-chip'>Fix: {safe_text(r, escape_html=True)}</span>" for r in recs[:3])
                st.markdown(f"<div class='quality-chip-list' style='margin-top:0.5rem;'>{chips}</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def get_ai_service() -> Optional[Any]:
    if AIReviewService is None:
        st.session_state.ai_service_ready = False
        return None
    service = st.session_state.get("ai_service")
    if service is None:
        try:
            service = AIReviewService()
            st.session_state.ai_service = service
        except Exception as exc:
            logger.warning("AI review service unavailable: %s", exc)
            st.session_state.ai_service_ready = False
            return None
    try:
        st.session_state.ai_service_ready = bool(service.is_available())
    except Exception:
        st.session_state.ai_service_ready = False
    return service


def render_ai_review_result(result: Dict[str, Any]) -> None:
    if not result:
        return
    recommendation = str(result.get("recommendation", "Unknown")).strip() or "Unknown"
    badge_class = {
        "merge": "pill-cyan", "review": "pill-amber",
        "keepseparate": "pill-purple", "unknown": "pill-blue",
    }.get(recommendation.lower(), "pill-blue")
    source = safe_text(result.get("source", "fallback"))
    summary = safe_text(result.get("confidence_summary"))
    uncertainty = safe_text(result.get("uncertainty"))
    bullets = result.get("bullets") or []
    evidence = result.get("evidence") or []
    score = safe_text(result.get("match_score"))
    cached_badge = '<span class="stat-pill pill-blue">Cached</span>' if result.get("cached") else ""

    st.markdown(
        f"""<div style="margin-top:0.75rem; padding:0.85rem 1rem; border-radius:12px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.02);">
            <div style="display:flex; flex-wrap:wrap; gap:0.4rem; align-items:center; margin-bottom:0.6rem;">
                <span class="stat-pill {badge_class}">AI: {recommendation}</span>
                <span class="stat-pill pill-blue">Score {score}</span>
                <span class="stat-pill pill-purple">via {source}</span>
                {cached_badge}
            </div>""",
        unsafe_allow_html=True,
    )
    if bullets:
        st.markdown("\n".join(f"- {safe_text(b, escape_html=True)}" for b in bullets[:3]))
    if summary:
        st.caption(f"Confidence: {summary}")
    if uncertainty:
        st.caption(f"Uncertainty: {uncertainty}")
    if evidence:
        st.caption(f"Evidence: {', '.join(safe_text(e) for e in evidence[:3])}")
    st.markdown("</div>", unsafe_allow_html=True)


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
    st.session_state.ai_explanations = {}
    st.session_state.quality_insights = {}
    st.session_state.ask_apexforge_query = ""


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


def ensure_database_manager() -> Optional[Any]:
    db_manager = st.session_state.get("db_manager")
    if db_manager is not None:
        return db_manager
    if get_db_manager is None:
        return None
    if not os.getenv("DATABASE_URL"):
        return None
    return init_database()


def compute_local_stats(df, matches, groups, assignments) -> Dict[str, Any]:
    if df is None or df.empty:
        return dict(total_records=0, ubids_generated=0, matches_found=0, pending_reviews=0,
                    active_count=0, dormant_count=0, closed_count=0, match_groups=0,
                    auto_merge=0, needs_review=0, new_records=0)
    status_counts = df["business_status"].value_counts(dropna=False).to_dict() if "business_status" in df.columns else {}
    decisions = df["match_decision"].value_counts(dropna=False).to_dict() if "match_decision" in df.columns else {}
    return dict(
        total_records=int(len(df)),
        ubids_generated=int(df["ubid"].nunique()) if "ubid" in df.columns else int(len(df)),
        matches_found=int(len(matches)),
        pending_reviews=int(sum(1 for m in matches if getattr(m, "decision", "") == "NeedsReview")),
        active_count=int(status_counts.get("Active", 0)),
        dormant_count=int(status_counts.get("Dormant", 0)),
        closed_count=int(status_counts.get("Closed", 0)),
        match_groups=int(len(groups)),
        auto_merge=int(decisions.get("AutoMerge", 0)),
        needs_review=int(decisions.get("NeedsReview", 0)),
        new_records=int(decisions.get("New", 0)),
    )


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

    db_manager = ensure_database_manager()
    use_db_pipeline = DataService is not None and db_manager is not None

    if use_db_pipeline:
        status_text.write("Running database-backed pipeline...")
        try:
            data_service = DataService(db_manager=db_manager)
            result = data_service.process_full_pipeline(df, batch_id=batch_id)
            df_final = attach_group_summary(result["df"], result["groups"])
            matches = result["matches"]
            groups = result["groups"]
            assignments = result["assignments"]
            progress.progress(90)
        except Exception as exc:
            logger.warning("Database pipeline failed, falling back to local mode: %s", exc)
            use_db_pipeline = False
            matches = []
            groups = []
            assignments = {}

    if not use_db_pipeline:
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
                    "ubid": ubid, "is_master": True,
                    "confidence": 100.0, "tier": "New",
                    "matched_fields": [], "decision": "New",
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

    if "business_status" in df_final.columns:
        counts = df_final["business_status"].value_counts(dropna=False).to_dict()
        total = int(len(df_final)) or 1
        st.session_state.status_summary = {
            "counts": {
                "active": int(counts.get("Active", 0)),
                "dormant": int(counts.get("Dormant", 0)),
                "closed": int(counts.get("Closed", 0)),
            },
            "percentages": {
                "active": (int(counts.get("Active", 0)) / total) * 100.0,
                "dormant": (int(counts.get("Dormant", 0)) / total) * 100.0,
                "closed": (int(counts.get("Closed", 0)) / total) * 100.0,
            },
            "total": int(len(df_final)),
        }
    else:
        st.session_state.status_summary = {}

    st.session_state.processing_complete = True
    st.session_state.last_error = None
    progress.progress(100)
    status_text.empty()
    st.success(f"Processing complete — Batch ID: {batch_id}")


def metric_card(label: str, value: Any, variant: str = "cyan", delta: Optional[str] = None) -> str:
    delta_html = f'<div class="metric-delta">{delta}</div>' if delta else ""
    return f"""
    <div class="metric-card {variant}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """


def render_header() -> None:
    if st.session_state.ai_service_ready is None:
        try:
            get_ai_service()
        except Exception:
            pass

    db_status = (
        '<span class="stat-pill pill-cyan">Database</span>'
        if st.session_state.db_initialized
        else '<span class="stat-pill pill-amber">Local Mode</span>'
    )
    ai_status = (
        '<span class="stat-pill pill-cyan">AI Ready</span>'
        if st.session_state.ai_service_ready
        else '<span class="stat-pill pill-purple">AI Idle</span>'
        if st.session_state.ai_service_ready is None
        else '<span class="stat-pill pill-amber">AI Offline</span>'
    )
    batch_status = (
        f'<span class="stat-pill pill-blue">{html.escape(str(st.session_state.batch_id))}</span>'
        if st.session_state.processing_complete and st.session_state.batch_id
        else ""
    )
    st.markdown(
        f"""
        <div class="hero">
            <h1>ApexForge AI</h1>
            <p>Unified Business Identity System — clean, match, assign, and explore at scale.</p>
            <div class="hero-badges">
                {db_status}{ai_status}{batch_status}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    with st.sidebar:
        nav_options = [
            ("Upload",        "Upload a CSV and inspect schema mapping"),
            ("Dashboard",     "Batch overview, match health, quality trends"),
            ("Results",       "Filter records and ask ApexForge AI"),
            ("UBID Explorer", "Search and inspect assigned identities"),
            ("Network Graph", "Visualize clusters and match links"),
            ("Review Queue",  "Review ambiguous match decisions"),
            ("Analytics",     "Batch metrics and distributions"),
        ]
        nav_labels = [label for label, _ in nav_options]
        page_copy = {label: copy for label, copy in nav_options}
        nav_index = 0 if not st.session_state.processing_complete else 1

        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-title">🏢 ApexForge AI</div>
                <div class="sidebar-brand-subtitle">Unified Business Identity</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        status_html = (
            '<span class="stat-pill pill-cyan">DB Connected</span>'
            if st.session_state.db_initialized
            else '<span class="stat-pill pill-amber">Local Mode</span>'
        )
        batch_html = (
            f'<span class="stat-pill pill-blue">{html.escape(safe_text(st.session_state.batch_id))}</span>'
            if st.session_state.processing_complete
            else '<span class="stat-pill pill-purple">Upload first</span>'
        )

        st.markdown(
            f"""
            <div class="sidebar-page-meta">
                <div style="display:flex; flex-wrap:wrap; gap:0.35rem; margin-bottom:0.5rem;">
                    {status_html}{batch_html}
                </div>
                <h4>{safe_text(nav_labels[nav_index])}</h4>
                <p>{safe_text(page_copy[nav_labels[nav_index]])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        db_col1, db_col2 = st.columns(2)
        with db_col1:
            if st.button("Connect DB", use_container_width=True, type="secondary"):
                init_database()
        with db_col2:
            if st.button("Reset", use_container_width=True, type="secondary"):
                reset_processing_state()
                st.rerun()

        st.markdown("<div class='sidebar-section-label'>Navigate</div>", unsafe_allow_html=True)
        icon_map = {
            "Upload": "📤 Upload", "Dashboard": "📊 Dashboard", "Results": "🔍 Results",
            "UBID Explorer": "🎯 UBID Explorer", "Network Graph": "🕸️ Network Graph",
            "Review Queue": "📝 Review Queue", "Analytics": "📈 Analytics",
        }
        selected = st.radio(
            "", nav_labels, index=nav_index,
            format_func=lambda v: icon_map.get(v, v),
            label_visibility="collapsed",
        )

        st.markdown(
            f"""
            <div class="sidebar-page-meta" style="margin-top:0.75rem;">
                <h4>{safe_text(selected)}</h4>
                <p>{safe_text(page_copy.get(selected, ""))}</p>
            </div>
            <div class="small-note" style="border-left:2px solid rgba(0,229,195,0.3); padding-left:0.7rem; margin-top:0.75rem;">
                Drop a CSV once, then navigate freely through all views.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected


def render_upload_page() -> None:
    st.markdown("<div class='section-title'>Upload Business Data</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Clean · Match · Assign · Review · Export</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="pipeline-steps">
        <div class="pipeline-step"><span class="step-icon">📤</span><div class="step-label">Upload</div></div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-step"><span class="step-icon">🧹</span><div class="step-label">Clean</div></div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-step"><span class="step-icon">🔍</span><div class="step-label">Match</div></div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-step"><span class="step-icon">🎯</span><div class="step-label">UBID</div></div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-step"><span class="step-icon">📊</span><div class="step-label">Explore</div></div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        st.markdown("<div class='surface upload-zone'>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload CSV (max 50 MB)",
            type=["csv"],
            help="Auto-maps common column name variations.",
        )

        if uploaded_file is not None:
            # Create processing animation container
            processing_container = st.container()

            with processing_container:
                # Show ultra-fast processing animation with loading bar
                st.markdown("""
                <div class="processing-animation">
                    <div class="pulse-loader"></div>
                    <div class="processing-content">
                        <div class="processing-text">
                            <h3>🚀 Ultra-Fast Processing</h3>
                            <p>Analyzing file with quantum-speed algorithms...</p>
                        </div>
                        <div class="loading-bar-container">
                            <div class="loading-bar">
                                <div class="loading-progress"></div>
                                <div class="loading-glow"></div>
                            </div>
                            <div class="loading-percentage">0%</div>
                        </div>
                    </div>
                </div>
                <style>
                .processing-animation {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 25px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 15px;
                    margin: 15px 0;
                    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
                }
                .pulse-loader {
                    width: 45px;
                    height: 45px;
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-top: 4px solid #00d4ff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-right: 25px;
                    box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .processing-content {
                    flex: 1;
                }
                .processing-text h3 {
                    margin: 0 0 8px 0;
                    color: white;
                    font-size: 20px;
                    font-weight: 600;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                }
                .processing-text p {
                    margin: 0 0 15px 0;
                    color: rgba(255,255,255,0.9);
                    font-size: 14px;
                }
                .loading-bar-container {
                    position: relative;
                    margin-top: 10px;
                }
                .loading-bar {
                    width: 100%;
                    height: 8px;
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 10px;
                    overflow: hidden;
                    position: relative;
                }
                .loading-progress {
                    height: 100%;
                    background: linear-gradient(90deg, #00d4ff, #00ff88);
                    border-radius: 10px;
                    width: 0%;
                    animation: loadingProgress 2s ease-in-out infinite;
                    box-shadow: 0 0 10px rgba(0, 212, 255, 0.8);
                }
                .loading-glow {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.8), transparent);
                    border-radius: 10px;
                    animation: loadingGlow 2s ease-in-out infinite;
                }
                @keyframes loadingProgress {
                    0% { width: 0%; }
                    50% { width: 75%; }
                    100% { width: 100%; }
                }
                @keyframes loadingGlow {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }
                .loading-percentage {
                    position: absolute;
                    top: -25px;
                    right: 0;
                    color: #00ff88;
                    font-weight: bold;
                    font-size: 14px;
                    animation: percentageUpdate 2s ease-in-out infinite;
                }
                @keyframes percentageUpdate {
                    0% { content: "0%"; }
                    25% { content: "25%"; }
                    50% { content: "50%"; }
                    75% { content: "75%"; }
                    100% { content: "100%"; }
                }
                </style>
                """, unsafe_allow_html=True)

            # Simulate ultra-fast processing with progress
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Phase 1: File validation
            progress_bar.progress(20)
            status_text.text("🔍 Validating file format...")
            import time
            time.sleep(0.1)  # Brief pause for effect

            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > MAX_UPLOAD_SIZE_MB:
                st.error(f"File too large ({file_size_mb:.1f} MB). Max: {MAX_UPLOAD_SIZE_MB} MB.")
                st.markdown("</div>", unsafe_allow_html=True)
                return

            # Phase 2: File parsing
            progress_bar.progress(40)
            status_text.text("📊 Parsing CSV structure...")
            time.sleep(0.1)

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
                    parse_errors.append(f"Parser #{i}: only {len(candidate.columns)} columns")
                except Exception as exc:
                    parse_errors.append(f"Parser #{i}: {str(exc)[:120]}")

            if df is None:
                st.error("Could not parse the uploaded file.")
                with st.expander("Parser errors"):
                    for err in parse_errors:
                        st.write(err)
                st.markdown("</div>", unsafe_allow_html=True)
                return

            # Phase 3: Column mapping
            progress_bar.progress(60)
            status_text.text("🗺️ Mapping intelligent columns...")
            time.sleep(0.1)

            mapped, detected, missing = auto_map_columns(df)

            # Phase 4: Data analysis
            progress_bar.progress(80)
            status_text.text("🧠 Analyzing data patterns...")
            time.sleep(0.1)

            # Phase 5: Complete
            progress_bar.progress(100)
            status_text.text("✨ Processing complete!")
            time.sleep(0.2)

            # Clear processing animation
            processing_container.empty()

            # Show success metrics with enhanced styling
            st.markdown("""
            <div class="success-metrics">
                <h4>🎯 Ultra-Fast Processing Complete</h4>
                <p>File processed in <strong>quantum time</strong> with AI-powered analysis</p>
            </div>
            <style>
            .success-metrics {
                background: linear-gradient(135deg, #00d4ff 0%, #0066cc 100%);
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
                text-align: center;
            }
            .success-metrics h4 {
                margin: 0 0 5px 0;
                font-size: 16px;
            }
            .success-metrics p {
                margin: 0;
                font-size: 14px;
                opacity: 0.9;
            }
            </style>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(metric_card("Rows", f"{len(mapped):,}", "cyan"), unsafe_allow_html=True)
            m2.markdown(metric_card("Columns", len(mapped.columns), "purple"), unsafe_allow_html=True)
            m3.markdown(metric_card("Mapped", len(detected), "pink"), unsafe_allow_html=True)
            m4.markdown(metric_card("Missing", len(missing), "orange"), unsafe_allow_html=True)

            if detected:
                with st.expander("Auto-mapped columns", expanded=False):
                    for item in detected:
                        st.write(f"• {item}")
            if missing:
                st.info(f"Blank columns created for: {', '.join(missing)}")

            with st.expander("Preview data", expanded=True):
                st.dataframe(mapped.head(10), use_container_width=True)

            quality_profile = build_quality_profile(mapped)
            quality_key = quality_profile_signature(quality_profile)
            quality_ai_result = st.session_state.quality_insights.get(quality_key)
            ai_service = get_ai_service()
            if quality_ai_result is None and ai_service is not None and ai_service.is_available():
                with st.spinner("Generating dataset quality insight..."):
                    try:
                        quality_ai_result = ai_service.analyze_data_quality(quality_profile, explicit=True)
                        st.session_state.quality_insights[quality_key] = quality_ai_result
                    except Exception as exc:
                        logger.warning("Dataset quality insight failed: %s", exc)

            render_quality_insights_panel(quality_profile, quality_ai_result)

            st.markdown("<hr>", unsafe_allow_html=True)
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
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("**Expected columns**")
        st.code(", ".join(REQUIRED_COLUMNS))
        st.caption("The app tolerates missing columns but performs best with the full schema.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard() -> None:
    st.markdown("<div class='section-title'>Dashboard</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">📊</span>
            <h3>Dashboard Locked</h3>
            <p>Process a file first to unlock the dashboard.</p>
        </div>""", unsafe_allow_html=True)
        return

    df = st.session_state.df_processed
    stats = compute_local_stats(df, st.session_state.matches, st.session_state.match_groups, st.session_state.ubid_assignments)

    total = stats["total_records"] or 1
    match_rate = (stats["matches_found"] / total) * 100
    dup_rate = (stats["auto_merge"] / total) * 100 if total else 0
    avg_confidence = 0.0
    if "match_confidence" in df.columns and not df["match_confidence"].isna().all():
        avg_confidence = float(df["match_confidence"].mean())

    # Batch overview banner
    st.markdown(
        f"""<div class="surface" style="margin-bottom: 1rem;">
            <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:1rem;">
                <div>
                    <div style="font-size:0.72rem; font-weight:700; color:var(--t3); text-transform:uppercase; letter-spacing:0.12em; margin-bottom:0.3rem;">Batch Overview</div>
                    <div style="font-size:1.2rem; font-weight:700; color:var(--t1); font-family:var(--font-data);">{safe_text(st.session_state.batch_id, 'Current Batch')}</div>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
                    <span class="stat-pill pill-cyan">{stats['total_records']:,} records</span>
                    <span class="stat-pill pill-purple">{stats['ubids_generated']:,} UBIDs</span>
                    <span class="stat-pill pill-amber">{stats['needs_review']:,} pending review</span>
                    <span class="stat-pill pill-blue">{stats['match_groups']:,} groups</span>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # KPIs
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Total Records",   f"{stats['total_records']:,}", "cyan"),   unsafe_allow_html=True)
    c2.markdown(metric_card("UBIDs Generated", f"{stats['ubids_generated']:,}", "purple"), unsafe_allow_html=True)
    c3.markdown(metric_card("Match Rate",      f"{match_rate:.1f}%", "pink"),            unsafe_allow_html=True)
    c4.markdown(metric_card("Avg Confidence",  f"{avg_confidence:.1f}%", "orange"),      unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Charts row 1
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Business Status Mix**")
        status_data = pd.DataFrame({
            "Status": ["Active", "Dormant", "Closed"],
            "Count": [stats["active_count"], stats["dormant_count"], stats["closed_count"]],
        })
        st.bar_chart(status_data, x="Status", y="Count", use_container_width=True)
        st.markdown(
            f"<span class='stat-pill pill-green'>Active {stats['active_count']}</span>"
            f"<span class='stat-pill pill-amber'>Dormant {stats['dormant_count']}</span>"
            f"<span class='stat-pill pill-red'>Closed {stats['closed_count']}</span>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("**Match Decisions**")
        decision_data = pd.DataFrame({
            "Decision": ["Auto Merge", "Needs Review", "New"],
            "Count": [stats["auto_merge"], stats["needs_review"], stats["new_records"]],
        })
        st.bar_chart(decision_data, x="Decision", y="Count", use_container_width=True)
        st.markdown(
            f"<span class='stat-pill pill-green'>Auto Merge {stats['auto_merge']}</span>"
            f"<span class='stat-pill pill-amber'>Review {stats['needs_review']}</span>"
            f"<span class='stat-pill pill-blue'>New {stats['new_records']}</span>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Charts row 2
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**Confidence Distribution**")
        if "match_confidence" in df.columns:
            conf_series = df["match_confidence"].dropna()
            if not conf_series.empty:
                bins = pd.cut(conf_series, bins=[0, 25, 50, 75, 90, 100],
                              labels=["0–25%", "26–50%", "51–75%", "76–90%", "91–100%"], include_lowest=True)
                conf_df = bins.value_counts().sort_index().reset_index()
                conf_df.columns = ["Confidence", "Count"]
                conf_df["Confidence"] = conf_df["Confidence"].astype(str)
                st.bar_chart(conf_df, x="Confidence", y="Count", use_container_width=True)
            else:
                st.info("No confidence data.")
        else:
            st.info("No confidence data.")
    with c2:
        st.markdown("**Match Tier Distribution**")
        if "match_tier" in df.columns:
            tier_counts = df["match_tier"].value_counts()
            tier_df = tier_counts.reset_index()
            tier_df.columns = ["Tier", "Count"]
            tier_df["Tier"] = tier_df["Tier"].astype(str)
            st.bar_chart(tier_df, x="Tier", y="Count", use_container_width=True)
            _tier_cls = {"Tier1": "pill-green", "Tier2": "pill-blue", "Tier3": "pill-amber", "New": "pill-purple"}
            pills = "".join(
                f"<span class='stat-pill {_tier_cls.get(str(tier), 'pill-cyan')}'>{tier} {count}</span>"
                for tier, count in tier_counts.items()
            )
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.info("No tier data.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Charts row 3
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**Top States**")
        if "state" in df.columns:
            top_states = df["state"].value_counts().head(10).reset_index()
            top_states.columns = ["State", "Count"]
            st.bar_chart(top_states, x="State", y="Count", use_container_width=True)
        else:
            st.info("No state data.")
    with c2:
        st.markdown("**Department Breakdown**")
        if "department" in df.columns:
            dept_counts = df["department"].value_counts().head(10).reset_index()
            dept_counts.columns = ["Department", "Count"]
            st.bar_chart(dept_counts, x="Department", y="Count", use_container_width=True)
        else:
            st.info("No department data.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Data quality chips
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    st.markdown("**Field Coverage**")
    dq_cols = [c for c in ["business_name", "pan", "gstin", "address", "district", "state"] if c in df.columns]
    if dq_cols:
        chips = "".join(
            f"<span class='quality-chip'>{c.replace('_',' ').title()}: {int(df[c].isna().sum()):,} missing ({(df[c].isna().sum()/len(df)*100):.1f}%)</span>"
            for c in dq_cols
        )
        st.markdown(f"<div class='quality-chip-list'>{chips}</div>", unsafe_allow_html=True)
    else:
        st.info("No coverage data.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Summary table
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    st.markdown("**Processing Summary**")
    solo_rate = ((stats["new_records"] - stats["needs_review"]) / total) * 100 if stats["new_records"] else 0
    summary_df = pd.DataFrame([
        ["Batch ID",         safe_text(st.session_state.batch_id)],
        ["Total Records",    f"{stats['total_records']:,}"],
        ["UBIDs Generated",  f"{stats['ubids_generated']:,}"],
        ["Matches Found",    f"{stats['matches_found']:,}"],
        ["Match Groups",     f"{stats['match_groups']:,}"],
        ["Auto Merge",       f"{stats['auto_merge']:,}"],
        ["Needs Review",     f"{stats['needs_review']:,}"],
        ["New Records",      f"{stats['new_records']:,}"],
        ["Active",           f"{stats['active_count']:,}"],
        ["Dormant",          f"{stats['dormant_count']:,}"],
        ["Closed",           f"{stats['closed_count']:,}"],
        ["Duplicate Rate",   f"{dup_rate:.1f}%"],
        ["Solo Rate",        f"{solo_rate:.1f}%"],
    ], columns=["Metric", "Value"])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_results_page() -> None:
    st.markdown("<div class='section-title'>Results</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">🔍</span>
            <h3>No Results Yet</h3>
            <p>Process a file first to see results.</p>
        </div>""", unsafe_allow_html=True)
        return

    df = st.session_state.df_processed.copy()
    ai_service = get_ai_service()

    st.markdown("<div class='surface' style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    status_filter = c1.selectbox("Status", ["All", "Active", "Dormant", "Closed"])
    tier_filter = c2.selectbox("Tier", ["All", "Tier1", "Tier2", "Tier3", "New"])
    confidence_min = c3.slider("Min confidence", 0, 100, 0)
    search_term = c4.text_input("Search")
    st.markdown("</div>", unsafe_allow_html=True)

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

    with st.expander("Ask ApexForge AI", expanded=False):
        st.markdown(
            """<div class="results-ask-panel">
                <div style="font-size:0.9rem; font-weight:600; color:var(--t1); margin-bottom:0.3rem;">Natural language filter</div>
                <div class="small-note">Try: "dormant firms in Odisha above 80 confidence"</div>
            </div>""",
            unsafe_allow_html=True,
        )
        query = st.text_input(
            "Natural language search", key="ask_apexforge_query",
            placeholder="Show dormant firms in Odisha with high confidence",
        )
        st.markdown(
            "<div class='quality-chip-list' style='margin:0.5rem 0;'>"
            "<span class='quality-chip'>duplicate businesses in Odisha</span>"
            "<span class='quality-chip'>dormant firms in Bengaluru</span>"
            "<span class='quality-chip'>Tier1 above 90 confidence</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        if query.strip():
            parsed = ai_service.parse_search_query(query) if ai_service is not None else {"ok": False, "filters": {}, "description": "AI helper unavailable."}
            st.caption(parsed.get("description", ""))
            filtered = apply_ask_apexforge_filters(filtered, parsed)

    st.caption(f"Showing {len(filtered):,} of {len(df):,} records")

    display_cols = [c for c in [
        "ubid", "business_name", "pan", "gstin", "district", "state",
        "business_status", "match_tier", "match_confidence", "match_decision",
    ] if c in filtered.columns]
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
    net = Network(height="700px", width="100%", bgcolor="#0D0F14", font_color="#F2F3F7", directed=False)
    net.barnes_hut()
    for idx, row in df.iterrows():
        name = safe_text(row.get("business_name"), f"Record {idx}", escape_html=True)
        ubid = safe_text(row.get("ubid"), f"ROW-{idx}", escape_html=True)
        title = (
            f"<b>{name}</b><br>UBID: {ubid}<br>Status: {safe_text(row.get('business_status'), escape_html=True)}"
            f"<br>Tier: {safe_text(row.get('match_tier'), escape_html=True)}"
            f"<br>Confidence: {safe_text(row.get('match_confidence'), escape_html=True)}"
        )
        tier = row.get("match_tier")
        color = {"Tier1": "#22C997", "Tier2": "#5B9CF6", "Tier3": "#F5A623", "New": "#7C5CFC"}.get(tier, "#4E5668")
        if row.get("is_master", False):
            color = "#00E5C3"
        net.add_node(int(idx), label=name[:30], title=title, color=color, size=24 if row.get("is_master", False) else 14)
    for m in matches:
        if 0 <= m.record1_id < len(df) and 0 <= m.record2_id < len(df):
            color = "#22C997" if m.tier == "Tier1" else "#5B9CF6" if m.tier == "Tier2" else "#F5A623"
            width = 4 if m.decision == "AutoMerge" else 2
            net.add_edge(m.record1_id, m.record2_id, title=m.reason, color=color, width=width)
    return net


def render_network_graph() -> None:
    st.markdown("<div class='section-title'>Network Graph</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">🕸️</span>
            <h3>Network Not Available</h3>
            <p>Process a file first to visualize the match network.</p>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown("<div class='surface' style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    show_only_groups = c1.checkbox("Show only matched groups", value=False)
    show_review = c2.checkbox("Include review matches", value=True)
    st.markdown("</div>", unsafe_allow_html=True)

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
                    remapped.append(MatchResult(
                        record1_id=remap[m.record1_id], record2_id=remap[m.record2_id],
                        score=m.score, tier=m.tier, matched_fields=m.matched_fields,
                        reason=m.reason, decision=m.decision,
                    ))
            matches = remapped

    st.markdown("<div class='network-container'>", unsafe_allow_html=True)
    if VisualizationService is not None:
        viz = VisualizationService()
        with st.spinner("Building interactive network..."):
            fig = viz.create_match_network(
                df.reset_index(drop=True), st.session_state.ubid_assignments, matches, height="700px",
            )
            if fig is not None:
                st.components.v1.html(fig.to_html(), height=760, scrolling=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
                st.markdown("**Legend**")
                cols = st.columns(5)
                legend = [("Tier 1","pill-green"),("Tier 2","pill-blue"),("Tier 3","pill-amber"),("New","pill-purple"),("Master","pill-cyan")]
                for col, (label, cls) in zip(cols, legend):
                    col.markdown(f"<span class='stat-pill {cls}'>{label}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                return

    if Network is None:
        st.warning("Network visualization libraries not available. Install gravis or pyvis.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    with st.spinner("Building network (pyvis)..."):
        net = build_pyvis_network(df.reset_index(drop=True), matches)
        if net is None:
            st.warning("Network could not be created.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, "r", encoding="utf-8") as fh:
                html_content = fh.read()
        st.components.v1.html(html_content, height=760, scrolling=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    st.markdown("**Legend**")
    cols = st.columns(5)
    legend = [("Tier 1","pill-green"),("Tier 2","pill-blue"),("Tier 3","pill-amber"),("New","pill-purple"),("Master","pill-cyan")]
    for col, (label, cls) in zip(cols, legend):
        col.markdown(f"<span class='stat-pill {cls}'>{label}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_ubid_explorer() -> None:
    st.markdown("<div class='section-title'>UBID Explorer</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">🎯</span>
            <h3>Explorer Empty</h3>
            <p>Process a file first to explore UBIDs.</p>
        </div>""", unsafe_allow_html=True)
        return

    df = st.session_state.df_processed.copy()
    st.markdown("<div class='surface' style='margin-bottom:1rem;'>", unsafe_allow_html=True)
    query = st.text_input("Search by UBID, name, PAN, GSTIN, district, or state")
    st.markdown("</div>", unsafe_allow_html=True)

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
        st.warning("No results found.")
        return

    st.caption(f"{len(results):,} result(s)")
    st.dataframe(results, use_container_width=True, hide_index=True)

    if "ubid" in results.columns:
        st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
        selected = st.selectbox("Select UBID for details", results["ubid"].astype(str).tolist())
        if selected:
            row = results[results["ubid"].astype(str) == str(selected)].iloc[0]
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**UBID Summary**")
                info = pd.DataFrame([
                    ["UBID",          safe_text(row.get("ubid"))],
                    ["Business Name", safe_text(row.get("business_name"))],
                    ["Status",        safe_text(row.get("business_status"))],
                    ["Tier",          safe_text(row.get("match_tier"))],
                    ["Confidence",    format_confidence(row.get("match_confidence"))],
                    ["Decision",      safe_text(row.get("match_decision"))],
                    ["State",         safe_text(row.get("state"))],
                    ["District",      safe_text(row.get("district"))],
                ], columns=["Field", "Value"])
                st.dataframe(info, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("**Raw Row**")
                st.dataframe(pd.DataFrame([row.to_dict()]), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_review_queue() -> None:
    st.markdown("<div class='section-title'>Review Queue</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">📝</span>
            <h3>Queue Empty</h3>
            <p>Process a file first to see review items.</p>
        </div>""", unsafe_allow_html=True)
        return

    matches = sorted(
        [m for m in st.session_state.matches if m.decision == "NeedsReview"],
        key=lambda m: float(m.score or 0.0), reverse=True,
    )
    if not matches:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">✅</span>
            <h3>All Clear</h3>
            <p>No items need review.</p>
        </div>""", unsafe_allow_html=True)
        return

    df = st.session_state.df_processed
    ai_service = get_ai_service()
    st.markdown(
        f"""<div style="margin-bottom: 1rem;">
            <span class="stat-pill pill-amber">{len(matches)} items need review</span>
            <span class="stat-pill {'pill-cyan' if ai_service and ai_service.is_available() else 'pill-purple'}">
                AI {'Ready' if ai_service and ai_service.is_available() else 'Offline'}
            </span>
        </div>""",
        unsafe_allow_html=True,
    )

    for i, m in enumerate(matches, start=1):
        r1 = df.iloc[m.record1_id]
        r2 = df.iloc[m.record2_id]
        priority = "High" if float(m.score or 0.0) >= 85 else "Medium" if float(m.score or 0.0) >= 75 else "Low"
        ai_key = f"{m.record1_id}:{m.record2_id}:{float(m.score or 0.0):.1f}:{m.tier}:{m.decision}"
        cached_ai = st.session_state.ai_explanations.get(ai_key)

        if cached_ai is None and ai_service is not None:
            try:
                cached_ai = ai_service.get_cached_explanation(m, r1, r2)
                if cached_ai is not None:
                    st.session_state.ai_explanations[ai_key] = cached_ai
            except Exception as exc:
                logger.debug("AI cache lookup skipped: %s", exc)

        with st.expander(
            f"Review {i}: {safe_text(r1.get('business_name'))} vs {safe_text(r2.get('business_name'))} · {m.tier} · {m.score:.1f}% · {priority}"
        ):
            st.markdown("<div class='review-card'>", unsafe_allow_html=True)
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

            st.markdown(
                f"""<div style="margin-top:0.75rem; padding-top:0.75rem; border-top:1px solid var(--edge-1);">
                    <span class="stat-pill pill-amber">Priority: {priority}</span>
                    <span class="stat-pill pill-blue">Confidence: {m.score:.1f}%</span>
                    <span class="stat-pill pill-blue">{safe_text(m.reason, escape_html=True)}</span>
                    <span class="stat-pill pill-purple">Fields: {safe_text(', '.join(m.matched_fields) or 'N/A', escape_html=True)}</span>
                </div>""",
                unsafe_allow_html=True,
            )

            with st.expander("AI explanation", expanded=bool(cached_ai)):
                if cached_ai is not None:
                    render_ai_review_result(cached_ai)
                if ai_service is None or not ai_service.is_available():
                    st.caption("Set GEMINI_API_KEY to enable optional AI explanations.")
                elif ai_service is not None and ai_service.is_available():
                    if st.button("Explain Match", key=f"explain_{ai_key}", use_container_width=True):
                        with st.spinner("Generating AI explanation..."):
                            try:
                                result = ai_service.explain_match(m, r1, r2, explicit=True)
                            except Exception as exc:
                                logger.warning("AI explanation failed: %s", exc)
                                result = {
                                    "ok": False, "source": "fallback", "cached": False,
                                    "recommendation": "Review",
                                    "confidence_summary": "AI explanation failed; deterministic review remains.",
                                    "uncertainty": safe_text(exc),
                                    "bullets": [f"Decision: {m.decision}", f"Score: {m.score:.1f}%", "Human review is the final step."],
                                    "evidence": list(m.matched_fields or [])[:3] or ["business_name"],
                                    "match_score": round(float(m.score or 0.0), 1),
                                    "tier": m.tier, "decision": m.decision,
                                }
                            st.session_state.ai_explanations[ai_key] = result
                            render_ai_review_result(result)

            st.markdown("</div>", unsafe_allow_html=True)


def render_analytics() -> None:
    st.markdown("<div class='section-title'>Analytics</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">📈</span>
            <h3>Analytics Unavailable</h3>
            <p>Process a file first to see analytics.</p>
        </div>""", unsafe_allow_html=True)
        return

    df = st.session_state.df_processed.copy()
    review_count = sum(1 for m in st.session_state.matches if m.decision == "NeedsReview")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Records",      f"{len(df):,}", "cyan"),   unsafe_allow_html=True)
    c2.markdown(metric_card("UBIDs",        f"{df['ubid'].nunique() if 'ubid' in df.columns else 0:,}", "purple"), unsafe_allow_html=True)
    c3.markdown(metric_card("Groups",       f"{len(st.session_state.match_groups):,}", "pink"), unsafe_allow_html=True)
    c4.markdown(metric_card("Review Items", f"{review_count:,}", "orange"), unsafe_allow_html=True)

    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Status Distribution**")
        if "business_status" in df.columns:
            sd = df["business_status"].value_counts().reset_index()
            sd.columns = ["Status", "Count"]
            st.bar_chart(sd, x="Status", y="Count", use_container_width=True)
        else:
            st.info("No status data.")
    with right:
        st.markdown("**Match Tier Distribution**")
        if "match_tier" in df.columns:
            td = df["match_tier"].value_counts().reset_index()
            td.columns = ["Tier", "Count"]
            td["Tier"] = td["Tier"].astype(str)
            st.bar_chart(td, x="Tier", y="Count", use_container_width=True)
        else:
            st.info("No match data.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='surface' style='margin-top:1rem;'>", unsafe_allow_html=True)
    st.markdown("**Recent Records**")
    preview_cols = [c for c in ["ubid", "business_name", "business_status", "match_tier", "match_confidence"] if c in df.columns]
    st.dataframe(df[preview_cols].head(20), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


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
