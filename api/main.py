"""
FastAPI application entry point — production-grade with:
  • Dual-model weighted ensemble (Logistic Regression 60% + XGBoost 40%)
  • Data router for React frontend (/v1/data/*)
  • Scoring endpoints (/v1/score, /v1/score/csv)
  • /v1/models — ensemble metadata
  • CORS, graceful startup/shutdown via lifespan
  • Firebase Auth JWT verification (per-route, via FastAPI Depends)
  • Per-user daily quota enforcement backed by SQLAlchemy/SQLite
  • Admin router (/v1/admin/*) for usage stats and user management
  • X-Request-ID response header on every response

Environment variables:
  ENSEMBLE_LR_WEIGHT       float 0–1, default 0.6
  ENSEMBLE_STRATEGY        "weighted" | "soft_vote" | "hard_vote"  (future)
  CORS_ORIGINS             comma-separated origins, default "*"
  API_MAX_SCORE_ROWS       int, default 50000
  FIREBASE_PROJECT_ID      Firebase project ID (required for auth)
  FIREBASE_CREDENTIALS_JSON  Service-account JSON string (optional)
  GOOGLE_APPLICATION_CREDENTIALS  Path to service-account file (optional)
  DATABASE_URL             SQLAlchemy URL for quota DB, default sqlite:////app/data/usage.db
  QUOTA_FREE_DAILY         Daily cap for free plan, default 100
  QUOTA_PRO_DAILY          Daily cap for pro plan, default 5000
  QUOTA_ENTERPRISE_DAILY   Daily cap for enterprise plan, default 999999
"""
from __future__ import annotations

import io
import os
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import ModelInfoResponse, ScoreRequest, ScoreResponse
from api.scoring import records_to_dataframe, score_wfp_dataframe, scored_to_json_rows
from api.data import init_data_cache, router as data_router
from src.data_loader import REQUIRED_WFP_COLUMNS, load_feature_names, load_fpma_data, load_inflation_data
from src.inference import (
    ArtifactBundle,
    EnsembleBundle,
    load_artifacts,
    load_ensemble_artifacts,
    score_ensemble,
)

# Auth + quota — Firebase Admin SDK required
# firebase-admin>=6.0.0 required — add to requirements.txt
from api.auth.dependencies import UserContext, get_current_user
from api.auth import require_admin
from api.auth import quota
from api.routers.admin import router as admin_router


# ---------------------------------------------------------------------------
# App-level state
# ---------------------------------------------------------------------------

def _max_rows() -> int:
    return int(os.environ.get("API_MAX_SCORE_ROWS", "50000"))


class AppState:
    # Ensemble (primary)
    ensemble: EnsembleBundle | None = None
    # Single model fallback (kept for backward-compat with older scoring client)
    bundle: ArtifactBundle | None = None
    # Shared reference data
    fpma: pd.DataFrame | None = None
    inflation: pd.DataFrame | None = None
    feature_names: list[str] | None = None
    startup_error: str | None = None


state = AppState()


# ---------------------------------------------------------------------------
# Lifespan: load all models + data on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Load both models
        state.ensemble = load_ensemble_artifacts()
        state.bundle = load_artifacts()

        # Shared reference data for scoring endpoints
        state.fpma = load_fpma_data()
        state.inflation = load_inflation_data()
        state.feature_names = load_feature_names()

        # Pre-build dashboard data cache for React frontend
        init_data_cache(
            ensemble_bundle=state.ensemble,
            single_bundle=state.bundle,
        )

    except Exception as e:  # noqa: BLE001
        state.startup_error = str(e)
        state.ensemble = None
        state.bundle = None

    yield


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Food Price Anomaly API",
    description=(
        "Production REST API for the Market Price Pulse AI platform. "
        "Serves a weighted LR + XGBoost ensemble anomaly scorer and "
        "pre-computed dashboard data for the React frontend."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Prometheus metrics — exposes /metrics for Prometheus scraping
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, include_in_schema=False)
except ImportError:
    pass  # prometheus-fastapi-instrumentator not installed; skip silently

# Mount data router
app.include_router(data_router)

# Mount admin router (all routes require admin Firebase custom claim)
app.include_router(admin_router)
# Mount payments router
from api.payments import router as payments_router
app.include_router(payments_router, prefix="/payments")

