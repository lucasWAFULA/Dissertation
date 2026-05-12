from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    """WFP-style market price rows (same columns as Streamlit upload)."""

    records: list[dict[str, Any]] = Field(
        ...,
        description="List of dicts with keys: date, admin1, admin2, market, market_id, "
        "latitude, longitude, category, commodity, commodity_id, unit, priceflag, "
        "pricetype, currency, price, usdprice",
    )


class ScoreResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    n_input_rows: int
    n_scored_rows: int
    results: list[dict[str, Any]]
    summary: dict[str, Any]


class ModelInfoResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    best_model: str
    threshold: float
    mode: str
    needs_scaling: bool
    n_features: int
    warning: str | None = None
