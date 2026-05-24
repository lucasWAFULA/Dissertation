from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from src.data_loader import REQUIRED_WFP_COLUMNS, standardize_wfp_data
from src.inference import ArtifactBundle, EnsembleBundle, score_dataset, score_ensemble
from src.preprocessing import build_feature_dataset
from src.visuals import enrich_dashboard_frame


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=REQUIRED_WFP_COLUMNS)
    df = pd.DataFrame(records)
    missing = [c for c in REQUIRED_WFP_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df[REQUIRED_WFP_COLUMNS].copy()


def score_wfp_dataframe(
    df: pd.DataFrame,
    *,
    bundle: ArtifactBundle,
    fpma: pd.DataFrame,
    inflation: pd.DataFrame,
    feature_names: list[str],
) -> pd.DataFrame:
    standardized = standardize_wfp_data(df)
    if standardized.empty:
        return pd.DataFrame()
    feature_df = build_feature_dataset(
        wfp=standardized,
        fpma=fpma,
        inflation=inflation,
        feature_names=feature_names,
        climate_tables=None,
    )
    scored = score_dataset(feature_df, bundle)
    return enrich_dashboard_frame(scored)


def score_wfp_dataframe_ensemble(
    df: pd.DataFrame,
    *,
    ensemble: EnsembleBundle,
    fpma: pd.DataFrame,
    inflation: pd.DataFrame,
    feature_names: list[str],
) -> pd.DataFrame:
    """Run the LR + XGB weighted ensemble on WFP-style CSV/JSON rows."""
    standardized = standardize_wfp_data(df)
    if standardized.empty:
        return pd.DataFrame()
    feature_df = build_feature_dataset(
        wfp=standardized,
        fpma=fpma,
        inflation=inflation,
        feature_names=feature_names,
        climate_tables=None,
    )
    scored = score_ensemble(feature_df, ensemble)
    return enrich_dashboard_frame(scored)


def scored_to_json_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    if "severity" in out.columns:
        out["severity"] = out["severity"].astype(str)

    cols = [
        "date",
        "COUNTY",
        "commodity",
        "market",
        "price_real",
        "expected_price",
        "prob_anomaly",
        "prob_lr",
        "prob_xgb",
        "prob_ensemble",
        "model_agreement",
        "pred_anomaly",
        "prediction_source",
        "severity",
        "risk_score",
        "price_spike_pct",
    ]
    present = [c for c in cols if c in out.columns]
    rows = out[present].replace({np.nan: None}).to_dict(orient="records")
    for r in rows:
        for k, v in list(r.items()):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                r[k] = None
            elif isinstance(v, np.bool_):
                r[k] = bool(v)
    return rows
