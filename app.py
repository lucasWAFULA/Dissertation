from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from src.app_state import APP_END_DATE, APP_START_DATE, get_app_context
from src.data_loader import load_optional_kenya_adm0_geojson, load_optional_kenya_adm1_geojson
from src.streamlit_plotly import plotly_chart_interactive
from src.theme import apply_custom_theme, render_badge
from src.visuals import (
    make_anomaly_timeline,
    build_early_warning_summary,
    build_kpi_summary,
    make_alerts_table,
    make_alerts_over_time_line,
    make_commodity_anomaly_trend,
    make_commodity_heatmap,
    make_county_anomaly_heatmap,
    make_feature_correlation_heatmap,
    make_feature_importance_chart,
    make_geo_anomaly_map,
    make_price_distribution_boxplot,
    make_price_trend_chart,
    make_score_distribution,
    make_severity_bar_chart,
    make_severity_donut,
    make_top_affected_commodities_bar,
)


st.set_page_config(
    page_title="Food Price Anomaly Detection Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
)

apply_custom_theme()


def _format_metric(value: float) -> str:
    if isinstance(value, float) and math.isnan(value):
        return "N/A"
    return f"{value:.3f}"


context = get_app_context()
bundle = context["bundle"]
dashboard_df = context["dashboard_df"]
combined_df = context["combined_df"]
raw_wfp_df = context["raw_wfp_df"]
county_reference = context["county_reference"]
pipeline_summary = context["pipeline_summary"]
artifact_status = context["artifact_status"]
deployed_model_meta = context["deployed_model_meta"]
kenya_geojson = load_optional_kenya_adm1_geojson()
kenya_adm0_geojson = load_optional_kenya_adm0_geojson()

st.title("Food Commodity Price Anomaly Detection Dashboard")
st.caption(
    "Dashboard page for historical monitoring and long-horizon outlook from 2020 to 2040. Use the sidebar to filter, and use the separate pages for uploaded-data alerts and SHAP interpretability."
)

if bundle.warning:
    st.warning(bundle.warning)

commodities = sorted(combined_df["commodity"].dropna().unique().tolist())
counties = sorted(combined_df["COUNTY"].dropna().unique().tolist())

# --- Header controls (wireframe-style) ---
header_cols = st.columns([1.25, 1.1, 1.1, 0.9])
with header_cols[0]:
    selected_dates = st.slider(
        "Time Range",
        min_value=APP_START_DATE,
        max_value=APP_END_DATE,
        value=(APP_START_DATE, APP_END_DATE),
    )
with header_cols[1]:
    selected_commodities = st.multiselect(
        "Commodity",
        options=commodities,
        default=commodities[: min(5, len(commodities))],
    )
with header_cols[2]:
    selected_counties = st.multiselect("County", options=counties, default=[])
with header_cols[3]:
    st.markdown("**Model**")
    st.markdown(f"`{artifact_status['best_model']}`")

# --- Advanced controls (reduced sidebar) ---
with st.sidebar:
    st.header("Controls")
    render_badge("Deployed Model", artifact_status["best_model"], tone="blue")
    render_badge("Scoring Mode", artifact_status["mode"])
    selected_severity = st.multiselect(
        "Severity",
        options=["Low", "Medium", "High"],
        default=["Low", "Medium", "High"],
    )
    price_min = float(dashboard_df["price_real"].min())
    price_max = float(dashboard_df["price_real"].max())
    selected_price_range = st.slider(
        "Price range (real, per kg)",
        min_value=float(round(price_min, 2)),
        max_value=float(round(price_max, 2)),
        value=(float(round(price_min, 2)), float(round(price_max, 2))),
    )

filtered_df = combined_df.copy()
if selected_commodities:
    filtered_df = filtered_df[filtered_df["commodity"].isin(selected_commodities)]
if selected_counties:
    filtered_df = filtered_df[filtered_df["COUNTY"].isin(selected_counties)]
filtered_df = filtered_df[
    filtered_df["date"].between(pd.Timestamp(selected_dates[0]), pd.Timestamp(selected_dates[1]))
]
if selected_severity:
    filtered_df = filtered_df[filtered_df["severity"].astype(str).isin(selected_severity)]
