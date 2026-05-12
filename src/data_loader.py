from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .config import (
    BASE_DIR,
    COUNTIES_SHP_PATH,
    DEFAULT_FEATURE_NAMES,
    FPMA_PATH,
    INFLATION_PATH,
    KENYA_ADM0_GEOJSON_PATH,
    KENYA_ADM1_GEOJSON_PATH,
    MODEL_CANDIDATES,
    OUTPUTS_DIR,
    SCALER_CANDIDATES,
    THRESHOLD_CANDIDATES,
    WFP_PATH,
)


REQUIRED_WFP_COLUMNS = [
    "date",
    "admin1",
    "admin2",
    "market",
    "market_id",
    "latitude",
    "longitude",
    "category",
    "commodity",
    "commodity_id",
    "unit",
    "priceflag",
    "pricetype",
    "currency",
    "price",
    "usdprice",
]


def _first_existing(directory: Path, candidates: list[str]) -> Path | None:
    for name in candidates:
        candidate = directory / name
        if candidate.exists():
            return candidate
    return None


def standardize_wfp_data(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_WFP_COLUMNS if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required WFP columns: {missing}")

    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        parsed = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
        fallback_mask = parsed.isna()
        if fallback_mask.any():
            parsed.loc[fallback_mask] = pd.to_datetime(df.loc[fallback_mask, "date"], errors="coerce")
        df["date"] = parsed
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df = df.rename(columns={"admin1": "region", "admin2": "county"})
    return df.sort_values(["county", "commodity", "market", "date"]).reset_index(drop=True)


def load_wfp_data(path: Path = WFP_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    return standardize_wfp_data(df)


def load_fpma_data(path: Path = FPMA_PATH) -> pd.DataFrame:
    fpma = pd.read_csv(path)
    date_col = next(col for col in fpma.columns if col.lower() == "date")
    fpma = fpma.rename(columns={date_col: "Date"})
    # FPMA file dates are month-first (e.g. 12/01/2024 -> Dec 2024), so parse
    # them explicitly and collapse to one monthly row before merging downstream.
    fpma["Date"] = pd.to_datetime(fpma["Date"], format="%m/%d/%Y", errors="coerce")
    fpma = fpma.dropna(subset=["Date"]).copy()
    fpma["Date"] = fpma["Date"].dt.to_period("M").dt.to_timestamp()

    value_columns = [column for column in fpma.columns if column != "Date"]
    fpma[value_columns] = fpma[value_columns].apply(pd.to_numeric, errors="coerce")
    fpma = (
        fpma.groupby("Date", as_index=False)[value_columns]
        .mean()
        .sort_values("Date")
        .reset_index(drop=True)
    )
    return fpma.ffill()


def load_inflation_data(path: Path = INFLATION_PATH) -> pd.DataFrame:
    inf_raw = pd.read_csv(path, header=0)
    inf_raw.columns = ["Year", "Month", "Inflation_pct"] + list(inf_raw.columns[3:])
    inf_raw = inf_raw[["Year", "Month", "Inflation_pct"]].copy()
    inf_raw["Year"] = pd.to_numeric(inf_raw["Year"], errors="coerce").ffill()
    inf_raw["Inflation_pct"] = pd.to_numeric(inf_raw["Inflation_pct"], errors="coerce")
    inf_raw = inf_raw.dropna(subset=["Year", "Inflation_pct"])

    month_map = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "June": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Sept": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    inf_raw["month_num"] = inf_raw["Month"].astype(str).str.strip().map(month_map)
    inf_raw = inf_raw.dropna(subset=["month_num"]).copy()
    inf_raw["date"] = pd.to_datetime(
        inf_raw["Year"].astype(int).astype(str)
        + "-"
        + inf_raw["month_num"].astype(int).astype(str)
        + "-01"
    )

    inflation = inf_raw[["date", "Inflation_pct"]].copy()
    return inflation.sort_values("date").reset_index(drop=True)


def load_best_model_meta(directory: Path = OUTPUTS_DIR) -> dict[str, Any]:
    meta_path = directory / "best_model_meta.json"
    if not meta_path.exists():
        return {}
    with meta_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_feature_names(directory: Path = OUTPUTS_DIR) -> list[str]:
    csv_path = directory / "feature_names.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if "name" in df.columns:
            names = df["name"].dropna().astype(str).tolist()
            if names:
                return names

    joblib_path = directory / "feature_names.joblib"
    if joblib_path.exists():
        names = joblib.load(joblib_path)
        if isinstance(names, (list, tuple)):
            return [str(name) for name in names]

    return DEFAULT_FEATURE_NAMES.copy()


def load_optimal_thresholds(directory: Path = OUTPUTS_DIR) -> dict[str, float]:
    csv_path = directory / "optimal_thresholds.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if {"model", "optimal_threshold"}.issubset(df.columns):
            return {
                str(row["model"]): float(row["optimal_threshold"])
                for _, row in df.iterrows()
            }

    joblib_path = directory / "optimal_thresholds.joblib"
    if joblib_path.exists():
        loaded = joblib.load(joblib_path)
        if isinstance(loaded, dict):
            return {str(key): float(value) for key, value in loaded.items()}

    return {}


def load_metrics_table(directory: Path = OUTPUTS_DIR) -> pd.DataFrame:
    metrics_path = directory / "optimized_test_metrics.csv"
    if not metrics_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(metrics_path, index_col=0)
    return df.reset_index().rename(columns={"index": "model"})


def load_optional_counties_path() -> Path | None:
    return COUNTIES_SHP_PATH if COUNTIES_SHP_PATH.exists() else None


def load_optional_kenya_adm1_geojson() -> dict[str, Any] | None:
    candidates = [
        KENYA_ADM1_GEOJSON_PATH,
        BASE_DIR / "kenya_adm1.geojson",
        BASE_DIR / "kenya_admin1.geojson",
        BASE_DIR / "kenya_counties.geojson",
        BASE_DIR / "KEN_ADM1.geojson",
        BASE_DIR / "KEN_ADM1.json",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_optional_kenya_adm0_geojson() -> dict[str, Any] | None:
    """Country outline (ADM0) — e.g. geoBoundaries-KEN-ADM0.geojson."""
    candidates = [
        KENYA_ADM0_GEOJSON_PATH,
        BASE_DIR / "kenya_adm0.geojson",
        BASE_DIR / "kenya_country.geojson",
        BASE_DIR / "KEN_ADM0.geojson",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_artifact_paths(directory: Path = OUTPUTS_DIR) -> dict[str, Path | None]:
    return {
        "model": _first_existing(directory, MODEL_CANDIDATES),
        "scaler": _first_existing(directory, SCALER_CANDIDATES),
        "threshold": _first_existing(directory, THRESHOLD_CANDIDATES),
    }

