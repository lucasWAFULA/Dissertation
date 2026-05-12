"""Call the FastAPI scoring service from Streamlit or other clients."""

from __future__ import annotations

import math
import os
from typing import Any

import httpx
import numpy as np
import pandas as pd

from src.data_loader import REQUIRED_WFP_COLUMNS


DEFAULT_CHUNK_ROWS = 45_000
DEFAULT_TIMEOUT_S = 600.0


def default_scoring_api_base() -> str:
    return os.environ.get("STREAMLIT_SCORING_API_URL", "").strip()


def harmonized_market_to_json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """WFP-shaped rows suitable for POST /v1/score."""
    if df.empty:
        return []
    d = df[REQUIRED_WFP_COLUMNS].copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"])
    records: list[dict[str, Any]] = []
    for _, row in d.iterrows():
        rec: dict[str, Any] = {}
        for c in REQUIRED_WFP_COLUMNS:
            v = row[c]
            if c == "date":
                rec[c] = pd.Timestamp(v).strftime("%Y-%m-%d")
            elif isinstance(v, (np.floating, float)) and (math.isnan(v) or math.isinf(v)):
                rec[c] = None
            elif pd.isna(v):
                rec[c] = None
            elif isinstance(v, (np.integer, np.int64, np.int32)):
                rec[c] = int(v)
            elif isinstance(v, (np.floating, float)):
                rec[c] = float(v)
            else:
                rec[c] = str(v) if v is not None else None
        records.append(rec)
    return records


def api_results_to_scored_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame()
    scored = pd.DataFrame(results)
    scored["date"] = pd.to_datetime(scored["date"], errors="coerce")
    if "pred_anomaly" in scored.columns:
        scored["pred_anomaly"] = pd.to_numeric(scored["pred_anomaly"], errors="coerce").fillna(0).astype(int)
    if "severity" in scored.columns:
        scored["severity"] = scored["severity"].astype(str)
    if "expected_price" not in scored.columns or scored["expected_price"].isna().all():
        scored["expected_price"] = scored.get("price_real", np.nan)
    return scored


def score_market_via_api(
    harmonized_market: pd.DataFrame,
    base_url: str,
    *,
    chunk_rows: int = DEFAULT_CHUNK_ROWS,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> pd.DataFrame:
    """
    POST harmonized WFP rows to /v1/score in chunks. Returns the same shape
    as the API results (dashboard-ready columns).
    """
    base = base_url.rstrip("/")
    if not base:
        raise ValueError("Scoring API base URL is empty")
    all_results: list[dict[str, Any]] = []
    n = len(harmonized_market)
    if n == 0:
        return pd.DataFrame()

    with httpx.Client(timeout=timeout) as client:
        for start in range(0, n, chunk_rows):
            chunk = harmonized_market.iloc[start : start + chunk_rows]
            payload = {"records": harmonized_market_to_json_records(chunk)}
            resp = client.post(f"{base}/v1/score", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "results" not in data:
                raise ValueError("API response missing 'results'")
            all_results.extend(data["results"])

    return api_results_to_scored_dataframe(all_results)


def fetch_model_info(base_url: str, timeout: float = 15.0) -> dict[str, Any]:
    base = base_url.rstrip("/")
    r = httpx.get(f"{base}/v1/model", timeout=timeout)
    r.raise_for_status()
    return r.json()


def check_api_health(base_url: str, timeout: float = 10.0) -> dict[str, Any]:
    base = base_url.rstrip("/")
    r = httpx.get(f"{base}/health", timeout=timeout)
    r.raise_for_status()
    return r.json()
