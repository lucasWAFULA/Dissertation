"""
FastAPI data router — exposes pre-computed dashboard data to the React frontend.

All endpoints read from the same Python pipeline used by Streamlit (src/app_state.py
logic, minus st.cache decorators). Data is computed once at startup and cached in
module-level state alongside the inference bundle.
"""
from __future__ import annotations

import functools
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.data_loader import (
    load_best_model_meta,
    load_feature_names,
    load_fpma_data,
    load_inflation_data,
    load_wfp_data,
)
from src.database import load_prices_from_db
from src.inference import EnsembleBundle, ArtifactBundle, score_ensemble, score_dataset
from src.preprocessing import build_feature_dataset, summarize_pipeline_output
from src.visuals import enrich_dashboard_frame

router = APIRouter(prefix="/v1/data", tags=["data"])


# ---------------------------------------------------------------------------
# Module-level cache (populated by api/main.py on startup)
# ---------------------------------------------------------------------------

class DataCache:
    dashboard_df: pd.DataFrame | None = None
    raw_wfp_df: pd.DataFrame | None = None
    county_reference: pd.DataFrame | None = None
    pipeline_summary: dict[str, Any] | None = None
    commodities: list[str] = []
    counties: list[str] = []
    error: str | None = None


_cache = DataCache()


