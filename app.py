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
import html
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    :root {
        --bg-deep: #030508;
        --bg-surface: rgba(10, 14, 24, 0.75);
        --bg-card: rgba(255, 255, 255, 0.025);
        --border-subtle: rgba(255, 255, 255, 0.05);
        --border-glow: rgba(0, 245, 212, 0.2);
        --text-primary: #f0f0f5;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --accent-cyan: #00f5d4;
        --accent-purple: #7b2ff7;
        --accent-pink: #f72585;
        --accent-orange: #ff9f1c;
        --accent-blue: #3b82f6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --info: #60a5fa;
        --glow-cyan: 0 0 20px rgba(0, 245, 212, 0.15);
        --glow-purple: 0 0 20px rgba(123, 47, 247, 0.15);
        --glow-pink: 0 0 20px rgba(247, 37, 133, 0.15);
    }

    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    .stApp {
        background: var(--bg-deep) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Animated aurora background */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background:
            radial-gradient(ellipse 80% 50% at 20% 40%, rgba(123, 47, 247, 0.07) 0%, transparent 50%),
            radial-gradient(ellipse 60% 40% at 80% 20%, rgba(0, 245, 212, 0.05) 0%, transparent 50%),
            radial-gradient(ellipse 70% 60% at 50% 90%, rgba(247, 37, 133, 0.04) 0%, transparent 50%),
            radial-gradient(ellipse 50% 30% at 90% 70%, rgba(255, 159, 28, 0.03) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
        animation: auroraDrift 25s ease-in-out infinite alternate;
    }

    @keyframes auroraDrift {
        0%   { transform: translate(0, 0) scale(1); opacity: 1; }
        25%  { transform: translate(-3%, 2%) scale(1.03); opacity: 0.9; }
        50%  { transform: translate(2%, -1%) scale(0.97); opacity: 1; }
        75%  { transform: translate(-1%, 3%) scale(1.01); opacity: 0.95; }
        100% { transform: translate(0, 0) scale(1); opacity: 1; }
    }

    /* Scanline overlay for cyberpunk feel */
    .stApp::after {
        content: '';
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: repeating-linear-gradient(
            0deg, transparent, transparent 2px,
            rgba(0, 245, 212, 0.008) 2px, rgba(0, 245, 212, 0.008) 4px
        );
        pointer-events: none;
        z-index: 9999;
    }

    /* Hero Section — Neon command center */
    .hero {
        position: relative;
        padding: 2.8rem 2.5rem;
        border-radius: 24px;
        background:
            linear-gradient(135deg, rgba(5, 8, 20, 0.95) 0%, rgba(15, 10, 40, 0.9) 50%, rgba(25, 8, 35, 0.95) 100%);
        border: 1px solid var(--border-subtle);
        color: var(--text-primary);
        margin-bottom: 1.5rem;
        overflow: hidden;
        box-shadow:
            0 12px 48px rgba(0, 0, 0, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.04),
            var(--glow-cyan);
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -50%; right: -20%;
        width: 500px; height: 500px;
        background: radial-gradient(circle, rgba(0, 245, 212, 0.1) 0%, transparent 70%);
        animation: orbFloat 8s ease-in-out infinite;
    }
    .hero::after {
        content: '';
        position: absolute;
        bottom: -30%; left: -10%;
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(123, 47, 247, 0.08) 0%, transparent 70%);
        animation: orbFloat 10s ease-in-out infinite reverse;
    }
    @keyframes orbFloat {
        0%, 100% { opacity: 0.4; transform: scale(1) translate(0, 0); }
        33% { opacity: 0.8; transform: scale(1.15) translate(10px, -15px); }
        66% { opacity: 0.6; transform: scale(1.05) translate(-10px, 10px); }
    }
    .hero h1 {
        position: relative;
        z-index: 1;
        margin: 0;
        font-size: 2.8rem;
        line-height: 1.1;
        font-weight: 900;
        background: linear-gradient(135deg, #fff 0%, var(--accent-cyan) 40%, var(--accent-purple) 70%, var(--accent-pink) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.03em;
        filter: drop-shadow(0 0 30px rgba(0, 245, 212, 0.15));
    }
    .hero p {
        position: relative;
        z-index: 1;
        margin: 0.75rem 0 0 0;
        color: var(--text-secondary);
        font-size: 1.05rem;
        font-weight: 400;
        max-width: 650px;
    }

    /* Glass Cards / Surfaces — Animated border gradient */
    .surface {
        background: var(--bg-card);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid var(--border-subtle);
        border-radius: 20px;
        padding: 1.5rem;
        position: relative;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .surface:hover {
        border-color: var(--border-glow);
        box-shadow: 0 12px 48px rgba(0, 245, 212, 0.06), 0 4px 24px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }
    .surface::before {
        content: '';
        position: absolute;
        top: -1px; left: -1px; right: -1px; bottom: -1px;
        border-radius: 21px;
        background: linear-gradient(135deg, rgba(0, 245, 212, 0.15), transparent 40%, transparent 60%, rgba(123, 47, 247, 0.1));
        z-index: -1;
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    .surface:hover::before {
        opacity: 1;
    }

    /* Section Typography — Neon accent underline */
    .section-title {
        font-size: 1.6rem;
        font-weight: 800;
        margin-bottom: 0.75rem;
        color: var(--text-primary);
        letter-spacing: -0.02em;
        position: relative;
        padding-bottom: 0.6rem;
    }
    .section-title::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0;
        width: 60px; height: 3px;
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
        border-radius: 999px;
        box-shadow: var(--glow-cyan);
    }
    .section-subtitle {
        color: var(--text-secondary);
        margin-bottom: 1.25rem;
        font-size: 0.95rem;
        font-weight: 400;
    }

    /* Stats / Metric Cards — Shimmer + animated gradient */
    .metric-card {
        background: var(--bg-card);
        backdrop-filter: blur(24px);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        position: relative;
        overflow: hidden;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric-card:hover {
        border-color: var(--border-glow);
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 12px 40px rgba(0, 245, 212, 0.08);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink), var(--accent-cyan));
        background-size: 300% 100%;
        animation: gradientSlide 4s ease infinite;
        opacity: 0.7;
    }
    @keyframes gradientSlide {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .metric-card.cyan::before { background: linear-gradient(90deg, var(--accent-cyan), #00c9a7, var(--accent-cyan)); background-size: 200% 100%; animation: gradientSlide 3s ease infinite; }
    .metric-card.purple::before { background: linear-gradient(90deg, var(--accent-purple), #a855f7, var(--accent-purple)); background-size: 200% 100%; animation: gradientSlide 3.5s ease infinite; }
    .metric-card.pink::before { background: linear-gradient(90deg, var(--accent-pink), #ec4899, var(--accent-pink)); background-size: 200% 100%; animation: gradientSlide 4s ease infinite; }
    .metric-card.orange::before { background: linear-gradient(90deg, var(--accent-orange), #fbbf24, var(--accent-orange)); background-size: 200% 100%; animation: gradientSlide 3.2s ease infinite; }
    .metric-card::after {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.03), transparent);
        animation: shimmer 5s ease-in-out infinite;
    }
    @keyframes shimmer {
        0% { left: -100%; }
        50% { left: 100%; }
        100% { left: 100%; }
    }
    .metric-card .metric-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
    }
    .metric-card .metric-value {
        font-size: 2.2rem;
        font-weight: 900;
        color: var(--text-primary);
        line-height: 1;
        letter-spacing: -0.03em;
    }
    .metric-card .metric-delta {
        font-size: 0.8rem;
        margin-top: 0.4rem;
        font-weight: 500;
    }

    /* Status Pills — Neon glow variants */
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.4rem 0.85rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.2rem 0.25rem 0.2rem 0;
        border: 1px solid transparent;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .stat-pill::before {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        transition: left 0.5s ease;
    }
    .stat-pill:hover::before { left: 100%; }
    .pill-green {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border-color: rgba(16, 185, 129, 0.2);
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.15);
    }
    .pill-amber {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border-color: rgba(245, 158, 11, 0.2);
        box-shadow: 0 0 12px rgba(245, 158, 11, 0.15);
    }
    .pill-red {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border-color: rgba(239, 68, 68, 0.2);
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.15);
    }
    .pill-blue {
        background: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
        border-color: rgba(59, 130, 246, 0.2);
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.15);
    }
    .pill-purple {
        background: rgba(123, 47, 247, 0.12);
        color: #a78bfa;
        border-color: rgba(123, 47, 247, 0.2);
        box-shadow: 0 0 12px rgba(123, 47, 247, 0.15);
    }
    .pill-cyan {
        background: rgba(0, 245, 212, 0.12);
        color: #2dd4bf;
        border-color: rgba(0, 245, 212, 0.2);
        box-shadow: 0 0 12px rgba(0, 245, 212, 0.15);
    }
    .stat-pill:hover {
        transform: translateY(-1px) scale(1.05);
        filter: brightness(1.1);
    }

    /* Notes & Muted text */
    .muted {
        color: var(--text-secondary);
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .small-note {
        font-size: 0.82rem;
        color: var(--text-muted);
        line-height: 1.5;
    }

    /* Sidebar Styling — Animated gradient */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(5, 8, 20, 0.98) 0%, rgba(10, 14, 24, 0.95) 50%, rgba(15, 10, 30, 0.98) 100%) !important;
        border-right: 1px solid var(--border-subtle) !important;
        position: relative;
    }
    [data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(180deg, transparent, rgba(0, 245, 212, 0.02), transparent);
        animation: sidebarGlow 8s ease-in-out infinite;
        pointer-events: none;
    }
    @keyframes sidebarGlow {
        0%, 100% { opacity: 0; }
        50% { opacity: 1; }
    }
    [data-testid="stSidebar"] .stRadio > label {
        color: var(--text-secondary) !important;
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 0.5rem !important;
    }
    [data-testid="stSidebar"] .stRadio > div > div > label {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 14px !important;
        padding: 0.7rem 1rem !important;
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        margin-bottom: 0.3rem !important;
        position: relative;
        overflow: hidden;
    }
    [data-testid="stSidebar"] .stRadio > div > div > label::before {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 245, 212, 0.1), transparent);
        transition: left 0.4s ease;
    }
    [data-testid="stSidebar"] .stRadio > div > div > label:hover::before { left: 100%; }
    [data-testid="stSidebar"] .stRadio > div > div > label:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        color: var(--text-primary) !important;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] .stRadio > div > div > label[data-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 245, 212, 0.12), rgba(123, 47, 247, 0.08)) !important;
        border-color: rgba(0, 245, 212, 0.25) !important;
        color: var(--accent-cyan) !important;
        font-weight: 700 !important;
        box-shadow: 0 0 16px rgba(0, 245, 212, 0.15) !important;
    }

    /* Buttons — Enhanced neon effects */
    .stButton > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        padding: 0.65rem 1.4rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid transparent !important;
        letter-spacing: 0.01em;
        position: relative;
        overflow: hidden;
    }
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s ease;
    }
    .stButton > button:hover::before { left: 100%; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)) !important;
        color: #030508 !important;
        border: none !important;
        box-shadow: 0 4px 20px rgba(0, 245, 212, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 8px 32px rgba(0, 245, 212, 0.4) !important;
        transform: translateY(-2px) scale(1.02) !important;
        filter: brightness(1.1);
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.05) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-subtle) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: var(--border-glow) !important;
        box-shadow: 0 0 16px rgba(0, 245, 212, 0.1) !important;
        transform: translateY(-1px) !important;
    }

    /* DataFrames / Tables */
    .stDataFrame {
        border-radius: 16px !important;
        overflow: hidden !important;
    }
    .stDataFrame table {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 16px !important;
    }
    .stDataFrame th {
        background: rgba(255, 255, 255, 0.04) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid var(--border-subtle) !important;
        padding: 0.75rem 1rem !important;
    }
    .stDataFrame td {
        color: var(--text-secondary) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
        padding: 0.65rem 1rem !important;
        font-size: 0.88rem !important;
    }
    .stDataFrame tr:hover td {
        background: rgba(255, 255, 255, 0.02) !important;
    }

    /* Progress Bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink)) !important;
        border-radius: 999px !important;
        box-shadow: 0 0 12px rgba(0, 245, 212, 0.3) !important;
    }
    .stProgress > div {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 999px !important;
    }

    /* Sliders */
    .stSlider [data-testid="stThumbValue"] {
        color: var(--accent-cyan) !important;
        font-weight: 600;
    }
    .stSlider [role="slider"] {
        background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)) !important;
        box-shadow: 0 0 12px rgba(0, 245, 212, 0.4) !important;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stFileUploader > div > div > div {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        font-size: 0.9rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus {
        border-color: var(--accent-cyan) !important;
        box-shadow: 0 0 0 3px rgba(0, 245, 212, 0.1) !important;
    }

    /* Expander */
    .stExpander {
        border: 1px solid var(--border-subtle) !important;
        border-radius: 16px !important;
        background: var(--bg-card) !important;
        overflow: hidden;
    }
    .stExpander > div:first-child {
        background: rgba(255, 255, 255, 0.02) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
    }

    /* Info / Warning / Error boxes */
    .stAlert {
        border-radius: 14px !important;
        border: 1px solid transparent !important;
        background: var(--bg-card) !important;
        backdrop-filter: blur(10px);
    }
    .stAlert[data-baseweb="notification"][data-kind="info"] {
        border-color: rgba(59, 130, 246, 0.2) !important;
        background: rgba(59, 130, 246, 0.06) !important;
    }
    .stAlert[data-baseweb="notification"][data-kind="warning"] {
        border-color: rgba(245, 158, 11, 0.2) !important;
        background: rgba(245, 158, 11, 0.06) !important;
    }
    .stAlert[data-baseweb="notification"][data-kind="error"] {
        border-color: rgba(239, 68, 68, 0.2) !important;
        background: rgba(239, 68, 68, 0.06) !important;
    }
    .stAlert[data-baseweb="notification"][data-kind="success"] {
        border-color: rgba(16, 185, 129, 0.2) !important;
        background: rgba(16, 185, 129, 0.06) !important;
    }

    /* Charts */
    .stChart {
        border-radius: 16px !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        padding: 1rem;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 999px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.15);
    }

    /* Loading / Spinner */
    .stSpinner > div > div {
        border-color: var(--accent-cyan) !important;
        border-top-color: transparent !important;
    }

    /* Network Graph container */
    .network-container {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    /* Review cards */
    .review-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        transition: all 0.25s ease;
    }
    .review-card:hover {
        border-color: var(--border-glow);
        box-shadow: 0 4px 20px rgba(0, 245, 212, 0.05);
    }

    /* Empty state — Animated SVG illustrations */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: var(--text-muted);
        position: relative;
    }
    .empty-state-icon {
        font-size: 3.5rem;
        margin-bottom: 1.5rem;
        opacity: 0.6;
        animation: float 4s ease-in-out infinite;
        filter: drop-shadow(0 0 20px rgba(0, 245, 212, 0.2));
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    .empty-state h3 {
        color: var(--text-primary);
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .empty-state p {
        color: var(--text-secondary);
        font-size: 0.95rem;
        max-width: 400px;
        margin: 0 auto;
    }

    /* Dashboard section animations */
    .dashboard-section {
        animation: slideInUp 0.6s ease-out;
    }
    @keyframes slideInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .dashboard-section:nth-child(2) { animation-delay: 0.1s; }
    .dashboard-section:nth-child(3) { animation-delay: 0.2s; }
    .dashboard-section:nth-child(4) { animation-delay: 0.3s; }

    /* Pipeline steps styling */
    .pipeline-steps {
        position: relative;
    }
    .pipeline-step {
        text-align: center;
        flex: 1;
        position: relative;
    }
    .step-icon {
        font-size: 1.8rem;
        margin-bottom: 0.3rem;
        animation: pulse 2s ease-in-out infinite;
    }
    .step-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .pipeline-arrow {
        font-size: 1.2rem;
        color: var(--accent-cyan);
        display: flex;
        align-items: center;
        justify-content: center;
        animation: arrowPulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.8; }
        50% { transform: scale(1.1); opacity: 1; }
    }
    @keyframes arrowPulse {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 1; }
    }

    /* Upload zone styling */
    .upload-zone {
        border: 2px dashed var(--border-glow) !important;
        background: linear-gradient(135deg, rgba(0, 245, 212, 0.02), rgba(123, 47, 247, 0.02)) !important;
        transition: all 0.3s ease !important;
    }
    .upload-zone:hover {
        border-color: var(--accent-cyan) !important;
        background: linear-gradient(135deg, rgba(0, 245, 212, 0.05), rgba(123, 47, 247, 0.05)) !important;
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 245, 212, 0.1) !important;
    }

    /* Focus accessibility */
    *:focus-visible {
        outline: 2px solid var(--accent-cyan) !important;
        outline-offset: 2px !important;
    }

    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border-subtle), transparent);
        margin: 1.5rem 0;
    }

    /* Code blocks */
    .stCode pre {
        background: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        color: var(--accent-cyan) !important;
    }

    /* Caption */
    .stCaption {
        color: var(--text-muted) !important;
        font-size: 0.8rem !important;
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
    db_status = (
        '<span class="stat-pill pill-cyan">Database Connected</span>'
        if st.session_state.db_initialized
        else '<span class="stat-pill pill-amber">Local Mode</span>'
    )
    batch_status = (
        f'<span class="stat-pill pill-blue">Batch {st.session_state.batch_id}</span>'
        if st.session_state.processing_complete and st.session_state.batch_id
        else ""
    )
    st.markdown(
        f"""
        <div class="hero">
            <h1 class="typing-text">ApexForge AI</h1>
            <p>Unified Business Identity System — clean uploads, intelligent matching, and UBID exploration at scale.</p>
            <div style="margin-top: 1.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                {db_status}
                {batch_status}
            </div>
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const typingElement = document.querySelector('.typing-text');
            if (typingElement) {{
                const text = typingElement.textContent;
                typingElement.textContent = '';
                let index = 0;
                function typeText() {{
                    if (index < text.length) {{
                        typingElement.textContent += text.charAt(index);
                        index++;
                        setTimeout(typeText, 80);
                    }}
                }}
                setTimeout(typeText, 500);
            }}
        }});
        </script>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.5rem 0 1.5rem 0;">
                <div style="font-size: 1.25rem; font-weight: 900; color: #f0f0f5; letter-spacing: -0.02em; display: flex; align-items: center; gap: 0.5rem;">
                    🏢 ApexForge AI
                </div>
                <div style="font-size: 0.72rem; color: #64748b; margin-top: 0.2rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;">
                    Business Identity Pipeline
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='margin: 1rem 0; opacity: 0.3;'>", unsafe_allow_html=True)

        db_col1, db_col2 = st.columns([1, 1])
        with db_col1:
            if st.button("⚡ Connect DB", use_container_width=True, type="secondary"):
                init_database()
        with db_col2:
            if st.button("🔄 Reset", use_container_width=True, type="secondary"):
                reset_processing_state()
                st.rerun()

        status_pills = []
        if st.session_state.db_initialized:
            status_pills.append("<span class='stat-pill pill-cyan'>Database Connected</span>")
        else:
            status_pills.append("<span class='stat-pill pill-amber'>Local Mode</span>")
        if st.session_state.processing_complete:
            status_pills.append("<span class='stat-pill pill-blue'>Batch Ready</span>")
        if status_pills:
            st.markdown(" ".join(status_pills), unsafe_allow_html=True)

        st.markdown("<hr style='margin: 1rem 0; opacity: 0.3;'>", unsafe_allow_html=True)

        nav_options = [
            ("📤 Upload", "Upload"),
            ("📊 Dashboard", "Dashboard"),
            ("🔍 Results", "Results"),
            ("🕸️ Network", "Network Graph"),
            ("🎯 UBID", "UBID Explorer"),
            ("📝 Review", "Review Queue"),
            ("📈 Analytics", "Analytics")
        ]
        nav_labels = [label for _, label in nav_options]
        nav_index = 0 if not st.session_state.processing_complete else 1

        # Custom radio with icons
        selected = st.radio(
            "",
            nav_labels,
            index=nav_index,
            label_visibility="collapsed",
        )

        # Display icon-based navigation
        for icon, label in nav_options:
            is_selected = selected == label
            st.markdown(
                f"""
                <div style="padding: 0.4rem 0; cursor: pointer; {'background: linear-gradient(90deg, rgba(0, 245, 212, 0.1), transparent); border-left: 3px solid var(--accent-cyan);' if is_selected else ''}">
                    <span style="font-size: 1rem; margin-right: 0.5rem;">{icon}</span>
                    <span style="color: {'var(--accent-cyan)' if is_selected else 'var(--text-secondary)'}; font-weight: {'700' if is_selected else '500'};">{label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='margin: 1rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="small-note" style="border-left: 2px solid var(--border-glow); padding-left: 0.75rem;">
                💡 Drop a CSV, process it once, then explore matches, clusters, reviews, and UBIDs without leaving the app.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected


def render_upload_page() -> None:
    st.markdown("<div class='section-title'>Upload Business Data</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Clean. Match. Assign. Review. Export.</div>", unsafe_allow_html=True)

    # Pipeline steps visualization
    st.markdown("""
    <div class='pipeline-steps' style='display: flex; justify-content: space-between; margin: 2rem 0; padding: 0 1rem;'>
        <div class='pipeline-step'>
            <div class='step-icon'>📤</div>
            <div class='step-label'>Upload</div>
        </div>
        <div class='pipeline-arrow'>→</div>
        <div class='pipeline-step'>
            <div class='step-icon'>🧹</div>
            <div class='step-label'>Clean</div>
        </div>
        <div class='pipeline-arrow'>→</div>
        <div class='pipeline-step'>
            <div class='step-icon'>🔍</div>
            <div class='step-label'>Match</div>
        </div>
        <div class='pipeline-arrow'>→</div>
        <div class='pipeline-step'>
            <div class='step-icon'>🎯</div>
            <div class='step-label'>UBID</div>
        </div>
        <div class='pipeline-arrow'>→</div>
        <div class='pipeline-step'>
            <div class='step-icon'>📊</div>
            <div class='step-label'>Explore</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        st.markdown("<div class='surface upload-zone'>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align: center; padding: 2rem 1rem 1rem 1rem;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem; animation: float 3s ease-in-out infinite;'>📁</div>
            <div style='font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;'>Drop your CSV here</div>
            <div style='color: var(--text-secondary); font-size: 0.9rem;'>or click to browse</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            label_visibility="collapsed",
            help="The app will auto-map common column variations when possible.",
        )

        if uploaded_file is not None:
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > MAX_UPLOAD_SIZE_MB:
                st.error(f"File too large ({file_size_mb:.1f} MB). Max allowed: {MAX_UPLOAD_SIZE_MB} MB.")
                st.markdown("</div>", unsafe_allow_html=True)
                return

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

            st.markdown("<div style='margin: 1rem 0;'>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(metric_card("Rows", f"{len(mapped):,}", "cyan"), unsafe_allow_html=True)
            m2.markdown(metric_card("Columns", len(mapped.columns), "purple"), unsafe_allow_html=True)
            m3.markdown(metric_card("Mapped", len(detected), "pink"), unsafe_allow_html=True)
            m4.markdown(metric_card("Missing", len(missing), "orange"), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if detected:
                with st.expander("Auto-mapped columns", expanded=False):
                    for item in detected:
                        st.write(f"• {item}")

            if missing:
                st.info(f"Blank columns created for: {', '.join(missing)}")

            with st.expander("Preview data", expanded=True):
                st.dataframe(mapped.head(10), use_container_width=True)

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
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <h3>Dashboard Locked</h3>
                <p>Process a file first to unlock the dashboard and view insights.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    df = st.session_state.df_processed
    stats = compute_local_stats(df, st.session_state.matches, st.session_state.match_groups, st.session_state.ubid_assignments)

    total = stats["total_records"] or 1
    match_rate = (stats["matches_found"] / total) * 100
    solo_rate = ((stats["new_records"] - stats["needs_review"]) / total) * 100 if stats["new_records"] else 0
    dup_rate = (stats["auto_merge"] / total) * 100 if total else 0

    avg_confidence = 0.0
    if "match_confidence" in df.columns and not df["match_confidence"].isna().all():
        avg_confidence = float(df["match_confidence"].mean())

    # Animated KPI section
    st.markdown("<div class='dashboard-section' style='margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("Total Records", f"{stats['total_records']:,}", "cyan"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("UBIDs Generated", f"{stats['ubids_generated']:,}", "purple"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Match Rate", f"{match_rate:.1f}%", "pink"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Avg Confidence", f"{avg_confidence:.1f}%", "orange"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Status & Decisions section
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("**Business Status**")
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

    # Confidence & Tiers section
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("**Match Confidence Distribution**")
        if "match_confidence" in df.columns:
            conf_series = df["match_confidence"].dropna()
            if not conf_series.empty:
                bins = pd.cut(conf_series, bins=[0, 25, 50, 75, 90, 100], labels=["0–25%", "26–50%", "51–75%", "76–90%", "91–100%"], include_lowest=True)
                conf_df = bins.value_counts().sort_index().reset_index()
                conf_df.columns = ["Confidence Range", "Count"]
                conf_df["Confidence Range"] = conf_df["Confidence Range"].astype(str)
                st.bar_chart(conf_df, x="Confidence Range", y="Count", use_container_width=True)
            else:
                st.info("No confidence data available")
        else:
            st.info("No confidence data available")

    with c2:
        st.markdown("**Match Tier Distribution**")
        if "match_tier" in df.columns:
            tier_counts = df["match_tier"].value_counts()
            tier_df = tier_counts.reset_index()
            tier_df.columns = ["Tier", "Count"]
            tier_df["Tier"] = tier_df["Tier"].astype(str)
            st.bar_chart(tier_df, x="Tier", y="Count", use_container_width=True)
            pills = ""
            for tier, count in tier_counts.items():
                cls = {
                    "Tier1": "pill-green",
                    "Tier2": "pill-blue",
                    "Tier3": "pill-amber",
                    "New": "pill-purple",
                }.get(tier, "pill-cyan")
                pills += f"<span class='stat-pill {cls}'>{tier} {count}</span>"
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.info("No tier data available")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Geographic & Department section
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("**Geographic — Top States**")
        if "state" in df.columns:
            top_states = df["state"].value_counts().head(10).reset_index()
            top_states.columns = ["State", "Count"]
            st.bar_chart(top_states, x="State", y="Count", use_container_width=True)
        else:
            st.info("No state data available")

    with c2:
        st.markdown("**Department / Industry Breakdown**")
        if "department" in df.columns:
            dept_counts = df["department"].value_counts().head(10).reset_index()
            dept_counts.columns = ["Department", "Count"]
            st.bar_chart(dept_counts, x="Department", y="Count", use_container_width=True)
        else:
            st.info("No department data available")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Data Quality section
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
    st.markdown("**Data Quality Overview**")
    dq_cols = [c for c in ["business_name", "pan", "gstin", "address", "district", "state"] if c in df.columns]
    if dq_cols:
        missing_rows = []
        for col in dq_cols:
            missing = int(df[col].isna().sum())
            pct = (missing / len(df)) * 100 if len(df) else 0
            missing_rows.append([col.replace("_", " ").title(), f"{missing:,}", f"{pct:.1f}%"])
        dq_df = pd.DataFrame(missing_rows, columns=["Field", "Missing", "Pct"])
        st.dataframe(dq_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data quality fields available")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Processing Summary section
    st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
    st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
    st.markdown("**Processing Summary**")
    summary_df = pd.DataFrame(
        [
            ["Batch ID", safe_text(st.session_state.batch_id)],
            ["Total Records", f"{stats['total_records']:,}"],
            ["UBIDs Generated", f"{stats['ubids_generated']:,}"],
            ["Matches Found", f"{stats['matches_found']:,}"],
            ["Match Groups", f"{stats['match_groups']:,}"],
            ["Auto Merge", f"{stats['auto_merge']:,}"],
            ["Needs Review", f"{stats['needs_review']:,}"],
            ["New Records", f"{stats['new_records']:,}"],
            ["Active", f"{stats['active_count']:,}"],
            ["Dormant", f"{stats['dormant_count']:,}"],
            ["Closed", f"{stats['closed_count']:,}"],
            ["Duplicate Rate", f"{dup_rate:.1f}%"],
            ["Solo Record Rate", f"{solo_rate:.1f}%"],
        ],
        columns=["Metric", "Value"],
    )
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_results_page() -> None:
    st.markdown("<div class='section-title'>Results</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f0f5; margin-bottom: 0.5rem;">No Results Yet</div>
                <div>Process a file first to see results.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    df = st.session_state.df_processed.copy()

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

    st.caption(f"Showing {len(filtered):,} of {len(df):,} records")

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
        name = safe_text(row.get("business_name"), f"Record {idx}", escape_html=True)
        ubid = safe_text(row.get("ubid"), f"ROW-{idx}", escape_html=True)
        title = (
            f"<b>{name}</b><br>UBID: {ubid}<br>Status: {safe_text(row.get('business_status'), escape_html=True)}"
            f"<br>Tier: {safe_text(row.get('match_tier'), escape_html=True)}"
            f"<br>Confidence: {safe_text(row.get('match_confidence'), escape_html=True)}"
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
    st.markdown("<div class='section-title'>Network Graph</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🕸️</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f0f5; margin-bottom: 0.5rem;">Network Not Available</div>
                <div>Process a file first to visualize the match network.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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

    st.markdown("<div class='network-container'>", unsafe_allow_html=True)
    # Try gravis-based visualization first (from VisualizationService)
    if VisualizationService is not None:
        viz = VisualizationService()
        with st.spinner("Building interactive network..."):
            fig = viz.create_match_network(
                df.reset_index(drop=True),
                st.session_state.ubid_assignments,
                matches,
                height="700px",
            )
            if fig is not None:
                st.components.v1.html(fig.to_html(), height=760, scrolling=True)
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
                st.markdown("**Legend**")
                legend_cols = st.columns(5)
                legend = [
                    ("Tier 1", "pill-green"),
                    ("Tier 2", "pill-blue"),
                    ("Tier 3", "pill-amber"),
                    ("New", "pill-purple"),
                    ("Master", "pill-red"),
                ]
                for col, (label, cls) in zip(legend_cols, legend):
                    with col:
                        st.markdown(f"<span class='stat-pill {cls}'>{label}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                return

    # Fallback to pyvis
    if Network is None:
        st.warning("Network visualization libraries not available. Install gravis or pyvis.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    with st.spinner("Building interactive network (pyvis fallback)..."):
        net = build_pyvis_network(df.reset_index(drop=True), matches)
        if net is None:
            st.warning("Network could not be created.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, "r", encoding="utf-8") as fh:
                html = fh.read()

        st.components.v1.html(html, height=760, scrolling=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
    st.markdown("**Legend**")
    legend_cols = st.columns(5)
    legend = [
        ("Tier 1", "pill-green"),
        ("Tier 2", "pill-blue"),
        ("Tier 3", "pill-amber"),
        ("New", "pill-purple"),
        ("Master", "pill-red"),
    ]
    for col, (label, cls) in zip(legend_cols, legend):
        with col:
            st.markdown(f"<span class='stat-pill {cls}'>{label}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_ubid_explorer() -> None:
    st.markdown("<div class='section-title'>UBID Explorer</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🔎</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f0f5; margin-bottom: 0.5rem;">Explorer Empty</div>
                <div>Process a file first to explore UBIDs.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    df = st.session_state.df_processed.copy()
    st.markdown("<div class='surface' style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
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
        st.warning("No results found")
        return

    st.caption(f"{len(results):,} result(s)")
    st.dataframe(results, use_container_width=True, hide_index=True)

    if "ubid" in results.columns:
        st.markdown("<div class='surface' style='margin-top: 1rem;'>", unsafe_allow_html=True)
        selected = st.selectbox("Select UBID for details", results["ubid"].astype(str).tolist())
        if selected:
            row = results[results["ubid"].astype(str) == str(selected)].iloc[0]
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**UBID Summary**")
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
            with col2:
                st.markdown("**Raw Row**")
                st.dataframe(pd.DataFrame([row.to_dict()]), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_review_queue() -> None:
    st.markdown("<div class='section-title'>Review Queue</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📝</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f0f5; margin-bottom: 0.5rem;">Queue Empty</div>
                <div>Process a file first to see review items.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    matches = [m for m in st.session_state.matches if m.decision == "NeedsReview"]
    if not matches:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f0f5; margin-bottom: 0.5rem;">All Clear</div>
                <div>No items need review.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    df = st.session_state.df_processed
    st.markdown(
        f"""
        <div style="margin-bottom: 1rem;">
            <span class="stat-pill pill-amber">{len(matches)} items need review</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i, m in enumerate(matches, start=1):
        r1 = df.iloc[m.record1_id]
        r2 = df.iloc[m.record2_id]
        with st.expander(
            f"Review {i}: {safe_text(r1.get('business_name'))} vs {safe_text(r2.get('business_name'))} | {m.tier} | {m.score:.1f}%"
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
                f"""
                <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.06);">
                    <span class="stat-pill pill-blue">Reason: {m.reason}</span>
                    <span class="stat-pill pill-purple">Fields: {', '.join(m.matched_fields)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)


def render_analytics() -> None:
    st.markdown("<div class='section-title'>Analytics</div>", unsafe_allow_html=True)

    if not st.session_state.processing_complete:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📈</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f0f5; margin-bottom: 0.5rem;">Analytics Unavailable</div>
                <div>Process a file first to see analytics.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    df = st.session_state.df_processed.copy()
    review_count = sum(1 for m in st.session_state.matches if m.decision == "NeedsReview")

    st.markdown("<div style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Records", f"{len(df):,}", "cyan"), unsafe_allow_html=True)
    c2.markdown(metric_card("UBIDs", f"{df['ubid'].nunique() if 'ubid' in df.columns else 0:,}", "purple"), unsafe_allow_html=True)
    c3.markdown(metric_card("Groups", f"{len(st.session_state.match_groups):,}", "pink"), unsafe_allow_html=True)
    c4.markdown(metric_card("Review Items", f"{review_count:,}", "orange"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Status Distribution**")
        if "business_status" in df.columns:
            status_dist = df["business_status"].value_counts().reset_index()
            status_dist.columns = ["Status", "Count"]
            st.bar_chart(status_dist, x="Status", y="Count", use_container_width=True)
        else:
            st.info("No status data available")
    with right:
        st.markdown("**Match Tier Distribution**")
        if "match_tier" in df.columns:
            tier_dist = df["match_tier"].value_counts().reset_index()
            tier_dist.columns = ["Tier", "Count"]
            tier_dist["Tier"] = tier_dist["Tier"].astype(str)
            st.bar_chart(tier_dist, x="Tier", y="Count", use_container_width=True)
        else:
            st.info("No match data available")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top: 1.5rem; font-size: 1.25rem;'>Recent Records</div>", unsafe_allow_html=True)
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
