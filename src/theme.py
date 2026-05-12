from __future__ import annotations

import base64
import mimetypes

import streamlit as st

from src.config import MAIN_PANEL_BACKGROUND_IMAGE

# Agriculture-oriented palette: sage, earth, harvest gold, forest green, terracotta
AGRI = {
    "bg_main": "#EEF2E8",        # light sage
    "bg_sidebar": "#E2EAD9",     # (fallback)
    "bg_control_panel": "#E5DFD4",
    "bg_control_panel_end": "#DDD6C8",
    "border_sidebar": "#B8A99A",
    "border_card": "#C5D4BC",
    "text_primary": "#2C3318",
    "text_secondary": "#4A5D44",
    "accent_primary": "#3D6B35",
    "accent_gold": "#8B6914",
    "low": "#3D7C47",
    "medium": "#B8860B",
    "high": "#A63D2E",
    "card_bg": "#FFFFFF",
    "tag_bg": "#E8F0E4",
    "tag_text": "#2D5A27",
    "model_badge_bg": "#E3EDE0",
    "model_badge_text": "#2D5A27",
    "chart_grid": "#E0E8DC",
    "forecast_band": "#E8EDE4",
}

# Dark green control panel (sidebar): high contrast, dense type
CP = {
    "bg_a": "#07180f",
    "bg_b": "#0f2918",
    "bg_c": "#143d24",
    "border": "#3d9f5c",
    "border_soft": "rgba(120,200,140,0.35)",
    "text": "#F2FFF2",
    "text_label": "#E0F8E4",
    "text_muted": "#9FD4A8",
    "text_dim": "#7CB892",
    "input_bg": "#FAFFFA",
    "input_text": "#081208",
    "input_border": "#4A9F5C",
    "btn_from": "#E8FF8A",
    "btn_to": "#B8E85A",
    "btn_text": "#031005",
    "code_bg": "rgba(0,24,12,0.65)",
    "code_text": "#E8FFD8",
    # Multipage nav (visible on dark green + on active pill)
    "nav_rb_light": "#FFAD9E",
    "nav_rb_hover": "#FFD4CC",
    "nav_rb_active": "#6E1810",
    "nav_rb_border": "rgba(220, 100, 85, 0.45)",
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
        else f"linear-gradient(180deg, {AGRI['bg_main']} 0%, #E6EDE0 100%)"
    )
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

        .stApp {{
            background: {app_bg};
            color: {AGRI["text_primary"]};
            font-family: 'DM Sans', sans-serif;
        }}
        {main_bg}

        /* ——— Right panel: readable surface over background image ——— */
        [data-testid="stMain"] .block-container,
        section.main .block-container {{
            background: rgba(252, 254, 249, 0.94) !important;
            backdrop-filter: blur(16px) saturate(1.08);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.98) !important;
            box-shadow:
                0 8px 48px rgba(12, 28, 14, 0.12),
                inset 0 1px 0 rgba(255, 255, 255, 0.9) !important;
            border-radius: 6px 6px 18px 18px;
            padding-top: 1.35rem !important;
            padding-bottom: 2.25rem !important;
            padding-left: 1.15rem !important;
            padding-right: 1.15rem !important;
        }}

        .block-container {{
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }}

        html, body, [class*="css"] {{
            font-family: 'DM Sans', sans-serif;
        }}

        /* Main: high-contrast type (near-black on light panel) */
        [data-testid="stMain"] h1, section.main h1 {{
            color: #0d180d !important;
            font-size: 28px !important;
            font-weight: 800 !important;
            letter-spacing: -0.03em;
            line-height: 1.18 !important;
            text-shadow: 0 1px 0 rgba(255,255,255,0.9);
        }}

        [data-testid="stMain"] h2, [data-testid="stMain"] h3,
        section.main h2, section.main h3 {{
            color: #0f1f0c !important;
            font-size: 21px !important;
            font-weight: 800 !important;
            line-height: 1.22 !important;
            margin-top: 0.85rem !important;
            margin-bottom: 0.35rem !important;
        }}

        [data-testid="stMain"] p, [data-testid="stMain"] li,
        [data-testid="stMain"] .stMarkdown, section.main .stMarkdown {{
            color: #1a2a16 !important;
            font-size: 16px !important;
            line-height: 1.5 !important;
            font-weight: 500;
        }}

        [data-testid="stMain"] .stCaption, section.main .stCaption {{
            color: #2d4a28 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            line-height: 1.4 !important;
        }}

        [data-testid="stMain"] label, [data-testid="stMain"] [data-testid="stWidgetLabel"] label {{
            color: #142814 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }}

        [data-testid="stMain"] .stCheckbox label p,
        [data-testid="stMain"] .stRadio label p {{
            color: #1a2a16 !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }}

        h1 {{
            color: {AGRI["text_primary"]} !important;
            font-size: 22px !important;
            font-weight: 700 !important;
        }}

        h2, h3 {{
            color: {AGRI["text_primary"]} !important;
            font-size: 18px !important;
            font-weight: 600 !important;
        }}

        p, li, label, .stCaption, .stMarkdown, .stText {{
            color: {AGRI["text_secondary"]};
            font-size: 14px;
        }}

        div[data-testid="column"] > div {{
            height: 100%;
        }}

        .element-container, .stMarkdown, .stPlotlyChart, .stDataFrame, [data-testid="stMetric"] {{
            margin-bottom: 0.85rem;
        }}

        /* ——— Dark green control panel (sidebar) ——— */
        [data-testid="stSidebar"] {{
            background: linear-gradient(165deg, {CP["bg_c"]} 0%, {CP["bg_b"]} 42%, {CP["bg_a"]} 100%) !important;
            border-right: 3px solid {CP["border"]} !important;
            box-shadow: 6px 0 24px rgba(0,0,0,0.35);
        }}

        [data-testid="stSidebar"] .block-container {{
            padding: 0.55rem 0.65rem 0.75rem 0.65rem !important;
        }}

        [data-testid="stSidebar"] .element-container {{
            margin-bottom: 0.38rem !important;
        }}

        [data-testid="stSidebar"] h1 {{
            color: {CP["text"]} !important;
            font-size: 0.82rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
            border-bottom: 1px solid {CP["border_soft"]};
            padding-bottom: 0.35rem !important;
            margin-bottom: 0.45rem !important;
        }}

        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            color: {CP["text_label"]} !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            margin-top: 0.35rem !important;
            margin-bottom: 0.25rem !important;
        }}

        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
        [data-testid="stSidebar"] label {{
            color: {CP["text_label"]} !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
        }}

        [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] .stMarkdown li {{
            color: {CP["text"]} !important;
            font-size: 13px !important;
            line-height: 1.4 !important;
        }}

        [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {{
            color: {CP["text_muted"]} !important;
            font-size: 11.5px !important;
            line-height: 1.35 !important;
        }}

        [data-testid="stSidebar"] .stCheckbox label p, [data-testid="stSidebar"] .stCheckbox span,
        [data-testid="stSidebar"] .stRadio label p, [data-testid="stSidebar"] .stRadio span {{
            color: {CP["text"]} !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] .stDateInput input,
        [data-testid="stSidebar"] .stNumberInput input,
        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] .stTextArea textarea {{
            background-color: {CP["input_bg"]} !important;
            color: {CP["input_text"]} !important;
            border: 2px solid {CP["input_border"]} !important;
            border-radius: 6px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] span {{
            color: {CP["input_text"]} !important;
        }}

        [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {{
            background: {CP["btn_from"]} !important;
            color: {CP["btn_text"]} !important;
            border: 1px solid {CP["border"]} !important;
            font-weight: 600 !important;
            font-size: 12px !important;
        }}

        [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {{
            padding-top: 0.35rem;
        }}

        [data-testid="stSidebar"] .stSlider [data-testid="stThumbValue"] {{
            color: {CP["text"]} !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="tag"] {{
            background: rgba(255,255,255,0.12) !important;
            border: 1px solid {CP["border_soft"]} !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="tag"] span {{
            color: {CP["text"]} !important;
            font-weight: 600 !important;
        }}

        [data-testid="stSidebar"] .stButton button,
        [data-testid="stSidebar"] .stDownloadButton button {{
            background: linear-gradient(180deg, {CP["btn_from"]} 0%, {CP["btn_to"]} 100%) !important;
            color: {CP["btn_text"]} !important;
            border: 2px solid #2d6b28 !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
            font-size: 13px !important;
            letter-spacing: 0.02em;
        }}

        [data-testid="stSidebar"] .stButton button:hover,
        [data-testid="stSidebar"] .stDownloadButton button:hover {{
            filter: brightness(1.08);
            color: {CP["btn_text"]} !important;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"] {{
            background: rgba(255,255,255,0.07) !important;
            border: 1px solid {CP["border_soft"]} !important;
            border-radius: 8px !important;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"] summary,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary p,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary span {{
            color: {CP["text"]} !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"] .stMarkdown code,
        [data-testid="stSidebar"] code {{
            background: {CP["code_bg"]} !important;
            color: {CP["code_text"]} !important;
            font-size: 11px !important;
            border: 1px solid {CP["border_soft"]} !important;
            padding: 2px 5px !important;
            border-radius: 4px !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] small {{
            color: {CP["text_muted"]} !important;
            font-size: 11.5px !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
            background: rgba(255,255,255,0.08) !important;
            border: 2px dashed {CP["border_soft"]} !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span {{
            color: {CP["text_label"]} !important;
            font-size: 12.5px !important;
            font-weight: 600 !important;
        }}

        [data-testid="stSidebar"] .stAlert {{
            font-size: 12.5px !important;
            line-height: 1.4 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
            gap: 0.35rem;
        }}

        [data-testid="stSidebar"] hr {{
            border-color: {CP["border_soft"]} !important;
            margin: 0.5rem 0 !important;
        }}

        /* Multipage links: app, Anomaly Detection, Interpretability */
        [data-testid="stSidebarNav"] {{
            padding-bottom: 0.65rem !important;
            margin-bottom: 0.45rem !important;
            border-bottom: 1px solid {CP["nav_rb_border"]} !important;
        }}

        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"] {{
            text-decoration: none !important;
            border-radius: 8px !important;
        }}

        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"] span,
        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"] p {{
            color: {CP["nav_rb_light"]} !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            letter-spacing: 0.02em !important;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45) !important;
        }}

        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"]:not([aria-current="page"]) span,
        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"]:not([aria-current="page"]) p {{
            color: {CP["nav_rb_light"]} !important;
        }}

        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"]:hover span,
        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"]:hover p {{
            color: {CP["nav_rb_hover"]} !important;
        }}

        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] span,
        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] p {{
            color: {CP["nav_rb_active"]} !important;
            font-weight: 800 !important;
            text-shadow: none !important;
        }}

        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{
            background: rgba(255, 220, 210, 0.95) !important;
            border: 1px solid #C45A4A !important;
        }}

        [data-testid="stSidebarNav"] ul[data-testid="stSidebarNavItems"] li {{
            margin-bottom: 0.2rem !important;
        }}

        /* Fallback if link text is not wrapped in span/p */
        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"]:not([aria-current="page"]) {{
            color: {CP["nav_rb_light"]} !important;
        }}

        [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{
            color: {CP["nav_rb_active"]} !important;
        }}

        [data-testid="stMetric"] {{
            background-color: {AGRI["card_bg"]};
            border-radius: 10px;
            padding: 0.9rem;
            border: 1px solid {AGRI["border_card"]};
            box-shadow: 0 2px 8px rgba(45,58,39,0.06);
            min-height: 122px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            overflow: hidden;
        }}

        /* Main panel: bolder KPIs */
        [data-testid="stMain"] [data-testid="stMetric"] {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F6FAF4 100%) !important;
            border: 2px solid #7A9B72 !important;
            border-radius: 12px !important;
            padding: 1rem 1.05rem !important;
            box-shadow: 0 4px 20px rgba(20, 45, 25, 0.1), inset 0 1px 0 #fff !important;
            min-height: 128px !important;
        }}

        [data-testid="stMetricLabel"] {{
            margin-bottom: 0.45rem;
        }}

        [data-testid="stMetricLabel"] p {{
            color: #2d3f28 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            line-height: 1.35 !important;
            white-space: normal !important;
            overflow-wrap: anywhere;
        }}

        [data-testid="stMain"] [data-testid="stMetricLabel"] p {{
            color: #1a3014 !important;
            font-size: 15px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stMetricValue"] {{
            color: {AGRI["text_primary"]} !important;
            font-size: 1.7rem !important;
            font-weight: 700 !important;
            line-height: 1.15 !important;
            white-space: normal !important;
            overflow-wrap: anywhere;
        }}

        [data-testid="stMain"] [data-testid="stMetricValue"] {{
            color: #061806 !important;
            font-size: 1.85rem !important;
            font-weight: 800 !important;
        }}

        .stDataFrame, [data-testid="stExpander"], .stAlert {{
            background-color: {AGRI["card_bg"]};
            border-radius: 10px;
            border: 1px solid {AGRI["border_card"]};
            box-shadow: 0 2px 8px rgba(45,58,39,0.06);
            padding: 0.35rem;
            overflow: hidden;
        }}

        /* Plotly: avoid clipping mode bar / zoom; keep pointer events on chart */
        .stPlotlyChart {{
            background-color: {AGRI["card_bg"]};
            border-radius: 10px;
            border: 1px solid {AGRI["border_card"]};
            box-shadow: 0 2px 8px rgba(45,58,39,0.06);
            padding: 0.35rem;
            overflow: visible !important;
        }}

        .stPlotlyChart .js-plotly-plot,
        .stPlotlyChart .plot-container {{
            pointer-events: auto !important;
            touch-action: pan-x pan-y pinch-zoom !important;
        }}

        /* Main: charts & tables stand out */
        [data-testid="stMain"] .stPlotlyChart {{
            background: #FDFEFC !important;
            border: 2px solid #5A7D52 !important;
            border-radius: 12px !important;
            padding: 0.55rem 0.65rem 0.75rem 0.65rem !important;
            box-shadow: 0 6px 28px rgba(15, 40, 18, 0.12) !important;
            overflow: visible !important;
        }}

        [data-testid="stMain"] .stDataFrame {{
            background: #FDFEFC !important;
            border: 2px solid #6B8B62 !important;
            border-radius: 10px !important;
            padding: 0.45rem !important;
            font-size: 14px !important;
        }}

        [data-testid="stMain"] [data-testid="stExpander"] {{
            background: #FAFCF8 !important;
            border: 2px solid #8AAA82 !important;
            border-radius: 10px !important;
        }}

        [data-testid="stMain"] [data-testid="stExpander"] summary p,
        [data-testid="stMain"] [data-testid="stExpander"] summary span {{
            color: #0d1a0d !important;
            font-size: 15px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stMain"] .stAlert {{
            border: 2px solid #6B9B5E !important;
            font-size: 14px !important;
            line-height: 1.45 !important;
        }}

        .stPlotlyChart > div,
        .stDataFrame > div {{
            width: 100%;
        }}

        .js-plotly-plot, .plotly, .plot-container {{
            max-width: 100%;
        }}

        .status-label {{
            font-size: 12px;
            font-weight: 700;
            color: #3d5238;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        [data-testid="stMain"] .status-label {{
            font-size: 13px !important;
            color: #061806 !important;
            letter-spacing: 0.05em !important;
        }}

        .status-badge {{
            display: inline-block;
            background: #E8F5E4;
            color: #0d280d;
            border: 2px solid #5A8F52;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 12px;
            max-width: 100%;
            white-space: normal;
            overflow-wrap: anywhere;
        }}

        [data-testid="stMain"] .status-badge {{
            font-size: 15px !important;
            padding: 10px 16px !important;
            box-shadow: 0 2px 12px rgba(30, 70, 35, 0.12);
        }}

        .model-badge {{
            display: inline-block;
            background: #E3F0DE;
            color: #062006;
            border: 2px solid #3D6B35;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 12px;
            max-width: 100%;
            white-space: normal;
            overflow-wrap: anywhere;
        }}

        [data-testid="stMain"] .model-badge {{
            font-size: 15px !important;
            padding: 10px 16px !important;
            box-shadow: 0 2px 12px rgba(30, 70, 35, 0.12);
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
