from __future__ import annotations

import base64
import mimetypes

import streamlit as st

from src.config import MAIN_PANEL_BACKGROUND_IMAGE

# Professional Intelligence/Fintech palette
AGRI = {
    "bg_main": "#F7F8FA",        # light grey background
    "bg_sidebar": "#111827",     # deep charcoal
    "bg_control_panel": "#1F2937",
    "bg_control_panel_end": "#111827",
    "border_sidebar": "#374151",
    "border_card": "#E5E7EB",
    "text_primary": "#111827",
    "text_secondary": "#4B5563",
    "accent_primary": "#10B981", # emerald accent
    "accent_gold": "#F59E0B",
    "low": "#10B981",
    "medium": "#F59E0B",
    "high": "#EF4444",
    "card_bg": "#FFFFFF",
    "tag_bg": "#F3F4F6",
    "tag_text": "#1F2937",
    "model_badge_bg": "#ECFDF5",
    "model_badge_text": "#065F46",
    "chart_grid": "#F3F4F6",
    "forecast_band": "#F9FAFB",
}

# Sidebar/Control Panel (CP) styling
CP = {
    "bg_a": "#0F172A",
    "bg_b": "#1E293B",
    "bg_c": "#111827",
    "border": "#334155",
    "border_soft": "rgba(148, 163, 184, 0.1)",
    "text": "#F8FAFC",
    "text_label": "#94A3B8",
    "text_muted": "#64748B",
    "text_dim": "#475569",
    "input_bg": "#1E293B",
    "input_text": "#F8FAFC",
    "input_border": "#334155",
    "btn_from": "#10B981",
    "btn_to": "#059669",
    "btn_text": "#FFFFFF",
    "code_bg": "rgba(15, 23, 42, 0.8)",
    "code_text": "#34D399",
    # Multipage nav
    "nav_rb_light": "#94A3B8",
    "nav_rb_hover": "#F8FAFC",
    "nav_rb_active": "#FFFFFF",
    "nav_rb_border": "rgba(16, 185, 129, 0.4)",
}


_main_bg_css_cache: tuple[float | None, str] = (None, "")


def _main_panel_background_css() -> str:
    global _main_bg_css_cache
    path = MAIN_PANEL_BACKGROUND_IMAGE
    if not path.is_file():
        return ""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return ""
    if _main_bg_css_cache[0] == mtime:
        return _main_bg_css_cache[1]
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "image/png"
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    url = f"data:{mime};base64,{b64}"
    css = f"""
        /* Right panel (main): full-cover background image */
        [data-testid="stMain"],
        section.main,
        .main {{
            background-image: url("{url}") !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
            min-height: 100vh !important;
        }}
        [data-testid="stMain"] > div,
        section.main > div {{
            background-color: transparent !important;
        }}
        /* Image still visible around edges; inner panel styled in apply_custom_theme */
    """
    _main_bg_css_cache = (mtime, css)
    return css


def apply_custom_theme() -> None:
    main_bg = _main_panel_background_css()
    app_bg = (
        "transparent"
        if main_bg
        else AGRI['bg_main']
    )
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        .stApp {{
            background: {app_bg};
            color: {AGRI["text_primary"]};
            font-family: 'Inter', sans-serif;
        }}
        {main_bg}

        /* ——— Right panel surface ——— */
        [data-testid="stMain"] .block-container,
        section.main .block-container {{
            background: rgba(255, 255, 255, 0.8) !important;
            backdrop-filter: blur(20px) saturate(1.2);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 2rem !important;
            margin-top: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        /* Typography */
        [data-testid="stMain"] h1 {{
            color: #111827 !important;
            font-size: 2.25rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.025em;
            margin-bottom: 0.5rem !important;
        }}

        [data-testid="stMain"] h2, [data-testid="stMain"] h3 {{
            color: #111827 !important;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
        }}

        [data-testid="stMain"] p, [data-testid="stMain"] li {{
            color: #4B5563 !important;
            font-size: 1rem !important;
            line-height: 1.6 !important;
        }}

        [data-testid="stMain"] .stCaption {{
            color: #6B7280 !important;
            font-size: 0.875rem !important;
        }}

        /* ——— Sidebar ——— */
        [data-testid="stSidebar"] {{
            background: {CP["bg_c"]} !important;
            border-right: 1px solid {CP["border"]} !important;
        }}

        [data-testid="stSidebar"] .block-container {{
            padding: 1.5rem 1rem !important;
        }}

        [data-testid="stSidebarNav"] {{
            background: transparent !important;
            margin-bottom: 2rem !important;
        }}

        [data-testid="stSidebarNav"] ul {{
            padding-top: 1rem !important;
        }}

        [data-testid="stSidebarNav"] a {{
            padding: 0.75rem 1rem !important;
            margin-bottom: 0.5rem !important;
            border-radius: 0.5rem !important;
            transition: all 0.2s ease !important;
            border-left: 3px solid transparent !important;
        }}

        [data-testid="stSidebarNav"] a:hover {{
            background: rgba(255, 255, 255, 0.05) !important;
        }}

        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: rgba(16, 185, 129, 0.1) !important;
            border-left: 3px solid #10B981 !important;
        }}

        [data-testid="stSidebarNav"] a span {{
            color: {CP["nav_rb_light"]} !important;
            font-weight: 500 !important;
        }}

        [data-testid="stSidebarNav"] a[aria-current="page"] span {{
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }}

        /* Sidebar Headers */
        [data-testid="stSidebar"] h1 {{
            color: #94A3B8 !important;
            font-size: 0.75rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.1em !important;
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
        }}

        /* Form Controls in Sidebar */
        [data-testid="stSidebar"] [data-baseweb="select"] > div {{
            background-color: {CP["input_bg"]} !important;
            border: 1px solid {CP["input_border"]} !important;
            color: #F8FAFC !important;
        }}

        [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {{
            background: #10B981 !important;
            color: white !important;
        }}

        /* Metrics */
        [data-testid="stMetric"] {{
            background: white !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1) !important;
        }}

        [data-testid="stMetricLabel"] p {{
            color: #6B7280 !important;
            font-size: 0.875rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.025em !important;
        }}

        [data-testid="stMetricValue"] div {{
            color: #111827 !important;
            font-size: 1.875rem !important;
            font-weight: 700 !important;
        }}

        /* Charts */
        .stPlotlyChart {{
            background: white !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1) !important;
        }}

        /* Custom KPI Card Style */
        .kpi-card {{
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease;
        }}
        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .kpi-label {{
            color: #6B7280;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .kpi-value {{
            color: #111827;
            font-size: 1.5rem;
            font-weight: 700;
            margin-top: 0.25rem;
        }}
        .kpi-trend {{
            font-size: 0.875rem;
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
        }}
        .trend-up {{ color: #10B981; }}
        .trend-down {{ color: #EF4444; }}

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_badge(label: str, value: str, tone: str = "brown") -> None:
    badge_class = "model-badge" if tone == "blue" else "status-badge"
    st.markdown(
        f"""
        <div class="status-label">{label}</div>
        <div class="{badge_class}">{value}</div>
        """,
        unsafe_allow_html=True,
    )
