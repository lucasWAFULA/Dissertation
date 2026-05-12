from __future__ import annotations

import base64
import mimetypes

import streamlit as st

from src.config import MAIN_PANEL_BACKGROUND_IMAGE

# Professional Intelligence/Fintech palette (Deep Dark Mode)
AGRI = {
    "bg_main": "#0F172A",        # Slate 900
    "bg_sidebar": "#111827",     # Gray 900
    "bg_control_panel": "#1E293B",
    "bg_control_panel_end": "#0F172A",
    "border_sidebar": "#334155",
    "border_card": "#334155",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "accent_primary": "#10B981", # Emerald
    "accent_sky": "#0EA5E9",     # Sky Blue
    "low": "#10B981",
    "medium": "#F59E0B",
    "high": "#EF4444",
    "card_bg": "#1E293B",        # Slate 800
    "tag_bg": "#334155",
    "tag_text": "#F1F5F9",
    "model_badge_bg": "rgba(16, 185, 129, 0.1)",
    "model_badge_text": "#10B981",
    "chart_grid": "#334155",
    "forecast_band": "rgba(14, 165, 233, 0.1)",
}

# Sidebar/Control Panel (CP) styling
CP = {
    "bg_a": "#0F172A",
    "bg_b": "#1E293B",
    "bg_c": "#111827",
    "border": "#334155",
    "border_soft": "rgba(148, 163, 184, 0.05)",
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
    "nav_rb_light": "#94A3B8",
    "nav_rb_hover": "#F8FAFC",
    "nav_rb_active": "#FFFFFF",
    "nav_rb_border": "rgba(16, 185, 129, 0.4)",
}

def apply_custom_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

        .stApp {{
            background: {AGRI['bg_main']};
            color: {AGRI["text_primary"]};
            font-family: 'Inter', sans-serif;
        }}

        /* --- Main Content Surface --- */
        [data-testid="stMain"] .block-container {{
            background: transparent !important;
            padding: 2.5rem !important;
        }}

        /* Typography */
        h1, h2, h3 {{
            font-family: 'Outfit', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }}

        [data-testid="stMain"] h1 {{
            color: #FFFFFF !important;
            font-size: 2.5rem !important;
            margin-bottom: 1rem !important;
        }}

        [data-testid="stMain"] p, [data-testid="stMain"] li {{
            color: {AGRI['text_secondary']} !important;
            font-size: 1.05rem !important;
        }}

        /* --- Sidebar Improvements --- */
        [data-testid="stSidebar"] {{
            background: {AGRI['bg_sidebar']} !important;
            border-right: 1px solid {AGRI['border_sidebar']} !important;
        }}

        /* Navigation Links */
        [data-testid="stSidebarNav"] ul {{
            padding-top: 2rem !important;
        }}

        [data-testid="stSidebarNav"] a {{
            padding: 0.85rem 1.25rem !important;
            margin: 0.25rem 0.75rem !important;
            border-radius: 12px !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            border-left: 4px solid transparent !important;
            text-decoration: none !important;
        }}

        [data-testid="stSidebarNav"] a:hover {{
            background: rgba(255, 255, 255, 0.05) !important;
            transform: translateX(4px);
        }}

        /* Active Page Highlighting */
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: rgba(16, 185, 129, 0.15) !important;
            border-left: 4px solid {AGRI['accent_primary']} !important;
            box-shadow: inset 0 0 20px rgba(16, 185, 129, 0.05) !important;
        }}

        [data-testid="stSidebarNav"] a span {{
            color: #94A3B8 !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            transition: color 0.2s ease;
        }}

        [data-testid="stSidebarNav"] a[aria-current="page"] span {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
        }}

        /* --- Metrics & Cards --- */
        [data-testid="stMetric"] {{
            background: {AGRI['card_bg']} !important;
            border: 1px solid {AGRI['border_card']} !important;
            border-radius: 16px !important;
            padding: 1.5rem !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
        }}

        [data-testid="stMetricLabel"] p {{
            color: {AGRI['text_secondary']} !important;
            font-size: 0.85rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }}

        [data-testid="stMetricValue"] div {{
            color: #FFFFFF !important;
            font-family: 'Outfit', sans-serif !important;
        }}

        /* Charts Container */
        .stPlotlyChart {{
            background: {AGRI['card_bg']} !important;
            border: 1px solid {AGRI['border_card']} !important;
            border-radius: 16px !important;
            padding: 1rem !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        }}

        /* Buttons & Controls */
        .stButton>button {{
            background: linear-gradient(135deg, {CP['btn_from']} 0%, {CP['btn_to']} 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.5rem !important;
            transition: all 0.3s ease !important;
        }}

        .stButton>button:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.4) !important;
        }}
        
        /* Badges */
        .status-badge {{
            background: rgba(16, 185, 129, 0.1);
            color: #10B981;
            padding: 4px 12px;
            border-radius: 99px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }}
        
        .model-badge {{
            background: rgba(14, 165, 233, 0.1);
            color: #0EA5E9;
            padding: 4px 12px;
            border-radius: 99px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }}
        
        .status-label {{
            font-size: 0.7rem;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }}

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
