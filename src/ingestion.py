from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd

from .data_loader import REQUIRED_WFP_COLUMNS


MARKET_PRICE_TEMPLATE_COLUMNS = [
    "date",
    "commodity",
    "market",
    "county",
    "price_retail",
    "price_wholesale",
    "unit",
]

ECONOMIC_TEMPLATE_COLUMNS = ["date", "CPI", "inflation_rate"]
GLOBAL_PRICE_TEMPLATE_COLUMNS = ["date", "commodity", "global_price"]
CLIMATE_TEMPLATE_COLUMNS = ["date", "county", "rainfall_anomaly", "SPI", "NDVI"]
SHOCK_TEMPLATE_COLUMNS = ["date", "event_type", "region", "severity"]
INFRA_TEMPLATE_COLUMNS = ["market", "road_density", "distance_nairobi", "trade_corridor"]


@dataclass
class ValidationSummary:
    dataset: str
    rows: int
    missing_columns: list[str]
    invalid_dates: int
    duplicate_rows: int
    accepted: bool


def read_uploaded_table(uploaded_file: object) -> pd.DataFrame:
    file_name = getattr(uploaded_file, "name", "uploaded.csv")
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(uploaded_file)
    if suffix == ".xlsx":
        return pd.read_excel(uploaded_file)
    raise ValueError("Only CSV and XLSX uploads are supported.")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [
        str(column).strip().lower().replace(" ", "_").replace("-", "_")
        for column in normalized.columns
    ]
    return normalized


def _clean_text(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _title_case_series(series: pd.Series) -> pd.Series:
    return series.fillna("").map(_clean_text).replace("", np.nan).str.title()


def _series_or_default(df: pd.DataFrame, column: str, default: object) -> pd.Series:
    if column in df.columns:
        return df[column]
    if isinstance(default, pd.Series):
        return default
    return pd.Series([default] * len(df), index=df.index)


def _parse_monthly_date(series: pd.Series) -> pd.Series:
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    text_values = series.astype(str).str.strip()

    formats = [
        "%Y-%m",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%m/%Y",
        "%b %Y",
        "%B %Y",
    ]
    for fmt in formats:
        missing = parsed.isna()
        if not missing.any():
            break
        parsed.loc[missing] = pd.to_datetime(
            text_values.loc[missing],
            format=fmt,
            errors="coerce",
        )

    if parsed.isna().any():
        missing = parsed.isna()
        parsed.loc[missing] = pd.to_datetime(text_values.loc[missing], errors="coerce")

    return parsed.dt.to_period("M").dt.to_timestamp()


def validate_upload(
    dataset_name: str,
    df: pd.DataFrame,
    required_columns: list[str],
    date_column: str | None = "date",
    duplicate_subset: list[str] | None = None,
) -> ValidationSummary:
    normalized = _normalize_columns(df)
    missing = [column for column in required_columns if column not in normalized.columns]
    invalid_dates = 0
    if date_column and date_column in normalized.columns:
        invalid_dates = int(_parse_monthly_date(normalized[date_column]).isna().sum())

    duplicate_rows = 0
    if duplicate_subset:
        available = [column for column in duplicate_subset if column in normalized.columns]
        if available:
            duplicate_rows = int(normalized.duplicated(subset=available).sum())

    accepted = not missing and invalid_dates == 0
    return ValidationSummary(
        dataset=dataset_name,
        rows=int(len(normalized)),
        missing_columns=missing,
        invalid_dates=invalid_dates,
        duplicate_rows=duplicate_rows,
        accepted=accepted,
    )


def validate_market_upload(dataset_name: str, df: pd.DataFrame) -> ValidationSummary:
    """Validate market price upload: requires date, commodity, market, county, and at least one price column. Unit is optional."""
    normalized = _normalize_columns(df)
    required = ["date", "commodity", "market", "county"]
    price_cols = ["price", "price_retail", "price_wholesale", "retail_price", "wholesale_price"]
    missing = [c for c in required if c not in normalized.columns]
    has_price = any(c in normalized.columns for c in price_cols)
    if not has_price:
        missing.append("(one of: " + ", ".join(price_cols) + ")")
    invalid_dates = 0
    if "date" in normalized.columns:
        invalid_dates = int(_parse_monthly_date(normalized["date"]).isna().sum())
    duplicate_rows = 0
    for subset in [["date", "commodity", "market", "county"], ["date", "admin2", "market", "commodity"]]:
        available = [c for c in subset if c in normalized.columns]
        if len(available) == len(subset):
            duplicate_rows = int(normalized.duplicated(subset=available).sum())
            break
    accepted = not missing and invalid_dates == 0
    return ValidationSummary(
        dataset=dataset_name,
        rows=int(len(normalized)),
        missing_columns=missing,
        invalid_dates=invalid_dates,
        duplicate_rows=duplicate_rows,
        accepted=accepted,
    )


def validation_summary_frame(summaries: list[ValidationSummary]) -> pd.DataFrame:
    if not summaries:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "dataset": summary.dataset,
                "rows": summary.rows,
                "missing_columns": ", ".join(summary.missing_columns) if summary.missing_columns else "None",
                "invalid_dates": summary.invalid_dates,
                "duplicate_rows": summary.duplicate_rows,
                "accepted": "Yes" if summary.accepted else "No",
            }
            for summary in summaries
        ]
    )