# CORS
_origins_raw = os.environ.get("CORS_ORIGINS", "*").strip()
_cors = ["*"] if _origins_raw == "*" else [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=_origins_raw != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# X-Request-ID middleware
# Injects a unique request ID into every response for tracing / log correlation.
# Auth is intentionally handled at the dependency level (FastAPI Depends) rather
# than as global middleware so that public routes (/health, /docs, /openapi.json,
# /redoc, /) remain unauthenticated and the OpenAPI UI stays fully functional.
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_request_id_header(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Dependency guards
# ---------------------------------------------------------------------------

def require_ready() -> None:
    if state.startup_error:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service misconfigured", "message": state.startup_error},
        )
    if state.fpma is None or state.inflation is None or not state.feature_names:
        raise HTTPException(status_code=503, detail="Scoring engine not ready")
    if state.ensemble is None and state.bundle is None:
        raise HTTPException(status_code=503, detail="No model artifacts loaded")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health() -> dict[str, Any]:
    ensemble_ok = state.ensemble is not None and state.ensemble.both_loaded
    fallback_ok = state.bundle is not None and state.bundle.model is not None
    ready = (
        state.startup_error is None
        and state.fpma is not None
        and state.inflation is not None
        and bool(state.feature_names)
        and (state.ensemble is not None or state.bundle is not None)
    )
    return {
        "status": "healthy" if ready else "degraded",
        "ensemble_loaded": ensemble_ok,
        "fallback_model_loaded": fallback_ok,
        "ready": ready,
        "error": state.startup_error,
    }


# ---------------------------------------------------------------------------
# Model info (single model — backward compat)
# ---------------------------------------------------------------------------

@app.get("/v1/model", response_model=ModelInfoResponse, tags=["inference"])
def model_info(
    _: Annotated[None, Depends(require_ready)],
    user: Annotated[UserContext, Depends(get_current_user)],
) -> ModelInfoResponse:
    b = state.bundle
    e = state.ensemble
    if b is None and e is None:
        raise HTTPException(status_code=503, detail="No model loaded")

    # Prefer ensemble metadata
    if e is not None:
        return ModelInfoResponse(
            best_model=e.lr_meta.get("name", "Logistic Regression"),
            threshold=float(e.threshold),
            mode="ensemble_weighted" if e.both_loaded else e.strategy,
            needs_scaling=bool(e.lr_meta.get("needs_scaling", False)),
            n_features=len(e.feature_names),
            warning=e.warning,
        )
    assert b is not None
    return ModelInfoResponse(
        best_model=b.best_model_name,
        threshold=float(b.threshold),
        mode="trained_model" if b.model is not None else "rule_based_fallback",
        needs_scaling=b.needs_scaling,
        n_features=len(b.feature_names),
        warning=b.warning,
    )


# ---------------------------------------------------------------------------
# Ensemble metadata (new)
# ---------------------------------------------------------------------------

@app.get("/v1/models", tags=["inference"])
def ensemble_info(
    user: Annotated[UserContext, Depends(get_current_user)],
) -> dict[str, Any]:
    """Returns full metadata for both models in the weighted ensemble."""
    e = state.ensemble
    b = state.bundle
    if e is None and b is None:
        raise HTTPException(status_code=503, detail="No models loaded")

    if e is not None:
        return {
            "ensemble": {
                "strategy": e.strategy,
                "weights": {"lr": e.lr_weight, "xgb": e.xgb_weight},
                "threshold": e.threshold,
                "lr": {
                    **e.lr_meta,
                    "loaded": e.lr_model is not None,
                },
                "xgb": {
                    **e.xgb_meta,
                    "loaded": e.xgb_model is not None,
                },
                "both_loaded": e.both_loaded,
                "warning": e.warning,
            },
            "active_model": "ensemble" if e.both_loaded else ("lr_only" if e.lr_model else "xgb_only"),
        }

    # Fallback: single model
    assert b is not None
    return {
        "ensemble": None,
        "active_model": b.best_model_name,
        "single_model": {
            "name": b.best_model_name,
            "threshold": b.threshold,
            "mode": "trained_model" if b.model is not None else "rule_based_fallback",
        },
    }


# ---------------------------------------------------------------------------
# Score (JSON body)
# ---------------------------------------------------------------------------

@app.post("/v1/score", response_model=ScoreResponse, tags=["inference"])
def score_json(
    body: ScoreRequest,
    _: Annotated[None, Depends(require_ready)],
    user: Annotated[UserContext, Depends(get_current_user)],
) -> ScoreResponse:
    # Enforce per-user daily quota before doing any work
    quota.check_and_increment_quota(user.uid, user.plan, "/v1/score")

    max_r = _max_rows()
    if len(body.records) > max_r:
        raise HTTPException(
            status_code=413,
            detail=f"Too many rows ({len(body.records)}); max is {max_r}.",
        )
    try:
        df = records_to_dataframe(body.records)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    fpma, inflation, fn = state.fpma, state.inflation, state.feature_names
    assert fpma is not None and inflation is not None and fn is not None

    # Use ensemble if available
    if state.ensemble is not None:
        from api.scoring import score_wfp_dataframe_ensemble
        scored = score_wfp_dataframe_ensemble(
            df, ensemble=state.ensemble, fpma=fpma, inflation=inflation, feature_names=fn
        )
    else:
        assert state.bundle is not None
        scored = score_wfp_dataframe(df, bundle=state.bundle, fpma=fpma, inflation=inflation, feature_names=fn)

    results = scored_to_json_rows(scored)
    n_anom = int(scored["pred_anomaly"].sum()) if not scored.empty and "pred_anomaly" in scored.columns else 0
    summary: dict[str, Any] = {
        "anomaly_count": n_anom,
        "avg_prob": float(scored["prob_anomaly"].mean()) if not scored.empty and scored["prob_anomaly"].notna().any() else None,
        "ensemble_strategy": state.ensemble.strategy if state.ensemble else "single_model",
        "models_used": (
            [n for n, m in [("LogisticRegression", state.ensemble.lr_model), ("XGBoost", state.ensemble.xgb_model)] if m is not None]
            if state.ensemble else [state.bundle.best_model_name if state.bundle else "Unknown"]
        ),
    }
    return ScoreResponse(n_input_rows=len(df), n_scored_rows=len(results), results=results, summary=summary)


# ---------------------------------------------------------------------------
# Score (CSV upload)
# ---------------------------------------------------------------------------

@app.post("/v1/score/csv", response_model=ScoreResponse, tags=["inference"])
async def score_csv(
    file: Annotated[UploadFile, File(description="CSV with WFP columns")],
    _: Annotated[None, Depends(require_ready)],
    user: Annotated[UserContext, Depends(get_current_user)],
) -> ScoreResponse:
    # Enforce per-user daily quota before doing any work
    quota.check_and_increment_quota(user.uid, user.plan, "/v1/score/csv")

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}") from e

    missing = [c for c in REQUIRED_WFP_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    max_r = _max_rows()
    if len(df) > max_r:
        raise HTTPException(status_code=413, detail=f"Too many rows; max is {max_r}")

    fpma, inflation, fn = state.fpma, state.inflation, state.feature_names
    assert fpma is not None and inflation is not None and fn is not None

    if state.ensemble is not None:
        from api.scoring import score_wfp_dataframe_ensemble
        scored = score_wfp_dataframe_ensemble(
            df, ensemble=state.ensemble, fpma=fpma, inflation=inflation, feature_names=fn
        )
    else:
        assert state.bundle is not None
        scored = score_wfp_dataframe(df, bundle=state.bundle, fpma=fpma, inflation=inflation, feature_names=fn)

    results = scored_to_json_rows(scored)
    n_anom = int(scored["pred_anomaly"].sum()) if not scored.empty and "pred_anomaly" in scored.columns else 0
    summary: dict[str, Any] = {
        "anomaly_count": n_anom,
        "avg_prob": float(scored["prob_anomaly"].mean()) if not scored.empty and scored["prob_anomaly"].notna().any() else None,
        "ensemble_strategy": state.ensemble.strategy if state.ensemble else "single_model",
        "models_used": (
            [n for n, m in [("LogisticRegression", state.ensemble.lr_model), ("XGBoost", state.ensemble.xgb_model)] if m is not None]
            if state.ensemble else [state.bundle.best_model_name if state.bundle else "Unknown"]
        ),
    }
    return ScoreResponse(n_input_rows=len(df), n_scored_rows=len(results), results=results, summary=summary)


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "service": "food-price-anomaly-api",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "models": "/v1/models",
    }
