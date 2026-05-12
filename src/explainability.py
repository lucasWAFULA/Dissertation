from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .inference import ArtifactBundle, align_feature_matrix


def _transform_features(frame: pd.DataFrame, bundle: ArtifactBundle) -> pd.DataFrame:
    X = align_feature_matrix(frame, bundle.feature_names)
    if bundle.needs_scaling and bundle.scaler is not None:
        X_scaled = bundle.scaler.transform(X)
        return pd.DataFrame(X_scaled, columns=bundle.feature_names, index=frame.index)
    return X


def _build_explainer(model: Any, background: pd.DataFrame):
    import shap

    if hasattr(model, "coef_"):
        return shap.LinearExplainer(model, background)
    if hasattr(model, "feature_importances_") or hasattr(model, "get_booster"):
        return shap.TreeExplainer(model)
    return shap.Explainer(model, background)


def _normalize_shap_values(values: Any) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim == 3:
        return array[:, :, -1]
    return array


def compute_global_shap_summary(
    frame: pd.DataFrame,
    bundle: ArtifactBundle,
    sample_size: int = 300,
    background_size: int = 100,
) -> tuple[pd.DataFrame | None, str | None]:
    if bundle.model is None:
        return None, "Deployed model artifact is unavailable for SHAP analysis."

    try:
        import shap  # noqa: F401
    except ImportError:
        return None, "SHAP is not installed in the current environment."

    X = _transform_features(frame, bundle)
    if X.empty:
        return None, "No rows available for SHAP analysis."

    sample = X.sample(n=min(sample_size, len(X)), random_state=42) if len(X) > sample_size else X.copy()
    background = sample.sample(n=min(background_size, len(sample)), random_state=42) if len(sample) > background_size else sample

    explainer = _build_explainer(bundle.model, background)
    explanation = explainer(sample)
    shap_values = _normalize_shap_values(explanation.values)
    mean_abs = np.abs(shap_values).mean(axis=0)

    summary = (
        pd.DataFrame({"feature": bundle.feature_names, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    return summary, None


def compute_local_shap_explanation(
    record: pd.Series,
    reference_frame: pd.DataFrame,
    bundle: ArtifactBundle,
    background_size: int = 100,
) -> tuple[pd.DataFrame | None, str | None]:
    if bundle.model is None:
        return None, "Deployed model artifact is unavailable for SHAP analysis."

    try:
        import shap  # noqa: F401
    except ImportError:
        return None, "SHAP is not installed in the current environment."

    X_reference = _transform_features(reference_frame, bundle)
    if X_reference.empty:
        return None, "No reference rows available for SHAP analysis."

    background = (
        X_reference.sample(n=min(background_size, len(X_reference)), random_state=42)
        if len(X_reference) > background_size
        else X_reference
    )
    local_frame = pd.DataFrame([record[bundle.feature_names].to_dict()])
    X_local = _transform_features(local_frame, bundle)

    explainer = _build_explainer(bundle.model, background)
    explanation = explainer(X_local)
    shap_values = _normalize_shap_values(explanation.values)[0]

    local_df = (
        pd.DataFrame(
            {
                "feature": bundle.feature_names,
                "feature_value": [record.get(feature, 0.0) for feature in bundle.feature_names],
                "shap_value": shap_values,
                "abs_shap": np.abs(shap_values),
            }
        )
        .sort_values("abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    return local_df, None

