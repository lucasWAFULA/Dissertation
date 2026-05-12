from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer

from .config import DEFAULT_FEATURE_NAMES


def _extract_mass_unit_kg(unit: object) -> float:
    unit_text = str(unit).upper().strip()
    unit_text = re.sub(r"\s+", " ", unit_text)

    if unit_text == "KG":
        return 1.0

    kg_match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*KG", unit_text)
    if kg_match:
        return float(kg_match.group(1))

    gram_match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*G", unit_text)
    if gram_match:
        return float(gram_match.group(1)) / 1000

    return np.nan


def _drop_unrealistic_commodity_prices(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    cleaned = frame.copy()
    cleaned["log_price_per_kg"] = np.log(cleaned["price"])

    bounds = cleaned.groupby("commodity")["log_price_per_kg"].agg(
        q1=lambda series: series.quantile(0.25),
        q3=lambda series: series.quantile(0.75),
    )
    bounds["iqr"] = bounds["q3"] - bounds["q1"]
    bounds["lower"] = bounds["q1"] - (3 * bounds["iqr"])
    bounds["upper"] = bounds["q3"] + (3 * bounds["iqr"])

    cleaned = cleaned.merge(
        bounds[["lower", "upper", "iqr"]],
        left_on="commodity",
        right_index=True,
        how="left",
    )

    keep_mask = (
        cleaned["iqr"].fillna(0).eq(0)
        | cleaned["log_price_per_kg"].between(cleaned["lower"], cleaned["upper"])
    )
    cleaned = cleaned.loc[keep_mask].copy()
    return cleaned.drop(columns=["log_price_per_kg", "lower", "upper", "iqr"])


def build_cpi_index(inflation: pd.DataFrame) -> pd.DataFrame:
    inflation = inflation.sort_values("date").reset_index(drop=True).copy()
    if "CPI" in inflation.columns and inflation["CPI"].notna().any():
        inflation["CPI_index"] = pd.to_numeric(inflation["CPI"], errors="coerce")
        cpi = inflation[["date", "CPI_index"]].dropna(subset=["date", "CPI_index"]).copy()
        cpi["year"] = cpi["date"].dt.year
        cpi["month"] = cpi["date"].dt.month
        return cpi

    # The KNBS file available here contains monthly inflation percentages, not
    # a full CPI level series. Compounding those percentages backward/forward
    # collapses early CPI values toward zero and creates unrealistic real prices.
    inflation["CPI_index"] = 100.0 + inflation["Inflation_pct"].clip(lower=-99.0)

    cpi = inflation[["date", "CPI_index"]].copy()
    cpi["year"] = cpi["date"].dt.year
    cpi["month"] = cpi["date"].dt.month
    return cpi


def clean_wfp_prices(wfp: pd.DataFrame) -> pd.DataFrame:
    wfp_clean = wfp.copy()
    wfp_clean["unit_mass_kg"] = wfp_clean["unit"].map(_extract_mass_unit_kg)
    wfp_clean = wfp_clean[wfp_clean["unit_mass_kg"].notna()].copy()

    wfp_clean["raw_unit"] = wfp_clean["unit"]
    wfp_clean["raw_price"] = wfp_clean["price"]
    wfp_clean["price"] = wfp_clean["price"] / wfp_clean["unit_mass_kg"]
    if "usdprice" in wfp_clean.columns:
        wfp_clean["usdprice"] = wfp_clean["usdprice"] / wfp_clean["unit_mass_kg"]
    wfp_clean["unit"] = "KG"
    wfp_clean["unit_scale"] = wfp_clean["unit_mass_kg"]

    wfp_clean = wfp_clean[wfp_clean["price"] > 0].copy()
    wfp_clean["price_prev"] = (
        wfp_clean.groupby(["county", "market", "commodity"])["price"].shift(1)
    )
    wfp_clean["ratio"] = wfp_clean["price"] / wfp_clean["price_prev"].replace(0, np.nan)
    typo_mask = (wfp_clean["ratio"] > 5) | (wfp_clean["ratio"] < 0.2)
    wfp_clean = wfp_clean.loc[~typo_mask].drop(columns=["price_prev", "ratio"])
    return _drop_unrealistic_commodity_prices(wfp_clean)


def build_monthly_price_series(wfp_clean: pd.DataFrame) -> pd.DataFrame:
    monthly = wfp_clean.copy()
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month

    wfp_monthly = monthly.groupby(
        ["county", "commodity", "year", "month"], as_index=False
    ).agg(price=("price", "mean"), usdprice=("usdprice", "mean"))

    wfp_monthly["date"] = pd.to_datetime(
        wfp_monthly["year"].astype(str)
        + "-"
        + wfp_monthly["month"].astype(str)
        + "-01"
    )

    wfp_pivot = wfp_monthly.pivot_table(
        index=["county", "commodity"],
        columns="date",
        values="price",
    )
    full_months = pd.date_range(
        wfp_pivot.columns.min(),
        wfp_pivot.columns.max(),
        freq="MS",
    )
    wfp_pivot = wfp_pivot.reindex(columns=full_months)

    wfp_interp = wfp_pivot.T.interpolate(method="linear", limit=3).T
    filled = pd.DataFrame(
        KNNImputer(n_neighbors=5).fit_transform(wfp_interp),
        index=wfp_interp.index,
        columns=wfp_interp.columns,
    )
    filled = filled.ffill(axis=1).bfill(axis=1)

    wfp_long = filled.stack().reset_index()
    wfp_long.columns = ["county", "commodity", "date", "price_nominal"]
    wfp_long["year"] = wfp_long["date"].dt.year
    wfp_long["month"] = wfp_long["date"].dt.month
    return wfp_long.dropna(subset=["price_nominal"]).reset_index(drop=True)


def add_price_features(wfp_long: pd.DataFrame, cpi: pd.DataFrame) -> pd.DataFrame:
    df = wfp_long.copy()
    cpi_cols = [col for col in df.columns if col.startswith("CPI_index")]
    if cpi_cols:
        df = df.drop(columns=cpi_cols)

    df = df.merge(cpi[["year", "month", "CPI_index"]], on=["year", "month"], how="left")
    df["price_real"] = df["price_nominal"] / (df["CPI_index"] / 100)
    df = df.dropna(subset=["price_real"]).copy()
    df["log_price"] = np.log(df["price_real"] + 1)

    df = df.sort_values(["county", "commodity", "date"]).reset_index(drop=True)
    df["price_prev"] = df.groupby(["county", "commodity"])["price_real"].shift(1)
    df["growth_rate"] = (
        (df["price_real"] - df["price_prev"])
        / df["price_prev"].replace(0, np.nan)
        * 100
    )
    df["rolling_vol"] = df.groupby(["county", "commodity"])["growth_rate"].transform(
        lambda values: values.rolling(6, min_periods=2).std()
    )
    return df.drop(columns=["price_prev"])


def label_price_anomalies(wfp_long: pd.DataFrame) -> pd.DataFrame:
    prices = wfp_long.rename(columns={"county": "COUNTY"}).copy()
    prices_sorted = prices.sort_values("date").copy()
    rolling_q = prices_sorted["price_real"].rolling(6).quantile(0.5)
    prices_sorted["price_anomaly"] = (prices_sorted["price_real"] >= rolling_q).astype(int)
    prices["price_anomaly"] = prices_sorted["price_anomaly"].reindex(prices.index).values

    if prices["price_anomaly"].isna().any():
        prices["price_anomaly"] = prices["price_anomaly"].fillna(0)

    if prices["price_anomaly"].mean() < 0.01:
        cutoff = prices["price_real"].quantile(0.9)
        prices["price_anomaly"] = (prices["price_real"] >= cutoff).astype(int)

    prices["price_anomaly"] = prices["price_anomaly"].astype(int)
    return prices


def _normalize_county_month_frame(
    frame: pd.DataFrame | None,
    date_col: str = "date",
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["COUNTY", "date"])

    normalized = frame.copy()
    cols = {col.lower(): col for col in normalized.columns}

    county_col = cols.get("county") or cols.get("name")
    if county_col and county_col != "COUNTY":
        normalized = normalized.rename(columns={county_col: "COUNTY"})

    if date_col not in normalized.columns:
        year_col = cols.get("year")
        month_col = cols.get("month")
        if year_col and month_col:
            normalized["date"] = pd.to_datetime(
                normalized[year_col].astype(int).astype(str)
                + "-"
                + normalized[month_col].astype(int).astype(str)
                + "-01"
            )
        else:
            raise KeyError("Climate frame must have `date` or `year`/`month` columns.")

    normalized["COUNTY"] = normalized["COUNTY"].astype(str)
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.to_period("M").dt.to_timestamp()
    return normalized


def _compute_spi_from_rain(rain_df: pd.DataFrame, scale: int) -> pd.Series:
    rain = rain_df["rain_mm"].fillna(0)
    roll = rain.rolling(scale, min_periods=scale).sum()
    mean = roll.mean()
    std = roll.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series(np.zeros(len(rain_df)), index=rain_df.index)
    return ((roll - mean) / std).fillna(0)


def prepare_climate_features(
    prices: pd.DataFrame,
    climate_tables: dict[str, pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    climate_tables = climate_tables or {}
    county_dates = prices[["COUNTY", "date"]].drop_duplicates().copy()
    county_dates["COUNTY"] = county_dates["COUNTY"].astype(str)
    county_dates["date"] = pd.to_datetime(county_dates["date"]).dt.to_period("M").dt.to_timestamp()

    ndvi_df = _normalize_county_month_frame(climate_tables.get("ndvi"))
    if "NDVI" not in ndvi_df.columns and not ndvi_df.empty:
        ndvi_candidates = [col for col in ndvi_df.columns if "ndvi" in col.lower()]
        if ndvi_candidates:
            ndvi_df = ndvi_df.rename(columns={ndvi_candidates[0]: "NDVI"})
        elif "mean" in ndvi_df.columns:
            ndvi_df = ndvi_df.rename(columns={"mean": "NDVI"})

    if "NDVI_anomaly" in ndvi_df.columns:
        ndvi_merge = ndvi_df[["COUNTY", "date", "NDVI_anomaly"]].copy()
    elif "NDVI" in ndvi_df.columns:
        ndvi_df["month"] = ndvi_df["date"].dt.month
        baseline = ndvi_df.groupby(["COUNTY", "month"])["NDVI"].transform("mean")
        ndvi_df["NDVI_anomaly"] = ndvi_df["NDVI"] - baseline
        ndvi_merge = ndvi_df[["COUNTY", "date", "NDVI_anomaly"]].copy()
    else:
        ndvi_merge = county_dates.copy()
        ndvi_merge["NDVI_anomaly"] = 0.0

    rain_df = _normalize_county_month_frame(climate_tables.get("rain"))
    if "rain_mm" not in rain_df.columns and "rainfall_anomaly" in rain_df.columns:
        rain_df = rain_df.rename(columns={"rainfall_anomaly": "rain_mm"})

    if "rain_mm" not in rain_df.columns and not rain_df.empty:
        rain_candidates = [col for col in rain_df.columns if "rain" in col.lower() or "precip" in col.lower()]
        if rain_candidates:
            rain_df = rain_df.rename(columns={rain_candidates[0]: "rain_mm"})

    if "SPI" in rain_df.columns:
        rain_df = rain_df.rename(columns={"SPI": "SPI3"})
    if "SPI3" in rain_df.columns and "SPI6" not in rain_df.columns:
        rain_df["SPI6"] = rain_df["SPI3"]

    if "rain_mm" in rain_df.columns:
        rain_df = rain_df.sort_values(["COUNTY", "date"]).copy()
        if "SPI3" not in rain_df.columns:
            rain_df["SPI3"] = rain_df.groupby("COUNTY", group_keys=False).apply(
                lambda group: _compute_spi_from_rain(group, 3)
            )
        if "SPI6" not in rain_df.columns:
            rain_df["SPI6"] = rain_df.groupby("COUNTY", group_keys=False).apply(
                lambda group: _compute_spi_from_rain(group, 6)
            )
        rain_merge = rain_df[["COUNTY", "date", "rain_mm", "SPI3", "SPI6"]].copy()
    elif {"SPI3", "SPI6"}.intersection(rain_df.columns):
        rain_merge = county_dates.merge(
            rain_df[[col for col in ["COUNTY", "date", "SPI3", "SPI6"] if col in rain_df.columns]],
            on=["COUNTY", "date"],
            how="left",
        )
        rain_merge["rain_mm"] = 0.0
        if "SPI3" not in rain_merge.columns:
            rain_merge["SPI3"] = 0.0
        else:
            rain_merge["SPI3"] = rain_merge["SPI3"].fillna(0.0)
        if "SPI6" not in rain_merge.columns:
            rain_merge["SPI6"] = rain_merge["SPI3"]
        else:
            rain_merge["SPI6"] = rain_merge["SPI6"].fillna(rain_merge["SPI3"])
    else:
        rain_merge = county_dates.copy()
        rain_merge["rain_mm"] = 0.0
        rain_merge["SPI3"] = 0.0
        rain_merge["SPI6"] = 0.0

    return ndvi_merge, rain_merge


def add_external_features(
    prices: pd.DataFrame,
    inflation: pd.DataFrame,
    fpma: pd.DataFrame,
    climate_tables: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    ndvi_merge, rain_merge = prepare_climate_features(prices, climate_tables=climate_tables)

    final_df = prices.copy()
    final_df["COUNTY"] = final_df["COUNTY"].astype(str)
    final_df = final_df.merge(ndvi_merge, on=["COUNTY", "date"], how="left")
    final_df = final_df.merge(rain_merge, on=["COUNTY", "date"], how="left")

    infl_merge = inflation[["date", "Inflation_pct"]].rename(
        columns={"Inflation_pct": "inflation_pct"}
    )
    final_df = final_df.merge(infl_merge, on="date", how="left")

    if "fpma_maize" in fpma.columns and "Date" in fpma.columns:
        fpma_maize = fpma[["Date", "fpma_maize"]].rename(columns={"Date": "date"})
        fpma_maize["date"] = pd.to_datetime(fpma_maize["date"]).dt.to_period("M").dt.to_timestamp()
        final_df["date_period"] = final_df["date"].dt.to_period("M").dt.to_timestamp()
        final_df = final_df.merge(
            fpma_maize,
            left_on="date_period",
            right_on="date",
            how="left",
            suffixes=("", "_fpma"),
        )
        final_df = final_df.drop(columns=["date_period", "date_fpma"], errors="ignore")
    else:
        fpma_cols = [col for col in fpma.columns if "maize" in col.lower() and "argentina" in col.lower()]
        if fpma_cols:
            fpma_maize = fpma[["Date", fpma_cols[0]]].rename(
                columns={"Date": "date", fpma_cols[0]: "fpma_maize"}
            )
            fpma_maize["date"] = pd.to_datetime(fpma_maize["date"]).dt.to_period("M").dt.to_timestamp()
            final_df["date_period"] = final_df["date"].dt.to_period("M").dt.to_timestamp()
            final_df = final_df.merge(
                fpma_maize,
                left_on="date_period",
                right_on="date",
                how="left",
                suffixes=("", "_fpma"),
            )
            final_df = final_df.drop(columns=["date_period", "date_fpma"], errors="ignore")
        else:
            final_df["fpma_maize"] = 0.0

    return final_df


def add_lag_features(final_df: pd.DataFrame) -> pd.DataFrame:
    final_df = final_df.sort_values(["COUNTY", "commodity", "date"]).copy()
    group_keys = ["COUNTY", "commodity"]
    final_df["price_lag1"] = final_df.groupby(group_keys)["price_real"].shift(1)
    final_df["price_lag2"] = final_df.groupby(group_keys)["price_real"].shift(2)
    final_df["price_lag3"] = final_df.groupby(group_keys)["price_real"].shift(3)
    final_df["price_roll3"] = final_df.groupby(group_keys)["price_real"].transform(
        lambda values: values.rolling(3, min_periods=1).mean()
    )
    final_df["NDVI_lag1"] = final_df.groupby(group_keys)["NDVI_anomaly"].shift(1)
    final_df["SPI3_lag1"] = final_df.groupby(group_keys)["SPI3"].shift(1)
    return final_df


def finalize_feature_table(
    final_df: pd.DataFrame,
    feature_names: list[str] | None = None,
) -> pd.DataFrame:
    feature_names = feature_names or DEFAULT_FEATURE_NAMES
    final_df = final_df.copy()

    for column in feature_names:
        if column not in final_df.columns:
            final_df[column] = 0.0

    fill_zero_columns = [
        "NDVI_anomaly",
        "rain_mm",
        "SPI3",
        "SPI6",
        "NDVI_lag1",
        "SPI3_lag1",
        "fpma_maize",
        "inflation_pct",
        "growth_rate",
        "rolling_vol",
        "price_lag1",
        "price_lag2",
        "price_lag3",
    ]
    existing_fill_columns = [col for col in fill_zero_columns if col in final_df.columns]
    final_df[existing_fill_columns] = final_df[existing_fill_columns].fillna(0)
    final_df["price_roll3"] = final_df["price_roll3"].fillna(final_df["price_real"])
    final_df["price_real"] = final_df["price_real"].fillna(0)

    return final_df.sort_values(["date", "COUNTY", "commodity"]).reset_index(drop=True)


def build_feature_dataset(
    wfp: pd.DataFrame,
    fpma: pd.DataFrame,
    inflation: pd.DataFrame,
    feature_names: list[str] | None = None,
    climate_tables: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    cpi = build_cpi_index(inflation)
    wfp_clean = clean_wfp_prices(wfp)
    wfp_long = build_monthly_price_series(wfp_clean)
    wfp_long = add_price_features(wfp_long, cpi)
    prices = label_price_anomalies(wfp_long)
    final_df = add_external_features(
        prices=prices,
        inflation=inflation,
        fpma=fpma,
        climate_tables=climate_tables,
    )
    final_df = add_lag_features(final_df)
    return finalize_feature_table(final_df, feature_names=feature_names)


def summarize_pipeline_output(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "commodities": int(frame["commodity"].nunique()) if "commodity" in frame else 0,
        "counties": int(frame["COUNTY"].nunique()) if "COUNTY" in frame else 0,
        "date_min": frame["date"].min() if "date" in frame and not frame.empty else None,
        "date_max": frame["date"].max() if "date" in frame and not frame.empty else None,
    }

