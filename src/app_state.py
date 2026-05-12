from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from .data_loader import (
    REQUIRED_WFP_COLUMNS,
    load_best_model_meta,
    load_feature_names,
    load_fpma_data,
    load_inflation_data,
    load_wfp_data,
    standardize_wfp_data,
)
from .inference import ArtifactBundle, format_artifact_status, load_artifacts, score_dataset
from .preprocessing import build_feature_dataset, summarize_pipeline_output
from .visuals import enrich_dashboard_frame

APP_START_DATE = date(2020, 1, 1)
APP_END_DATE = date(2040, 12, 1)


@st.cache_resource(show_spinner=False)
def get_artifacts() -> ArtifactBundle:
    return load_artifacts()


@st.cache_data(show_spinner=True)
def build_dashboard_dataset() -> pd.DataFrame:
    wfp = load_wfp_data()
    fpma = load_fpma_data()
    inflation = load_inflation_data()
    feature_names = load_feature_names()
    feature_df = build_feature_dataset(
        wfp=wfp,
        fpma=fpma,
        inflation=inflation,
        feature_names=feature_names,
        climate_tables=None,
    )
    bundle = get_artifacts()
    scored = score_dataset(feature_df, bundle)
    enriched = enrich_dashboard_frame(scored)
    enriched["record_type"] = "historical"
    return enriched


@st.cache_data(show_spinner=False)
def load_raw_wfp_reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_wfp = load_wfp_data()
    county_reference = (
        raw_wfp.groupby("county", as_index=False)
        .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        .rename(columns={"county": "COUNTY"})
    )
    return raw_wfp, county_reference


def _months_to_target_end(last_date: pd.Timestamp) -> int:
    target = pd.Timestamp(APP_END_DATE)
    return max(0, (target.year - last_date.year) * 12 + (target.month - last_date.month))


@st.cache_data(show_spinner=True)
def build_future_outlook_dataset() -> pd.DataFrame:
    history_df = build_dashboard_dataset().sort_values(["COUNTY", "commodity", "date"]).copy()
    bundle = get_artifacts()
    future_rows: list[dict] = []

    if history_df.empty:
        return pd.DataFrame()

    horizon_months = _months_to_target_end(pd.Timestamp(history_df["date"].max()))
    if horizon_months <= 0:
        return pd.DataFrame()

    for (_, _), group in history_df.groupby(["COUNTY", "commodity"], sort=False):
        group = group.tail(12).copy()
        if len(group) < 3:
            continue

        latest = group.iloc[-1]
        price_history = group["price_real"].tail(3).astype(float).tolist()
        growth_history = (
            group["growth_rate"]
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
            .tail(6)
            .astype(float)
            .tolist()
        )
        if not growth_history:
            growth_history = [0.0]

        for step in range(1, horizon_months + 1):
            prev_price = float(price_history[-1])
            mean_growth = float(np.nanmean(growth_history[-6:])) if growth_history else 0.0
            mean_growth = float(np.clip(mean_growth, -15.0, 15.0))
            projected_price = max(prev_price * (1 + mean_growth / 100), 0.01)
            expected_price = float(np.mean(price_history[-3:]))
            growth_rate = ((projected_price - prev_price) / prev_price * 100) if prev_price else 0.0
            rolling_vol = float(np.std(growth_history[-6:], ddof=0)) if len(growth_history) >= 2 else 0.0

            future_date = (
                pd.Timestamp(latest["date"]) + pd.DateOffset(months=step)
            ).to_period("M").to_timestamp()

            row = latest.to_dict()
            row.update(
                {
                    "date": future_date,
                    "year": future_date.year,
                    "month": future_date.month,
                    "price_real": projected_price,
                    "price_nominal": projected_price * (float(row.get("CPI_index", 100.0)) / 100.0),
                    "growth_rate": growth_rate,
                    "rolling_vol": rolling_vol,
                    "price_lag1": float(price_history[-1]),
                    "price_lag2": float(price_history[-2]),
                    "price_lag3": float(price_history[-3]),
                    "price_roll3": expected_price,
                    "price_anomaly": 0,
                    "prediction_source": "forward_projection",
                    "record_type": "forecast",
                }
            )
            future_rows.append(row)

            price_history.append(projected_price)
            price_history = price_history[-3:]
            growth_history.append(growth_rate)
            growth_history = growth_history[-6:]

    if not future_rows:
        return pd.DataFrame()

    future_df = pd.DataFrame(future_rows)
    future_df = score_dataset(future_df, bundle)
    future_df = enrich_dashboard_frame(future_df)
    future_df["record_type"] = "forecast"
    return future_df


