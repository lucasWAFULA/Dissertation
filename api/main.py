"""
Scalable FastAPI layer for anomaly scoring.

Run locally (project root):
  uvicorn api.main:app --host 0.0.0.0 --port 8000

Production (multiple processes):
  uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

Each worker loads model + reference data in memory (horizontal scale = more replicas).
"""
from __future__ import annotations

import io
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import ModelInfoResponse, ScoreRequest, ScoreResponse
from api.scoring import records_to_dataframe, score_wfp_dataframe, scored_to_json_rows
from src.data_loader import REQUIRED_WFP_COLUMNS, load_feature_names, load_fpma_data, load_inflation_data
from src.inference import ArtifactBundle, load_artifacts


def _max_rows() -> int:
    return int(os.environ.get("API_MAX_SCORE_ROWS", "50000"))


class AppState:
    bundle: ArtifactBundle | None = None
    fpma: pd.DataFrame | None = None
    inflation: pd.DataFrame | None = None
    feature_names: list[str] | None = None
    startup_error: str | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        state.bundle = load_artifacts()
        state.fpma = load_fpma_data()
        state.inflation = load_inflation_data()
        state.feature_names = load_feature_names()
    except Exception as e:  # noqa: BLE001
        state.startup_error = str(e)
        state.bundle = None
    yield


app = FastAPI(
    title="Food Price Anomaly API",
    description="REST API for scoring WFP-style market records with the deployed model.",
    version="1.0.0",
    lifespan=lifespan,
)

_origins = os.environ.get("CORS_ORIGINS", "*").strip()
if _origins == "*":
    _cors = ["*"]
else:
    _cors = [o.strip() for o in _origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=_origins != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_ready() -> None:
    if state.startup_error:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service misconfigured", "message": state.startup_error},
        )
    if state.bundle is None or state.fpma is None or state.inflation is None or not state.feature_names:
        raise HTTPException(status_code=503, detail="Scoring engine not ready")


@app.get("/health")
def health() -> dict[str, Any]:
    ready = bool(
        state.startup_error is None
        and state.bundle is not None
        and state.fpma is not None
        and state.inflation is not None
        and state.feature_names
    )
    return {
        "status": "healthy" if ready else "degraded",
        "model_loaded": state.bundle is not None and state.bundle.model is not None,
        "ready": ready,
        "error": state.startup_error,
    }


@app.get("/v1/model", response_model=ModelInfoResponse)
def model_info(_: Annotated[None, Depends(require_ready)]) -> ModelInfoResponse:
    b = state.bundle
    assert b is not None
    return ModelInfoResponse(
        best_model=b.best_model_name,
        threshold=float(b.threshold),
        mode="trained_model" if b.model is not None else "rule_based_fallback",
        needs_scaling=b.needs_scaling,
        n_features=len(b.feature_names),
        warning=b.warning,
    )


@app.post("/v1/score", response_model=ScoreResponse)
def score_json(
    body: ScoreRequest,
    _: Annotated[None, Depends(require_ready)],
) -> ScoreResponse:
    max_r = _max_rows()
    if len(body.records) > max_r:
        raise HTTPException(
            status_code=413,
            detail=f"Too many rows ({len(body.records)}); max is {max_r}. "
            "Raise API_MAX_SCORE_ROWS or split the batch.",
        )
    try:
        df = records_to_dataframe(body.records)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    b, fpma, inflation, fn = state.bundle, state.fpma, state.inflation, state.feature_names
    assert b is not None and fpma is not None and inflation is not None and fn is not None
    scored = score_wfp_dataframe(df, bundle=b, fpma=fpma, inflation=inflation, feature_names=fn)
    results = scored_to_json_rows(scored)
    n_anom = int(scored["pred_anomaly"].sum()) if not scored.empty and "pred_anomaly" in scored.columns else 0
    summary = {
        "anomaly_count": n_anom,
        "avg_prob": float(scored["prob_anomaly"].mean())
        if not scored.empty and scored["prob_anomaly"].notna().any()
        else None,
    }
    return ScoreResponse(
        n_input_rows=len(df),
        n_scored_rows=len(results),
        results=results,
        summary=summary,
    )


@app.post("/v1/score/csv", response_model=ScoreResponse)
async def score_csv(
    file: Annotated[UploadFile, File(description="CSV with WFP columns")],
    _: Annotated[None, Depends(require_ready)],
) -> ScoreResponse:
    require_ready()
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

    b, fpma, inflation, fn = state.bundle, state.fpma, state.inflation, state.feature_names
    assert b is not None and fpma is not None and inflation is not None and fn is not None
    scored = score_wfp_dataframe(df, bundle=b, fpma=fpma, inflation=inflation, feature_names=fn)
    results = scored_to_json_rows(scored)
    n_anom = int(scored["pred_anomaly"].sum()) if not scored.empty and "pred_anomaly" in scored.columns else 0
    summary = {
        "anomaly_count": n_anom,
        "avg_prob": float(scored["prob_anomaly"].mean())
        if not scored.empty and scored["prob_anomaly"].notna().any()
        else None,
    }
    return ScoreResponse(
        n_input_rows=len(df),
        n_scored_rows=len(results),
        results=results,
        summary=summary,
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "food-price-anomaly-api",
        "docs": "/docs",
        "health": "/health",
    }
