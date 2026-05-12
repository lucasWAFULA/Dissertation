from __future__ import annotations

import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

from src.app_state import (
    APP_END_DATE,
    APP_START_DATE,
    build_uploaded_scored_dataset,
    get_artifacts,
    merge_scored_with_uploads,
)
from src.scoring_client import fetch_model_info, score_market_via_api
from src.data_loader import REQUIRED_WFP_COLUMNS
from src.ingestion import (
    CLIMATE_TEMPLATE_COLUMNS,
    ECONOMIC_TEMPLATE_COLUMNS,
    GLOBAL_PRICE_TEMPLATE_COLUMNS,
    INFRA_TEMPLATE_COLUMNS,
    MARKET_PRICE_TEMPLATE_COLUMNS,
    SHOCK_TEMPLATE_COLUMNS,
    harmonize_climate_data,
    harmonize_economic_data,
    harmonize_global_prices,
    harmonize_infrastructure_data,
    harmonize_market_price_data,
    harmonize_shock_data,
    read_uploaded_table,
    validate_market_upload,
    validate_upload,
    validation_summary_frame,
)
from src.streamlit_plotly import plotly_chart_interactive
from src.theme import apply_custom_theme, render_badge
from src.visuals import (
    make_alerts_table,
    make_alerts_over_time_line,
    make_commodity_anomaly_trend,
    make_county_anomaly_heatmap,
    make_price_trend_chart,
    make_severity_bar_chart,
    make_severity_donut,
)


st.set_page_config(page_title="Forensic Audit | Market Price Pulse AI", page_icon="🚨", layout="wide")
apply_custom_theme()


def _secrets_scoring_api_url() -> str:
    try:
        return str(
            st.secrets.get("SCORING_API_URL", "")
            or st.secrets.get("STREAMLIT_SCORING_API_URL", "")
            or ""
        ).strip()
    except Exception:
        return ""


if "scoring_api_base_input" not in st.session_state:
    st.session_state.scoring_api_base_input = (
        os.environ.get("STREAMLIT_SCORING_API_URL", "").strip() or _secrets_scoring_api_url()
    )

st.title("🚨 Forensic Audit & Custom Ingestion")
st.markdown(
    """
    **Forensic Audit Mode**: Use this page to upload external market data, validate custom datasets, and run ad-hoc anomaly detection. 
    
    *Note: For automated daily monitoring, please refer to the **Market Intelligence** dashboard. Data uploaded here is processed in isolation for forensic review.*
    """
)

with st.expander("Supported upload templates"):
    st.markdown("**Market Price Data Upload**")
    st.code(", ".join(MARKET_PRICE_TEMPLATE_COLUMNS))
    st.caption("Also accepts the original WFP-style raw schema.")
    st.code(", ".join(REQUIRED_WFP_COLUMNS))
    st.markdown("**Economic Indicators Upload**")
    st.code(", ".join(ECONOMIC_TEMPLATE_COLUMNS))
    st.markdown("**Global Commodity Prices**")
    st.code(", ".join(GLOBAL_PRICE_TEMPLATE_COLUMNS))
    st.markdown("**Climate and Environmental Data**")
    st.code(", ".join(CLIMATE_TEMPLATE_COLUMNS))
    st.markdown("**Market Events and Shock Data**")
    st.code(", ".join(SHOCK_TEMPLATE_COLUMNS))
    st.markdown("**Spatial Infrastructure Data**")
    st.code(", ".join(INFRA_TEMPLATE_COLUMNS))


def _load_module(
    label: str,
    key: str,
    required_columns: list[str],
    duplicate_subset: list[str],
    help_text: str,
    date_column: str | None = "date",
) -> tuple[pd.DataFrame | None, object | None]:
    uploaded_file = st.file_uploader(label, type=["csv", "xlsx"], key=key, help=help_text)
    if uploaded_file is None:
        return None, None

    try:
        frame = read_uploaded_table(uploaded_file)
    except Exception as exc:
        st.error(f"{label}: could not read file - {exc}")
        return None, None

    review = validate_upload(
        dataset_name=label,
        df=frame,
        required_columns=required_columns,
        date_column=date_column,
        duplicate_subset=duplicate_subset,
    )
    return frame, review