def harmonize_market_price_data(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_columns(df)
    rename_map = {
        "county": "admin2",
        "region": "admin1",
        "price_retail": "price",
        "retail_price": "price",
        "price_wholesale": "price_wholesale",
        "wholesale_price": "price_wholesale",
    }
    normalized = normalized.rename(columns=rename_map)

    if "price" not in normalized.columns and "price_wholesale" in normalized.columns:
        normalized["price"] = normalized["price_wholesale"]

    normalized["date"] = _parse_monthly_date(normalized["date"])
    admin1_source = normalized["admin1"] if "admin1" in normalized.columns else _series_or_default(normalized, "admin2", "Unknown")
    normalized["admin1"] = _title_case_series(admin1_source)
    normalized["admin2"] = _title_case_series(normalized["admin2"])
    normalized["market"] = _title_case_series(normalized["market"])
    normalized["commodity"] = normalized["commodity"].fillna("").map(_clean_text).replace("", np.nan)
    normalized["unit"] = _series_or_default(normalized, "unit", "KG").fillna("KG").map(_clean_text).str.upper()
    normalized["price"] = pd.to_numeric(normalized["price"], errors="coerce")
    normalized["price_wholesale"] = pd.to_numeric(_series_or_default(normalized, "price_wholesale", np.nan), errors="coerce")

    normalized["market_id"] = _series_or_default(normalized, "market_id", pd.Series(normalized["market"].factorize()[0] + 1, index=normalized.index))
    normalized["latitude"] = pd.to_numeric(_series_or_default(normalized, "latitude", np.nan), errors="coerce")
    normalized["longitude"] = pd.to_numeric(_series_or_default(normalized, "longitude", np.nan), errors="coerce")
    normalized["category"] = _series_or_default(normalized, "category", "Uploaded Market Prices").fillna("Uploaded Market Prices")
    normalized["commodity_id"] = _series_or_default(
        normalized,
        "commodity_id",
        pd.Series(normalized["commodity"].factorize()[0] + 1, index=normalized.index),
    )
    normalized["priceflag"] = _series_or_default(normalized, "priceflag", "actual").fillna("actual")
    normalized["pricetype"] = _series_or_default(normalized, "pricetype", "Retail").fillna("Retail")
    normalized["currency"] = _series_or_default(normalized, "currency", "KES").fillna("KES").map(_clean_text).str.upper()
    normalized["usdprice"] = pd.to_numeric(_series_or_default(normalized, "usdprice", np.nan), errors="coerce")

    cleaned = normalized.dropna(subset=["date", "admin2", "market", "commodity", "price"]).copy()
    cleaned = cleaned[cleaned["price"] > 0].copy()
    cleaned = cleaned.sort_values(["admin2", "commodity", "market", "date"]).copy()
    cleaned = cleaned.drop_duplicates(subset=["date", "admin2", "market", "commodity"], keep="last")
    return cleaned[REQUIRED_WFP_COLUMNS].reset_index(drop=True)


def harmonize_economic_data(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_columns(df).rename(
        columns={
            "cpi": "CPI",
            "consumer_price_index": "CPI",
            "inflation_rate": "Inflation_pct",
            "inflation": "Inflation_pct",
        }
    )
    normalized["date"] = _parse_monthly_date(normalized["date"])
    if "CPI" in normalized.columns:
        normalized["CPI"] = pd.to_numeric(normalized["CPI"], errors="coerce")
    if "Inflation_pct" in normalized.columns:
        normalized["Inflation_pct"] = pd.to_numeric(normalized["Inflation_pct"], errors="coerce")

    if "Inflation_pct" not in normalized.columns and "CPI" in normalized.columns:
        normalized = normalized.sort_values("date").copy()
        normalized["Inflation_pct"] = normalized["CPI"].pct_change().mul(100)

    if "CPI" not in normalized.columns and "Inflation_pct" not in normalized.columns:
        raise ValueError("Economic indicators upload must include `CPI` or `inflation_rate`.")

    columns = [column for column in ["date", "CPI", "Inflation_pct"] if column in normalized.columns]
    return normalized[columns].dropna(subset=["date"]).drop_duplicates(subset=["date"]).reset_index(drop=True)


def harmonize_global_prices(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_columns(df)
    normalized["date"] = _parse_monthly_date(normalized["date"])
    normalized["commodity"] = normalized["commodity"].fillna("").map(_clean_text).str.lower()
    normalized["global_price"] = pd.to_numeric(normalized["global_price"], errors="coerce")
    cleaned = normalized.dropna(subset=["date", "global_price"]).copy()

    maize_rows = cleaned[cleaned["commodity"].str.contains("maize", na=False)].copy()
    source_rows = maize_rows if not maize_rows.empty else cleaned
    fpma = (
        source_rows.groupby("date", as_index=False)["global_price"]
        .mean()
        .rename(columns={"date": "Date", "global_price": "fpma_maize"})
        .sort_values("Date")
        .reset_index(drop=True)
    )
    return fpma


def harmonize_climate_data(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    normalized = _normalize_columns(df).rename(
        columns={
            "county": "COUNTY",
            "rainfall": "rain_mm",
            "rainfall_mm": "rain_mm",
            "rainfall_anomaly": "rain_mm",
            "spi": "SPI3",
            "ndvi": "NDVI",
        }
    )
    normalized["date"] = _parse_monthly_date(normalized["date"])
    normalized["COUNTY"] = _title_case_series(normalized["COUNTY"])
    for column in ["rain_mm", "SPI3", "SPI6", "NDVI"]:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    rain_columns = [column for column in ["COUNTY", "date", "rain_mm", "SPI3", "SPI6"] if column in normalized.columns]
    ndvi_columns = [column for column in ["COUNTY", "date", "NDVI", "NDVI_anomaly"] if column in normalized.columns]
    return {
        "rain": normalized[rain_columns].dropna(subset=["COUNTY", "date"]).drop_duplicates().reset_index(drop=True),
        "ndvi": normalized[ndvi_columns].dropna(subset=["COUNTY", "date"]).drop_duplicates().reset_index(drop=True),
    }


def harmonize_shock_data(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_columns(df).rename(columns={"region": "COUNTY"})
    normalized["date"] = _parse_monthly_date(normalized["date"])
    normalized["COUNTY"] = _title_case_series(normalized["COUNTY"])
    normalized["event_type"] = normalized["event_type"].fillna("").map(_clean_text)
    normalized["severity"] = normalized["severity"].fillna("").map(_clean_text).str.title()
    return normalized[["date", "COUNTY", "event_type", "severity"]].dropna(subset=["date", "COUNTY"]).reset_index(drop=True)


def harmonize_infrastructure_data(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_columns(df)
    normalized["market"] = _title_case_series(normalized["market"])
    normalized["road_density"] = pd.to_numeric(normalized.get("road_density", np.nan), errors="coerce")
    normalized["distance_nairobi"] = pd.to_numeric(
        normalized.get("distance_nairobi", np.nan), errors="coerce"
    )
    normalized["trade_corridor"] = (
        _series_or_default(normalized, "trade_corridor", "")
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"yes": "Yes", "no": "No", "true": "Yes", "false": "No"})
        .fillna("Unknown")
    )
    return normalized[
        ["market", "road_density", "distance_nairobi", "trade_corridor"]
    ].dropna(subset=["market"]).drop_duplicates(subset=["market"]).reset_index(drop=True)