filtered_df = filtered_df[
    filtered_df["price_real"].between(selected_price_range[0], selected_price_range[1])
]

raw_filtered = raw_wfp_df.copy()
if selected_commodities:
    raw_filtered = raw_filtered[raw_filtered["commodity"].isin(selected_commodities)]
if selected_counties:
    raw_filtered = raw_filtered[raw_filtered["county"].isin(selected_counties)]
raw_filtered = raw_filtered[
    raw_filtered["date"].between(
        pd.Timestamp(selected_dates[0]),
        min(pd.Timestamp(selected_dates[1]), pd.Timestamp(dashboard_df["date"].max())),
    )
]

# WFP lat/lon for map markers: all time (same commodity/county filters) so markets stay visible
raw_map_coords = raw_wfp_df.copy()
if selected_commodities:
    raw_map_coords = raw_map_coords[raw_map_coords["commodity"].isin(selected_commodities)]
if selected_counties:
    _cset = {str(c).strip().lower() for c in selected_counties}
    raw_map_coords = raw_map_coords[
        raw_map_coords["county"].astype(str).str.strip().str.lower().isin(_cset)
    ]

if filtered_df.empty:
    st.error("No records match the selected dashboard filters.")
    st.stop()

kpis = build_kpi_summary(filtered_df, raw_frame=raw_filtered)
included_types = ", ".join(sorted(filtered_df["record_type"].astype(str).unique()))
st.markdown(
    f"""
**Detection threshold:** `{artifact_status['threshold']}`  |  **Records (historical):** `{pipeline_summary['rows']:,}`  
**Current view:** {filtered_df['commodity'].nunique()} commodities, {filtered_df['COUNTY'].nunique()} counties, {filtered_df['date'].min():%b %Y} to {filtered_df['date'].max():%b %Y}  |  **Included data:** {included_types}
"""
)

st.subheader("KPI Summary")
metric_cols = st.columns(5)
metric_cols[0].metric("Commodities", f"{kpis['total_commodities']:,}")
metric_cols[1].metric("Markets", f"{kpis['total_markets']:,}")
metric_cols[2].metric("Anomalies (latest month)", f"{kpis['latest_month_anomalies']:,}")
metric_cols[3].metric("Max price spike", f"{kpis['highest_price_spike']:.1f}%")
metric_cols[4].metric("Avg risk score", _format_metric(kpis["avg_risk_score"]))

st.subheader("Core Analytics")
main_row = st.columns([1.7, 1.0])
with main_row[0]:
    plotly_chart_interactive(make_price_trend_chart(filtered_df))
with main_row[1]:
    plotly_chart_interactive(
        make_geo_anomaly_map(
            filtered_df,
            county_reference,
            all_47_counties=True,
            map_height=520,
            kenya_adm1_geojson=kenya_geojson,
            kenya_adm0_geojson=kenya_adm0_geojson,
            raw_market_frame=raw_map_coords,
        ),
    )

# ---- Anomaly section: early warning + threshold ----
date_min_str = filtered_df["date"].min().strftime("%b %Y") if not filtered_df.empty else ""
date_max_str = filtered_df["date"].max().strftime("%b %Y") if not filtered_df.empty else ""
date_range_str = f"{date_min_str} – {date_max_str}" if date_min_str else ""
threshold_str = f"> {artifact_status['threshold']}"

early = build_early_warning_summary(filtered_df)
st.subheader("Anomaly monitoring")
ew_col1, ew_col2, ew_col3 = st.columns([2, 1, 1])
with ew_col1:
    aff = early["affected_commodities"][:5]
    aff_text = ", ".join(aff) if aff else "None"
    latest = early["latest_alert_date"]
    latest_text = latest.strftime("%b %Y") if latest is not None else "N/A"
    st.markdown(
        f"""
        **Early warning panel**  
        High severity alerts: **{early['high_severity_count']:,}**  
        Affected commodities: **{aff_text}**  
        Most affected county: **{early['most_affected_county']}**  
        Latest alert: **{latest_text}**
        """
    )