def _load_market_module() -> tuple[pd.DataFrame | None, object | None]:
    uploaded_file = st.file_uploader(
        "Upload Market Prices",
        type=["csv", "xlsx"],
        key="market_prices_upload",
        help="Required primary dataset for anomaly detection.",
    )
    if uploaded_file is None:
        return None, None

    try:
        frame = read_uploaded_table(uploaded_file)
    except Exception as exc:
        st.error(f"Upload Market Prices: could not read file - {exc}")
        return None, None

    # Flexible market validation: template (date, commodity, market, county + one price column; unit optional) or full WFP schema
    market_review = validate_market_upload("Upload Market Prices", frame)
    if market_review.accepted:
        return frame, market_review

    raw_review = validate_upload(
        dataset_name="Upload Market Prices",
        df=frame,
        required_columns=REQUIRED_WFP_COLUMNS,
        date_column="date",
        duplicate_subset=["date", "admin2", "market", "commodity"],
    )
    return frame, raw_review


with st.sidebar:
    st.header("Data Ingestion")
    market_df, market_review = _load_market_module()
    economic_df, economic_review = _load_module(
        "Upload Economic Indicators",
        "economic_upload",
        ["date"],
        ["date"],
        "Optional. Overrides the default inflation reference data.",
    )
    global_df, global_review = _load_module(
        "Upload Global Prices",
        "global_upload",
        GLOBAL_PRICE_TEMPLATE_COLUMNS,
        ["date", "commodity"],
        "Optional. Overrides the default FPMA reference series.",
    )
    climate_df, climate_review = _load_module(
        "Upload Climate Indicators",
        "climate_upload",
        ["date", "county"],
        ["date", "county"],
        "Optional. Adds rainfall, SPI, and NDVI context.",
    )
    shock_df, shock_review = _load_module(
        "Upload Market Shocks",
        "shock_upload",
        SHOCK_TEMPLATE_COLUMNS,
        ["date", "event_type", "region"],
        "Optional. Adds contextual event information to the scored output.",
    )
    infra_df, infra_review = _load_module(
        "Upload Infrastructure Data",
        "infra_upload",
        INFRA_TEMPLATE_COLUMNS,
        ["market"],
        "Optional. Adds market accessibility context to the scored output.",
        date_column=None,
    )

    st.divider()
    st.subheader("Remote scoring")
    st.checkbox(
        "Score via FastAPI",
        key="use_api_scoring",
        help="Calls POST /v1/score on your API service. Economic / global / climate uploads are not sent to the API—only shock & infrastructure are merged after scoring.",
    )
    st.text_input(
        "API base URL",
        key="scoring_api_base_input",
        placeholder="http://127.0.0.1:8000",
    )
    if st.session_state.get("use_api_scoring") and st.session_state.get("scoring_api_base_input", "").strip():
        if st.button("Check API", key="check_scoring_api"):
            try:
                base = st.session_state.scoring_api_base_input.strip().rstrip("/")
                h = httpx.get(f"{base}/health", timeout=15.0)
                h.raise_for_status()
                mi = fetch_model_info(base)
                st.success(f"Ready: {h.json().get('status')} · model `{mi.get('best_model')}`")
            except Exception as exc:
                st.error(f"API check failed: {exc}")

    run_detection = st.button("Run ingestion and anomaly detection", use_container_width=True)


use_api_scoring = bool(st.session_state.get("use_api_scoring"))
api_base_url = str(st.session_state.get("scoring_api_base_input", "")).strip()

if use_api_scoring and api_base_url:
    try:
        _mi = fetch_model_info(api_base_url)
        render_badge("Deployed Model (API)", str(_mi.get("best_model", "?")), tone="blue")
        render_badge("Alert Threshold", f'{float(_mi.get("threshold", 0)):.3f}')
        _active_threshold = float(_mi["threshold"])
    except Exception:
        _bundle = get_artifacts()
        render_badge("Deployed Model", _bundle.best_model_name, tone="blue")
        render_badge("Alert Threshold", f"{_bundle.threshold:.3f}")
        _active_threshold = float(_bundle.threshold)
        st.warning("Scoring API unreachable—badges show local `outputs/` artifacts. Fix URL or start the API.")
else:
    _bundle = get_artifacts()
    render_badge("Deployed Model", _bundle.best_model_name, tone="blue")
    render_badge("Alert Threshold", f"{_bundle.threshold:.3f}")
    _active_threshold = float(_bundle.threshold)

if use_api_scoring:
    st.info(
        "**API mode:** Scores use the API server’s FPMA, inflation, and climate defaults. "
        "Optional **economic / global / climate** uploads here are ignored for scoring (shock & infrastructure still merge onto results)."
    )

reviews = [
    review
    for review in [
        market_review,
        economic_review,
        global_review,
        climate_review,
        shock_review,
        infra_review,
    ]
    if review is not None
]