def _safe_float(val: Any) -> float | None:
    try:
        f = float(val)
        return None if (f != f) else f   # NaN check
    except (TypeError, ValueError):
        return None


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to JSON-safe list of dicts."""
    records = []
    for row in df.to_dict(orient="records"):
        clean: dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, pd.Timestamp):
                clean[k] = v.strftime("%Y-%m-%d")
            elif isinstance(v, float) and (v != v):  # NaN
                clean[k] = None
            elif isinstance(v, np.integer):
                clean[k] = int(v)
            elif isinstance(v, np.floating):
                clean[k] = None if (float(v) != float(v)) else float(v)
            elif isinstance(v, np.bool_):
                clean[k] = bool(v)
            else:
                clean[k] = v
        records.append(clean)
    return records


# ---------------------------------------------------------------------------
# Startup initializer (called from main.py lifespan)
# ---------------------------------------------------------------------------

def init_data_cache(
    ensemble_bundle: EnsembleBundle | None = None,
    single_bundle: ArtifactBundle | None = None,
) -> None:
    """Build the dashboard DataFrame and populate the module cache."""
    try:
        wfp = load_wfp_data()
        fpma = load_fpma_data()
        inflation = load_inflation_data()
        feature_names = load_feature_names()

        feature_df = build_feature_dataset(
            wfp=wfp,
            fpma=fpma,
            inflation=inflation,
            feature_names=feature_names,
        )

        # Score with ensemble if available, else single model
        if ensemble_bundle is not None:
            scored = score_ensemble(feature_df, ensemble_bundle)
        elif single_bundle is not None:
            scored = score_dataset(feature_df, single_bundle)
        else:
            scored = feature_df.copy()

        enriched = enrich_dashboard_frame(scored)
        enriched["record_type"] = "historical"

        # Try to append live DB records
        try:
            live_df = load_prices_from_db(limit=5000)
            if not live_df.empty:
                live_df["record_type"] = "live"
                live_df["date"] = pd.to_datetime(live_df["date"])
                if "county" in live_df.columns:
                    live_df = live_df.rename(columns={"county": "COUNTY"})
                enriched = pd.concat([enriched, live_df], ignore_index=True)
        except Exception:
            pass

        county_ref = (
            wfp.groupby("county", as_index=False)
            .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
            .rename(columns={"county": "COUNTY"})
        )

        _cache.dashboard_df = enriched
        _cache.raw_wfp_df = wfp
        _cache.county_reference = county_ref
        _cache.pipeline_summary = summarize_pipeline_output(enriched)
        _cache.commodities = sorted(enriched["commodity"].dropna().unique().tolist()) if "commodity" in enriched.columns else []
        _cache.counties = sorted(enriched["COUNTY"].dropna().unique().tolist()) if "COUNTY" in enriched.columns else []
        _cache.error = None

    except Exception as exc:
        _cache.error = str(exc)


def _require_data() -> pd.DataFrame:
    if _cache.error:
        raise HTTPException(status_code=503, detail=f"Data pipeline error: {_cache.error}")
    if _cache.dashboard_df is None:
        raise HTTPException(status_code=503, detail="Data cache not yet initialized.")
    return _cache.dashboard_df


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_dashboard() -> dict[str, Any]:
    """KPIs, commodity/county lists, pipeline summary and model info."""
    df = _require_data()

    # KPIs
    latest_month = df["date"].max() if not df.empty else None
    if latest_month is not None:
        latest_mask = df["date"] == latest_month
        latest_anomalies = int(df.loc[latest_mask, "pred_anomaly"].sum()) if "pred_anomaly" in df.columns else 0
    else:
        latest_anomalies = 0

    growth_col = "growth_rate" if "growth_rate" in df.columns else None
    max_spike = float(df[growth_col].abs().max()) if growth_col and not df.empty else 0.0
    avg_risk = _safe_float(df["risk_score"].mean()) if "risk_score" in df.columns and not df.empty else None

    # Compute Highest Risk Market
    highest_risk_market = None
    if "risk_score" in df.columns and "commodity" in df.columns and "COUNTY" in df.columns and not df.empty:
        risk_sorted = df.dropna(subset=["risk_score", "commodity", "COUNTY"]).sort_values("risk_score", ascending=False)
        if not risk_sorted.empty:
            top_rec = risk_sorted.iloc[0]
            price_real = _safe_float(top_rec.get("price_real"))
            expected_price = _safe_float(top_rec.get("expected_price"))
            deviation = None
            if price_real is not None and expected_price is not None and expected_price > 0:
                deviation = round(((price_real - expected_price) / expected_price) * 100, 1)
            elif growth_col in top_rec:
                deviation = round(float(top_rec[growth_col]) * 100, 1)
            
            highest_risk_market = {
                "commodity": str(top_rec["commodity"]),
                "county": str(top_rec["COUNTY"]),
                "risk_score": round(float(top_rec["risk_score"]), 3),
                "severity": str(top_rec.get("severity", "High")),
                "deviation": deviation
            }

    # Compute Anomaly Trend
    anomalies_trend = None
    if "date" in df.columns and "pred_anomaly" in df.columns and not df.empty:
        try:
            df_temp = df.copy()
            df_temp["month_stamp"] = pd.to_datetime(df_temp["date"]).dt.to_period("M")
            months = sorted(df_temp["month_stamp"].unique())
            if len(months) >= 2:
                latest_m = months[-1]
                prior_m = months[-2]
                
                latest_anoms = int(df_temp.loc[df_temp["month_stamp"] == latest_m, "pred_anomaly"].sum())
                prior_anoms = int(df_temp.loc[df_temp["month_stamp"] == prior_m, "pred_anomaly"].sum())
                
                if prior_anoms > 0:
                    pct_change = round(((latest_anoms - prior_anoms) / prior_anoms) * 100, 1)
                    anomalies_trend = {
                        "direction": "up" if pct_change > 0 else "down" if pct_change < 0 else "neutral",
                        "pct": abs(pct_change),
                        "label": f"{'+' if pct_change > 0 else ''}{pct_change}% vs last month"
                    }
                else:
                    anomalies_trend = {
                        "direction": "up" if latest_anoms > 0 else "neutral",
                        "pct": 100 if latest_anoms > 0 else 0,
                        "label": f"+{latest_anoms} anomalies vs last month" if latest_anoms > 0 else "Stable"
                    }
        except Exception:
            pass

    meta = load_best_model_meta()

    return {
        "kpis": {
            "total_commodities": len(_cache.commodities),
            "latest_month_anomalies": latest_anomalies,
            "highest_price_spike": round(max_spike, 2),
            "avg_risk_score": avg_risk,
            "highest_risk_market": highest_risk_market,
            "anomalies_trend": anomalies_trend,
        },
        "pipeline": _cache.pipeline_summary or {},
        "commodities": _cache.commodities,
        "counties": _cache.counties,
        "model_info": {
            "best_model": meta.get("best_model", "Unknown"),
            "F1": _safe_float(meta.get("F1")),
            "Recall": _safe_float(meta.get("Recall")),
            "AUC": _safe_float(meta.get("AUC")),
        },
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@router.get("/prices")
def get_prices(
    commodity: str | None = Query(None, description="Filter by commodity name"),
    county: str | None = Query(None, description="Filter by county name"),
    from_date: str | None = Query(None, description="ISO date string (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="ISO date string (YYYY-MM-DD)"),
    limit: int = Query(2000, le=10000),
) -> dict[str, Any]:
    """Price trend records for charting."""
    df = _require_data()

    cols_wanted = [
        "date", "commodity", "COUNTY", "price_real", "price_nominal", "expected_price",
        "growth_rate", "rolling_vol", "pred_anomaly", "prob_anomaly",
        "prob_lr", "prob_xgb", "prob_ensemble", "severity", "record_type",
    ]
    available = [c for c in cols_wanted if c in df.columns]
    result = df[available].copy()
    result = result.rename(columns={"COUNTY": "county"})

    if commodity:
        result = result[result["commodity"].str.lower() == commodity.lower()]
    if county:
        result = result[result["county"].str.lower() == county.lower()]
    if from_date:
        result = result[result["date"] >= pd.Timestamp(from_date)]
    if to_date:
        result = result[result["date"] <= pd.Timestamp(to_date)]

    result = result.sort_values("date").tail(limit)
    return {"records": _df_to_records(result), "total": len(result)}


@router.get("/anomalies")
def get_anomalies(
    severity: str | None = Query(None, description="High | Medium | Low"),
    commodity: str | None = Query(None),
    county: str | None = Query(None),
    limit: int = Query(500, le=5000),
) -> dict[str, Any]:
    """Anomaly alert records for the alerts table."""
    df = _require_data()

    if "pred_anomaly" in df.columns:
        result = df[df["pred_anomaly"] == 1].copy()
    else:
        result = df.copy()

    if "severity" in result.columns and severity:
        result = result[result["severity"].str.lower() == severity.lower()]
    if commodity:
        result = result[result["commodity"].str.lower() == commodity.lower()]
    if "COUNTY" in result.columns and county:
        result = result[result["COUNTY"].str.lower() == county.lower()]

    cols_wanted = [
        "date", "commodity", "COUNTY", "market", "price_real", "expected_price",
        "risk_score", "prob_anomaly", "prob_lr", "prob_xgb", "prob_ensemble",
        "pred_anomaly", "severity", "source", "model_agreement", "record_type",
    ]
    available = [c for c in cols_wanted if c in result.columns]
    result = result[available].rename(columns={"COUNTY": "county"})

    if "risk_score" in result.columns:
        result = result.sort_values("risk_score", ascending=False)
    result = result.head(limit)
    return {"records": _df_to_records(result), "total": len(result)}


@router.get("/geo")
def get_geo() -> dict[str, Any]:
    """County-level aggregates for the choropleth map."""
    df = _require_data()

    county_col = "COUNTY" if "COUNTY" in df.columns else "county"
    if county_col not in df.columns:
        return {"counties": []}

    agg: dict[str, Any] = {county_col: df[county_col]}
    if "pred_anomaly" in df.columns:
        agg["anomaly_count"] = df["pred_anomaly"]
    if "risk_score" in df.columns:
        agg["avg_risk_score"] = df["risk_score"]

    geo_df = df[[c for c in [county_col, "pred_anomaly", "risk_score"] if c in df.columns]].copy()
    grouped = geo_df.groupby(county_col, as_index=False).agg(
        anomaly_count=("pred_anomaly", "sum") if "pred_anomaly" in geo_df.columns else (county_col, "count"),
        avg_risk_score=("risk_score", "mean") if "risk_score" in geo_df.columns else (county_col, "count"),
    )

    # Merge lat/lon from county_reference
    if _cache.county_reference is not None:
        grouped = grouped.merge(
            _cache.county_reference.rename(columns={"COUNTY": county_col}),
            on=county_col,
            how="left",
        )

    grouped = grouped.rename(columns={county_col: "COUNTY"})
    return {"counties": _df_to_records(grouped)}


@router.get("/features")
def get_features() -> dict[str, Any]:
    """Feature importance data for the Explainability page."""
    df = _require_data()

    feature_names = load_feature_names()

    # Build a simple variance-based importance proxy if model feature importances unavailable
    importances: list[dict[str, Any]] = []
    for feat in feature_names:
        if feat in df.columns:
            importance = float(df[feat].var()) if not df[feat].isna().all() else 0.0
            importances.append({"feature": feat, "importance": importance})
        else:
            importances.append({"feature": feat, "importance": 0.0})

    # Normalize
    total = sum(i["importance"] for i in importances) or 1.0
    for item in importances:
        item["importance"] = round(item["importance"] / total, 6)

    importances.sort(key=lambda x: x["importance"], reverse=True)

    meta = load_best_model_meta()
    return {
        "feature_importance": importances,
        "model_name": meta.get("best_model", "Unknown"),
        "n_features": len(feature_names),
        "shap_summary": [],   # Placeholder; can be extended with SHAP values
    }


@router.get("/commodities")
def get_commodities() -> dict[str, Any]:
    _require_data()
    return {"commodities": _cache.commodities}


@router.get("/counties")
def get_counties() -> dict[str, Any]:
    _require_data()
    return {"counties": _cache.counties}