from .database import load_prices_from_db

@st.cache_data(show_spinner=False)
def load_live_data_from_db() -> pd.DataFrame:
    """Load live ingestion records from the SQL database."""
    try:
        live_df = load_prices_from_db(limit=5000)
        if not live_df.empty:
            live_df["record_type"] = "live"
            live_df["date"] = pd.to_datetime(live_df["date"])
            # Rename for consistency if needed
            if "county" in live_df.columns:
                live_df = live_df.rename(columns={"county": "COUNTY"})
            return live_df
        return pd.DataFrame()
    except Exception as e:
        st.sidebar.warning(f"Database connection offline: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=True)
def build_combined_dashboard_dataset() -> pd.DataFrame:
    dashboard_df = build_dashboard_dataset()
    future_df = build_future_outlook_dataset()
    live_df = load_live_data_from_db()
    
    parts = [dashboard_df]
    if not future_df.empty:
        parts.append(future_df)
    if not live_df.empty:
        parts.append(live_df)
        
    return pd.concat(parts, ignore_index=True)


def get_app_context() -> dict[str, object]:
    bundle = get_artifacts()
    dashboard_df = build_dashboard_dataset()
    combined_df = build_combined_dashboard_dataset()
    raw_wfp_df, county_reference = load_raw_wfp_reference()
    pipeline_summary = summarize_pipeline_output(dashboard_df)
    artifact_status = format_artifact_status(bundle)
    deployed_model_meta = load_best_model_meta()

    return {
        "bundle": bundle,
        "dashboard_df": dashboard_df,
        "combined_df": combined_df,
        "raw_wfp_df": raw_wfp_df,
        "county_reference": county_reference,
        "pipeline_summary": pipeline_summary,
        "artifact_status": artifact_status,
        "deployed_model_meta": deployed_model_meta,
    }


def _merge_uploaded_context(
    scored: pd.DataFrame,
    shock_df: pd.DataFrame | None = None,
    infrastructure_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    enriched = scored.copy()
    if shock_df is not None and not shock_df.empty:
        shock_view = shock_df.rename(
            columns={"event_type": "shock_event", "severity": "shock_severity"}
        ).copy()
        shock_view["date"] = pd.to_datetime(shock_view["date"]).dt.to_period("M").dt.to_timestamp()
        enriched["date"] = pd.to_datetime(enriched["date"]).dt.to_period("M").dt.to_timestamp()
        enriched = enriched.merge(
            shock_view[["date", "COUNTY", "shock_event", "shock_severity"]],
            on=["date", "COUNTY"],
            how="left",
        )

    if infrastructure_df is not None and not infrastructure_df.empty:
        infra_view = infrastructure_df.copy()
        infra_view["market"] = infra_view["market"].astype(str)
        if "market" in enriched.columns:
            enriched["market"] = enriched["market"].astype(str)
            enriched = enriched.merge(infra_view, on="market", how="left")

    return enriched


def merge_scored_with_uploads(
    scored: pd.DataFrame,
    shock_df: pd.DataFrame | None = None,
    infrastructure_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Attach shock / infrastructure context to a scored frame (local or API)."""
    return _merge_uploaded_context(scored, shock_df=shock_df, infrastructure_df=infrastructure_df)


def build_uploaded_scored_dataset(
    upload_df: pd.DataFrame,
    inflation_df: pd.DataFrame | None = None,
    fpma_df: pd.DataFrame | None = None,
    climate_tables: dict[str, pd.DataFrame] | None = None,
    shock_df: pd.DataFrame | None = None,
    infrastructure_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    standardized = standardize_wfp_data(upload_df)
    fpma = fpma_df.copy() if fpma_df is not None else load_fpma_data()
    inflation = inflation_df.copy() if inflation_df is not None else load_inflation_data()
    feature_names = load_feature_names()
    feature_df = build_feature_dataset(
        wfp=standardized,
        fpma=fpma,
        inflation=inflation,
        feature_names=feature_names,
        climate_tables=climate_tables,
    )
    bundle = get_artifacts()
    scored = score_dataset(feature_df, bundle)
    enriched = enrich_dashboard_frame(scored)
    enriched = _merge_uploaded_context(
        enriched,
        shock_df=shock_df,
        infrastructure_df=infrastructure_df,
    )
    enriched["record_type"] = "uploaded"
    return enriched