status_rows = [
    {
        "module": "Market prices",
        "status": "Uploaded" if market_df is not None else "Required",
    },
    {
        "module": "Economic indicators",
        "status": "Uploaded" if economic_df is not None else "Using default KNBS reference",
    },
    {
        "module": "Global prices",
        "status": "Uploaded" if global_df is not None else "Using default FPMA reference",
    },
    {
        "module": "Climate indicators",
        "status": "Uploaded" if climate_df is not None else "Missing - climate features default to zero",
    },
    {
        "module": "Market shocks",
        "status": "Uploaded" if shock_df is not None else "Optional contextual layer not provided",
    },
    {
        "module": "Infrastructure",
        "status": "Uploaded" if infra_df is not None else "Optional contextual layer not provided",
    },
]

top_cols = st.columns([1.3, 1.0])
with top_cols[0]:
    st.subheader("Upload Module Status")
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
with top_cols[1]:
    st.subheader("Validation Summary")
    validation_df = validation_summary_frame(reviews)
    if validation_df.empty:
        st.info("Upload one or more datasets to see schema checks, date validation, and duplicate checks.")
    else:
        st.dataframe(validation_df, use_container_width=True, hide_index=True)

if market_df is None:
    st.info("Upload the market price dataset to activate the ingestion workflow.")
    st.stop()

# Only the market price dataset is required; block run if it failed validation.
if market_review is not None and not market_review.accepted:
    msg = "**Market Price** upload failed validation (required). "
    if market_review.missing_columns:
        msg += f"Missing columns: {', '.join(market_review.missing_columns)}. "
    if market_review.invalid_dates:
        msg += f"Invalid or unparseable dates: {market_review.invalid_dates} row(s). "
    msg += "Fix the schema or date format and try again."
    st.error(msg)
    st.stop()

# Optional uploads: list any that failed so we skip them; don't block run.
optional_reviews = [
    (economic_review, "Economic indicators", economic_df),
    (global_review, "Global prices", global_df),
    (climate_review, "Climate indicators", climate_df),
    (shock_review, "Market shocks", shock_df),
    (infra_review, "Infrastructure", infra_df),
]
failed_optional = [
    name for review, name, _ in optional_reviews
    if review is not None and not review.accepted
]
if failed_optional:
    st.warning(
        f"Optional dataset(s) **{', '.join(failed_optional)}** failed validation and will be skipped. "
        "Run will use default reference data for those. Fix and re-upload if you want them included."
    )

if not run_detection:
    st.info("All accepted uploads are ready. Click `Run ingestion and anomaly detection` to harmonize and score the data.")
    st.stop()

if use_api_scoring and not api_base_url:
    st.error("Turn off **Score via FastAPI** or enter an API base URL (e.g. `http://127.0.0.1:8000`).")
    st.stop()

# Use optional data only when uploaded and accepted.
use_economic = economic_df if (economic_df is not None and economic_review is not None and economic_review.accepted) else None
use_global = global_df if (global_df is not None and global_review is not None and global_review.accepted) else None
use_climate = climate_df if (climate_df is not None and climate_review is not None and climate_review.accepted) else None
use_shock = shock_df if (shock_df is not None and shock_review is not None and shock_review.accepted) else None
use_infra = infra_df if (infra_df is not None and infra_review is not None and infra_review.accepted) else None

try:
    harmonized_market = harmonize_market_price_data(market_df)
    harmonized_economic = harmonize_economic_data(use_economic) if use_economic is not None else None
    harmonized_global = harmonize_global_prices(use_global) if use_global is not None else None
    harmonized_climate = harmonize_climate_data(use_climate) if use_climate is not None else None
    harmonized_shocks = harmonize_shock_data(use_shock) if use_shock is not None else None
    harmonized_infra = harmonize_infrastructure_data(use_infra) if use_infra is not None else None

    if use_api_scoring:
        with st.spinner("Scoring via FastAPI…"):
            scored_df = score_market_via_api(harmonized_market, api_base_url)
            scored_df = merge_scored_with_uploads(
                scored_df,
                shock_df=harmonized_shocks,
                infrastructure_df=harmonized_infra,
            )
            scored_df["record_type"] = "uploaded_api"
    else:
        scored_df = build_uploaded_scored_dataset(
            harmonized_market,
            inflation_df=harmonized_economic,
            fpma_df=harmonized_global,
            climate_tables=harmonized_climate,
            shock_df=harmonized_shocks,
            infrastructure_df=harmonized_infra,
        )
except httpx.HTTPStatusError as exc:
    st.error(f"Scoring API returned HTTP {exc.response.status_code}: {exc.response.text[:500]}")
    st.stop()
except Exception as exc:
    st.error(f"Could not process the uploaded datasets: {exc}")
    st.stop()

