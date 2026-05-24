"""
Inference engine: single-model artifact loading and dual-model (LR + XGBoost)
weighted ensemble scoring.

Ensemble weights are controlled by the ENSEMBLE_LR_WEIGHT env var (0–1 float).
Default: 0.6 (LR) / 0.4 (XGB) — because Logistic Regression is the declared
best model (F1=0.841, AUC=0.918).
"""
from __future__ import annotations

import os
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

# ---------------------------------------------------------------------------
# XGBoost artifact name (separate from the "best model" slot)
# ---------------------------------------------------------------------------
XGB_CANDIDATES = [
    "model_xgb_anomaly.joblib",
    "model_xgb_anomaly.pkl",
    "xgboost_model.joblib",
    "xgboost_model.pkl",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

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


@dataclass
class EnsembleBundle:
    """Holds both the Logistic Regression and XGBoost models for weighted voting."""
    lr_model: Any | None
    xgb_model: Any | None
    scaler: Any | None                # Used by LR (needs_scaling=True)
    threshold: float                  # Ensemble threshold
    lr_weight: float                  # Weight for LR (default 0.6)
    xgb_weight: float                 # Weight for XGB (default 0.4)
    feature_names: list[str]
    lr_meta: dict[str, Any]
    xgb_meta: dict[str, Any]
    strategy: str = "weighted"        # "weighted" | "soft_vote" | "hard_vote"
    warning: str | None = None

    @property
    def both_loaded(self) -> bool:
        return self.lr_model is not None and self.xgb_model is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_load_joblib(path: Path | None) -> Any | None:
    if path is None or not path.exists():
        return None
    return joblib.load(path)


def _find_xgb_artifact(directory: Path) -> Path | None:
    for name in XGB_CANDIDATES:
        p = directory / name
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Single-model loader (original, unchanged API)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Ensemble loader
# ---------------------------------------------------------------------------

def load_ensemble_artifacts(directory: Path = OUTPUTS_DIR) -> EnsembleBundle:
    """
    Load the LR (best_model.joblib) and XGB (model_xgb_anomaly.joblib) models
    alongside shared metadata for weighted ensemble scoring.

    Weights are read from env vars:
      ENSEMBLE_LR_WEIGHT  (float 0–1, default 0.6)
    """
    lr_weight = float(os.environ.get("ENSEMBLE_LR_WEIGHT", "0.6"))
    lr_weight = max(0.0, min(1.0, lr_weight))
    xgb_weight = round(1.0 - lr_weight, 6)

    meta = load_best_model_meta(directory)
    feature_names = load_feature_names(directory)
    thresholds = load_optimal_thresholds(directory)

    best_model_name = meta.get("best_model", "Logistic Regression")
    threshold = float(meta.get("optimal_threshold", thresholds.get(best_model_name, 0.5)))

    # Try best_threshold.joblib first
    paths = resolve_artifact_paths(directory)
    threshold_artifact = _safe_load_joblib(paths.get("threshold"))
    if threshold_artifact is not None:
        try:
            threshold = float(threshold_artifact)
        except (TypeError, ValueError):
            pass

    # Load LR model (best_model slot)
    lr_model = _safe_load_joblib(paths.get("model"))
    scaler = _safe_load_joblib(paths.get("scaler"))

    # Load XGB model (dedicated slot)
    xgb_path = _find_xgb_artifact(directory)
    xgb_model = _safe_load_joblib(xgb_path)

    warnings_list: list[str] = []
    if lr_model is None:
        warnings_list.append("LR model not found in outputs/ — ensemble will use XGB only.")
    if xgb_model is None:
        warnings_list.append("XGB model not found in outputs/ — ensemble will use LR only.")
    if lr_model is None and xgb_model is None:
        warnings_list.append("No model artifacts found; falling back to rule-based scoring.")

    lr_meta = {
        "name": best_model_name,
        "threshold": threshold,
        "needs_scaling": bool(meta.get("needs_scaling", False)),
        "F1": meta.get("F1"),
        "Recall": meta.get("Recall"),
        "AUC": meta.get("AUC"),
    }
    xgb_meta = {
        "name": "XGBoost",
        "path": str(xgb_path) if xgb_path else None,
    }

    return EnsembleBundle(
        lr_model=lr_model,
        xgb_model=xgb_model,
        scaler=scaler,
        threshold=threshold,
        lr_weight=lr_weight,
        xgb_weight=xgb_weight,
        feature_names=feature_names,
        lr_meta=lr_meta,
        xgb_meta=xgb_meta,
        strategy="weighted",
        warning="; ".join(warnings_list) if warnings_list else None,
    )


# ---------------------------------------------------------------------------
# Feature alignment
# ---------------------------------------------------------------------------

def align_feature_matrix(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    aligned = frame.reindex(columns=feature_names, fill_value=0).copy()
    return aligned.fillna(0)


# ---------------------------------------------------------------------------
# Low-level probability predictor
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Single-model scoring (original, unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Ensemble scoring (new)
# ---------------------------------------------------------------------------

def score_ensemble(frame: pd.DataFrame, bundle: EnsembleBundle) -> pd.DataFrame:
    """
    Score each row with the LR and XGB models independently, then combine
    their probabilities using weighted averaging.

    Added columns:
        prob_lr          – Logistic Regression anomaly probability
        prob_xgb         – XGBoost anomaly probability
        prob_ensemble    – Weighted combination
        prob_anomaly     – Alias for prob_ensemble (API compat)
        pred_anomaly     – 1 if prob_ensemble >= threshold
        model_agreement  – True if both models agree on the binary label
        prediction_source – "ensemble" | "lr_only" | "xgb_only" | "rule_based_fallback"
    """
    if frame.empty:
        return frame.copy()

    scored = frame.copy()
    X = align_feature_matrix(scored, bundle.feature_names)

    # --- LR ---
    prob_lr: np.ndarray | None = None
    if bundle.lr_model is not None:
        Xlr = X
        if bundle.lr_meta.get("needs_scaling") and bundle.scaler is not None:
            Xlr = bundle.scaler.transform(X)
        prob_lr = _predict_proba(bundle.lr_model, Xlr)

    # --- XGB ---
    prob_xgb: np.ndarray | None = None
    if bundle.xgb_model is not None:
        prob_xgb = _predict_proba(bundle.xgb_model, X)

    # --- Combine ---
    n = len(scored)
    if prob_lr is not None and prob_xgb is not None:
        prob_ensemble = bundle.lr_weight * prob_lr + bundle.xgb_weight * prob_xgb
        source = "ensemble"
    elif prob_lr is not None:
        prob_ensemble = prob_lr
        prob_xgb = np.full(n, np.nan)
        source = "lr_only"
    elif prob_xgb is not None:
        prob_ensemble = prob_xgb
        prob_lr = np.full(n, np.nan)
        source = "xgb_only"
    else:
        # Fallback to rule-based
        scored["prob_lr"] = np.nan
        scored["prob_xgb"] = np.nan
        scored["prob_ensemble"] = np.nan
        scored["prob_anomaly"] = np.nan
        scored["pred_anomaly"] = scored.get("price_anomaly", 0).fillna(0).astype(int)
        scored["model_agreement"] = True
        scored["prediction_source"] = "rule_based_fallback"
        return scored

    scored["prob_lr"] = prob_lr
    scored["prob_xgb"] = prob_xgb
    scored["prob_ensemble"] = prob_ensemble
    scored["prob_anomaly"] = prob_ensemble   # API compatibility alias
    scored["pred_anomaly"] = (prob_ensemble >= bundle.threshold).astype(int)

    # Agreement: both models produce a binary label and they match
    if prob_lr is not None and prob_xgb is not None and not np.all(np.isnan(prob_lr)) and not np.all(np.isnan(prob_xgb)):
        pred_lr_bin = (prob_lr >= bundle.threshold).astype(int)
        pred_xgb_bin = (prob_xgb >= bundle.threshold).astype(int)
        scored["model_agreement"] = pred_lr_bin == pred_xgb_bin
    else:
        scored["model_agreement"] = True

    scored["prediction_source"] = source
    return scored


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

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
