from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import OUTPUTS_DIR
from .data_loader import (
    load_best_model_meta,
    load_feature_names,
    load_metrics_table,
    load_optimal_thresholds,
    resolve_artifact_paths,
)


@dataclass
class ArtifactBundle:
    model: Any | None
    scaler: Any | None
    threshold: float
    best_model_name: str
    feature_names: list[str]
    needs_scaling: bool
    metrics_table: pd.DataFrame
    paths: dict[str, Path | None]
    warning: str | None = None


def _safe_load_joblib(path: Path | None) -> Any | None:
    if path is None or not path.exists():
        return None
    return joblib.load(path)


def load_artifacts(directory: Path = OUTPUTS_DIR) -> ArtifactBundle:
    meta = load_best_model_meta(directory)
    feature_names = load_feature_names(directory)
    thresholds = load_optimal_thresholds(directory)
    metrics_table = load_metrics_table(directory)
    paths = resolve_artifact_paths(directory)

    best_model_name = meta.get("best_model", "Unknown")
    threshold = float(
        meta.get(
            "optimal_threshold",
            thresholds.get(best_model_name, 0.5),
        )
    )
    needs_scaling = bool(meta.get("needs_scaling", False))

    warning = None
    model = _safe_load_joblib(paths["model"])
    scaler = _safe_load_joblib(paths["scaler"])

    threshold_artifact = _safe_load_joblib(paths["threshold"])
    if threshold_artifact is not None:
        try:
            threshold = float(threshold_artifact)
        except (TypeError, ValueError):
            pass

    if model is None:
        warning = (
            "Serialized model artifact not found in `outputs`. "
            "The dashboard will use notebook-derived anomaly labels until "
            "a supported model file is added."
        )

    if needs_scaling and scaler is None:
        warning = (
            "Model metadata indicates scaling is required, but no scaler artifact "
            "was found. Falling back to notebook-derived anomaly labels."
        )
        model = None

    return ArtifactBundle(
        model=model,
        scaler=scaler,
        threshold=threshold,
        best_model_name=best_model_name,
        feature_names=feature_names,
        needs_scaling=needs_scaling,
        metrics_table=metrics_table,
        paths=paths,
        warning=warning,
    )


def align_feature_matrix(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    aligned = frame.reindex(columns=feature_names, fill_value=0).copy()
    return aligned.fillna(0)


def _predict_proba(model: Any, X: pd.DataFrame | np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        if isinstance(proba, np.ndarray) and proba.ndim == 2:
            return proba[:, 1]
        return np.asarray(proba).reshape(-1)

    if hasattr(model, "decision_function"):
        scores = np.asarray(model.decision_function(X)).reshape(-1)
        return 1 / (1 + np.exp(-scores))

    predictions = np.asarray(model.predict(X)).reshape(-1)
    return predictions.astype(float)


def score_dataset(frame: pd.DataFrame, bundle: ArtifactBundle) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
        
    scored = frame.copy()
    X = align_feature_matrix(scored, bundle.feature_names)

    if bundle.model is None:
        scored["prob_anomaly"] = np.nan
        scored["pred_anomaly"] = scored.get("price_anomaly", 0).fillna(0).astype(int)
        scored["prediction_source"] = "rule_based_fallback"
        return scored

    Xt = X
    if bundle.needs_scaling and bundle.scaler is not None:
        Xt = bundle.scaler.transform(X)

    probabilities = _predict_proba(bundle.model, Xt)
    scored["prob_anomaly"] = probabilities
    scored["pred_anomaly"] = (scored["prob_anomaly"] >= bundle.threshold).astype(int)
    scored["prediction_source"] = "trained_model"
    return scored


def format_artifact_status(bundle: ArtifactBundle) -> dict[str, str]:
    return {
        "best_model": bundle.best_model_name,
        "threshold": f"{bundle.threshold:.3f}",
        "mode": "Model scoring" if bundle.model is not None else "Rule-based fallback",
        "model_path": str(bundle.paths["model"]) if bundle.paths["model"] else "Not found",
    }

def run_batch_inference(frame: pd.DataFrame, bundle: ArtifactBundle) -> pd.DataFrame:
    """Convenience wrapper for scoring a batch of price records."""
    return score_dataset(frame, bundle)