scored_df = scored_df[
    scored_df["date"].between(pd.Timestamp(APP_START_DATE), pd.Timestamp(APP_END_DATE))
].copy()

if scored_df.empty:
    st.warning("The uploaded datasets produced no scored records in the 2020 to 2040 window.")
    st.stop()

st.divider()
st.write("### 📊 Forensic Scoring Results")
summary_cols = st.columns(4)

with summary_cols[0]:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Scored Records</div>
            <div class="kpi-value">{len(scored_df):,}</div>
            <div class="kpi-trend">📄 File Audit</div>
        </div>
    """, unsafe_allow_html=True)

with summary_cols[1]:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Detected Anomalies</div>
            <div class="kpi-value">{int(scored_df['pred_anomaly'].sum()):,}</div>
            <div class="kpi-trend trend-down">🚨 Critical Flag</div>
        </div>
    """, unsafe_allow_html=True)

with summary_cols[2]:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Avg Anomaly Score</div>
            <div class="kpi-value">{float(scored_df['risk_score'].mean()):.3f}</div>
            <div class="kpi-trend">🎯 Precision Score</div>
        </div>
    """, unsafe_allow_html=True)

with summary_cols[3]:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Active Commodities</div>
            <div class="kpi-value">{scored_df['commodity'].nunique():,}</div>
            <div class="kpi-trend">📦 Varieties</div>
        </div>
    """, unsafe_allow_html=True)

st.subheader("Uploaded Data Trend View")
plotly_chart_interactive(make_price_trend_chart(scored_df))

st.subheader("Generated Alerts")
_watch_alerts = st.checkbox(
    "Include Medium/High severity rows (full commodity list)",
    value=True,
    key="anomaly_page_alerts_watchlist",
)
alerts = make_alerts_table(scored_df, include_elevated=_watch_alerts)
if "shock_event" in scored_df.columns:
    shock_view = scored_df[
        ["date", "commodity", "COUNTY", "shock_event", "shock_severity"]
    ].drop_duplicates()
    shock_view["date"] = pd.to_datetime(shock_view["date"]).dt.strftime("%Y-%m-%d")
    alerts = alerts.merge(
        shock_view,
        left_on=["date", "commodity", "county"],
        right_on=["date", "commodity", "COUNTY"],
        how="left",
    ).drop(columns=["COUNTY"], errors="ignore")
st.caption(f"**{len(alerts):,}** rows · by commodity — scroll vertically in the table.")
if alerts.empty:
    st.info("No alert rows. Try enabling the watchlist above or widening filters.")
else:
    st.dataframe(alerts, use_container_width=True, hide_index=True, height=520)

date_min_str = scored_df["date"].min().strftime("%b %Y") if not scored_df.empty else ""
date_max_str = scored_df["date"].max().strftime("%b %Y") if not scored_df.empty else ""
date_range_str = f"{date_min_str} – {date_max_str}" if date_min_str else ""
threshold_str = f"> {_active_threshold:.3f}"
sev_col1, sev_col2 = st.columns([1.2, 0.8])
with sev_col1:
    plotly_chart_interactive(
        make_severity_bar_chart(scored_df, date_range_str=date_range_str, threshold_str=threshold_str),
    )
with sev_col2:
    plotly_chart_interactive(make_severity_donut(scored_df, date_range_str=date_range_str))
plotly_chart_interactive(
    make_alerts_over_time_line(scored_df, date_range_str=date_range_str),
)
plotly_chart_interactive(make_commodity_anomaly_trend(scored_df))
plotly_chart_interactive(make_county_anomaly_heatmap(scored_df))

with st.expander("Harmonized data notes"):
    st.markdown(
        """
- Market prices are the required scoring dataset.
- Economic indicators, global prices, and climate uploads are folded into the feature-building stage when provided.
- Shock and infrastructure uploads are merged back onto the scored output as contextual layers for review and export.
"""
    )

export_cols = [
    "COUNTY",
    "market",
    "commodity",
    "date",
    "price_real",
    "expected_price",
    "prob_anomaly",
    "pred_anomaly",
    "risk_score",
    "severity",
    "shock_event",
    "shock_severity",
    "road_density",
    "distance_nairobi",
    "trade_corridor",
]
export_df = scored_df[[col for col in export_cols if col in scored_df.columns]].copy()
export_df["date"] = pd.to_datetime(export_df["date"]).dt.strftime("%Y-%m-%d")
st.download_button(
    "Download scored alerts as CSV",
    export_df.to_csv(index=False).encode("utf-8"),
    file_name="anomaly_alerts.csv",
    mime="text/csv",
)