with ew_col2:
    st.info(f"**Alert threshold:** anomaly score {threshold_str}")
with ew_col3:
    st.caption(f"View period: {date_range_str}")

# Severity distribution (bar + donut) and alerts over time
row_sev = st.columns([1.2, 0.8])
with row_sev[0]:
    plotly_chart_interactive(
        make_severity_bar_chart(filtered_df, date_range_str=date_range_str, threshold_str=threshold_str),
    )
with row_sev[1]:
    plotly_chart_interactive(make_severity_donut(filtered_df, date_range_str=date_range_str))

plotly_chart_interactive(
    make_alerts_over_time_line(filtered_df, date_range_str=date_range_str),
)

st.subheader("Distribution & Patterns")
pattern_row = st.columns(2)
with pattern_row[0]:
    plotly_chart_interactive(make_commodity_heatmap(filtered_df))
with pattern_row[1]:
    plotly_chart_interactive(make_top_affected_commodities_bar(filtered_df, top_n=10))

st.subheader("Statistical Insight")
stats_row = st.columns(2)
with stats_row[0]:
    plotly_chart_interactive(make_price_distribution_boxplot(filtered_df))
with stats_row[1]:
    plotly_chart_interactive(make_feature_correlation_heatmap(filtered_df))

st.subheader("Alert Timeline")
plotly_chart_interactive(make_anomaly_timeline(filtered_df))

st.subheader("County & Commodity Hotspots")
row_anom = st.columns(2)
with row_anom[0]:
    plotly_chart_interactive(make_county_anomaly_heatmap(filtered_df))
with row_anom[1]:
    plotly_chart_interactive(make_commodity_anomaly_trend(filtered_df))

# Alerts table + model summary
row_three = st.columns([1.5, 1.0])
with row_three[0]:
    st.subheader("Anomaly Alerts Panel")
    _watch = st.checkbox(
        "Include Medium/High severity rows (more commodities; scroll full list)",
        value=True,
        key="dashboard_alerts_watchlist",
    )

    def _severity_style(value: str) -> str:
        colors = {
            "Low": "background-color: #E8F5E9; color: #1B5E20;",
            "Medium": "background-color: #FFF8E1; color: #F57F17;",
            "High": "background-color: #FFEBEE; color: #B71C1C;",
        }
        return colors.get(value, "")

    def _source_style(value: str) -> str:
        if value == "Model anomaly":
            return "font-weight: 600; color: #1B5E20;"
        if value == "Elevated risk":
            return "font-weight: 500; color: #5D4037;"
        return ""

    alerts = make_alerts_table(filtered_df, include_elevated=_watch)
    st.caption(f"**{len(alerts):,}** rows · sorted by commodity — scroll inside the table.")
    if alerts.empty:
        st.info("No alert rows for current filters. Widen the time range or enable the watchlist above.")
    else:
        styled = alerts.style.map(_severity_style, subset=["status_level"]).map(
            _source_style, subset=["source"]
        )
        st.dataframe(styled, use_container_width=True, hide_index=True, height=520)

with row_three[1]:
    st.subheader("Deployed Model Summary")
    score_chart = make_score_distribution(filtered_df)
    if score_chart is not None:
        plotly_chart_interactive(score_chart)

    feature_chart = make_feature_importance_chart(bundle.model, bundle.feature_names)
    if feature_chart is not None:
        plotly_chart_interactive(feature_chart)

    if deployed_model_meta:
        model_cols = st.columns(3)
        model_cols[0].metric("F1-score", f"{float(deployed_model_meta.get('F1', float('nan'))):.3f}")
        model_cols[1].metric("Recall", f"{float(deployed_model_meta.get('Recall', float('nan'))):.3f}")
        model_cols[2].metric("AUC", f"{float(deployed_model_meta.get('AUC', float('nan'))):.3f}")

with st.expander("Dashboard notes"):
    st.markdown(
        """
This page covers the 2020 to 2040 monitoring horizon by combining historical observations with forward projections.
For uploaded-data alert generation, use the `Anomaly Detection` page. For SHAP-based explanation, use the `Interpretability` page.
"""
    )

