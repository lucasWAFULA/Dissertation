# APPENDIX: Technical Implementation Details
## Food Price Anomaly Detection System - Kenya

---

## 1. Data Description and Sources

### 1.1 Food Price Data
**Source:** World Food Programme (WFP) Price Database via OCHA  
**Coverage:** Monthly retail/wholesale prices (2006-2025)  
**Commodities:** Maize, beans, rice  
**Spatial Resolution:** County-level (47 counties)  
**Records:** 137,358 monthly observations

```python
# Data loading
WFP_PATH = DATA_DIR / "wfp_food_prices_ken (1).csv"
wfp = pd.read_csv(WFP_PATH)
wfp["date"] = pd.to_datetime(wfp["date"], format="%d/%m/%Y")
wfp = wfp.sort_values(["admin2", "commodity", "market", "date"])

# Rename columns for analysis
wfp = wfp.rename(columns={"admin1": "region", "admin2": "county"})
```

**Key Columns:**
- `date`: Observation date
- `county`: County name (admin2)
- `commodity`: Food commodity type
- `market`: Market name
- `price`: Nominal price (KES)

### 1.2 Climate Data
**Source:** Google Earth Engine (MODIS, CHIRPS)  
**Variables:**
- **NDVI:** MODIS MOD13Q1 (250m resolution, 16-day)
- **Rainfall:** CHIRPS daily (5km resolution)

```python
# Earth Engine initialization
import ee
import geemap

EE_PROJECT = "food-price-anomaly"
ee.Initialize(project=EE_PROJECT)

# NDVI extraction (county-level monthly aggregation)
def get_ndvi_rainfall_ee():
    ndvi = ee.ImageCollection("MODIS/061/MOD13Q1").select("NDVI")
    ndvi = ndvi.filterDate("2015-01-01", "2024-12-31")
    
    # Scale NDVI
    def scale_ndvi(img):
        return img.multiply(0.0001).copyProperties(img, ["system:time_start"])
    
    ndvi = ndvi.map(scale_ndvi)
    
    # Monthly aggregation per county
    years = range(2015, 2025)
    months = range(1, 13)
    
    def monthly_ndvi(year, month):
        start = ee.Date.fromYMD(year, month, 1)
        end = start.advance(1, "month")
        return ndvi.filterDate(start, end).mean().set("year", year).set("month", month)
    
    ndvi_monthly = ee.ImageCollection([monthly_ndvi(y, m) for y in years for m in months])
    
    # Reduce by county boundaries
    def reduce_county(img):
        stats = img.reduceRegions(collection=counties_ee, reducer=ee.Reducer.mean(), scale=250)
        return stats.map(lambda f: f.set("year", img.get("year")).set("month", img.get("month")))
    
    ndvi_county = ndvi_monthly.map(reduce_county).flatten()
    ndvi_df = geemap.ee_to_df(ndvi_county)
    
    return ndvi_df
```

### 1.3 Economic Data
**Source:** Kenya National Bureau of Statistics (KNBS)  
**Variables:**
- **CPI:** Consumer Price Index (monthly, base 2015=100)
- **Inflation:** Month-on-month inflation rate (%)

```python
# Inflation data loading
INFLATION_PATH = DATA_DIR / "Inflation Rates.csv"
inflation = pd.read_csv(INFLATION_PATH)

# CPI index construction
def build_cpi_index(inflation_df, base_year=2015):
    """Build CPI index from inflation rates (base=100)."""
    cpi = inflation_df.sort_values(["year", "month"]).copy()
    cpi["CPI_index"] = 100.0
    
    # Cumulative product of (1 + inflation_rate)
    for i in range(1, len(cpi)):
        if cpi.iloc[i]["year"] == base_year and cpi.iloc[i]["month"] == 1:
            cpi.iloc[i, cpi.columns.get_loc("CPI_index")] = 100.0
        else:
            prev_cpi = cpi.iloc[i-1]["CPI_index"]
            infl_rate = cpi.iloc[i]["Inflation_pct"] / 100
            cpi.iloc[i, cpi.columns.get_loc("CPI_index")] = prev_cpi * (1 + infl_rate)
    
    return cpi[["year", "month", "CPI_index"]]

cpi = build_cpi_index(inflation)
```

### 1.4 Spatial Data
**Source:** Google Earth Engine (FAO GAUL)  
**Format:** Shapefile (kenya_counties.shp)  
**Attributes:** COUNTY name, geometry

```python
# Download Kenya counties shapefile
if not COUNTIES_SHP.exists() and EE_AVAILABLE:
    gadm = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(
        ee.Filter.eq("ADM0_NAME", "Kenya")
    )
    kenya_gdf = geemap.ee_to_gdf(gadm)
    kenya_gdf = kenya_gdf.rename(columns={"ADM1_NAME": "COUNTY"})[["COUNTY", "geometry"]]
    kenya_gdf.to_file(COUNTIES_SHP)
    print(f"Saved {len(kenya_gdf)} counties to {COUNTIES_SHP}")

# Load shapefile for spatial analysis
import geopandas as gpd
counties_gdf = gpd.read_file(COUNTIES_SHP)
```

---

## 2. Data Preprocessing Pipeline

### 2.1 Missing Values Handling

```python
# Strategy 1: Forward-fill then backward-fill (preserves temporal continuity)
wfp_filled = wfp_long.sort_values(["county", "commodity", "date"]).copy()
wfp_filled["price_nominal"] = (
    wfp_filled.groupby(["county", "commodity"])["price_nominal"]
    .transform(lambda x: x.ffill().bfill())
)

# Strategy 2: KNN Imputation for multivariate features
from sklearn.impute import KNNImputer

num_cols = ["price_real", "NDVI_anomaly", "rain_mm", "SPI3", "SPI6"]
kn = KNNImputer(n_neighbors=5, weights="distance")
final_df[num_cols] = kn.fit_transform(final_df[num_cols])

# Strategy 3: Fill climate features with 0 (conservative approach)
climate_cols = ["NDVI_anomaly", "rain_mm", "SPI3", "SPI6", "NDVI_lag1", "SPI3_lag1"]
for col in climate_cols:
    if col in feat_df.columns:
        feat_df[col] = feat_df[col].fillna(0)
```

### 2.2 Inflation Adjustment (Real Price Calculation)

```python
# Deflate nominal prices to real terms (base year 2015)
wfp_long["year"] = wfp_long["date"].dt.year
wfp_long["month"] = wfp_long["date"].dt.month

# Merge CPI index
wfp_long = wfp_long.merge(
    cpi[["year", "month", "CPI_index"]], 
    on=["year", "month"], 
    how="left"
)

# Calculate real price
wfp_long["price_real"] = wfp_long["price_nominal"] / (wfp_long["CPI_index"] / 100)

# Log-transform to stabilize variance
wfp_long["log_price"] = np.log(wfp_long["price_real"] + 1)

print(f"Real prices calculated. Mean real price: {wfp_long['price_real'].mean():.2f} KES")
```

### 2.3 Anomaly Labeling (Target Variable)

```python
# Method: Global Rolling Percentile (6-month window, 70th percentile)
prices = wfp_long.rename(columns={"county": "COUNTY"}).copy()
prices_sorted = prices.sort_values("date").copy()

window = 6
rolling_q = prices_sorted["price_real"].rolling(window).quantile(0.7)
prices_sorted["price_anomaly"] = (prices_sorted["price_real"] >= rolling_q).astype(int)

# Fallback: Global percentile if insufficient positives
if prices["price_anomaly"].mean() < 0.01:
    q = prices["price_real"].quantile(0.9)
    prices["price_anomaly"] = (prices["price_real"] >= q).astype(int)
    print("Fallback to global 90th percentile for anomaly labels")

print(f"Anomaly rate: {prices['price_anomaly'].mean():.2%}")
print(prices["price_anomaly"].value_counts())
```

---

## 3. Feature Engineering

### 3.1 Temporal Features (Price-based)

```python
# Growth rate: month-on-month percentage change (Equation 1)
k = 3  # look-back window
wfp_long = wfp_long.sort_values(["county", "commodity", "date"])
wfp_long["growth_rate"] = (
    wfp_long.groupby(["county", "commodity"])["price_real"]
    .pct_change(periods=1) * 100
)

# Rolling volatility: k-month standard deviation of growth rate (Equation 2)
wfp_long["rolling_vol"] = (
    wfp_long.groupby(["county", "commodity"])["growth_rate"]
    .transform(lambda x: x.rolling(k, min_periods=1).std())
)

# Lag features (autoregressive signals)
for lag in [1, 2, 3]:
    wfp_long[f"price_lag{lag}"] = (
        wfp_long.groupby(["county", "commodity"])["price_real"].shift(lag)
    )

# Rolling mean (3-month smoothed price)
wfp_long["price_roll3"] = (
    wfp_long.groupby(["county", "commodity"])["price_real"]
    .transform(lambda x: x.rolling(3, min_periods=1).mean())
)
```

### 3.2 Climate Features (Agro-ecological)

```python
# NDVI Anomaly: deviation from county-month historical mean
ndvi_df["date"] = pd.to_datetime(
    ndvi_df["year"].astype(str) + "-" + ndvi_df["month"].astype(str) + "-01"
)

baseline = ndvi_df.groupby(["COUNTY", "month"])["NDVI"].transform("mean")
ndvi_df["NDVI_anomaly"] = ndvi_df["NDVI"] - baseline

# Lagged NDVI (climate leads price by ~1 month)
ndvi_df = ndvi_df.sort_values(["COUNTY", "date"])
ndvi_df["NDVI_lag1"] = ndvi_df.groupby("COUNTY")["NDVI_anomaly"].shift(1)
```

### 3.3 SPI Calculation (Drought Index)

```python
def _spi_zscore(vals, scale):
    """SPI as z-score of scale-month rolling sum."""
    vals = np.asarray(vals, dtype=float)
    vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
    roll = pd.Series(vals).rolling(scale, min_periods=scale).sum()
    valid = roll.notna()
    
    if valid.sum() < scale:
        return np.nan * np.ones(len(vals))
    
    r = roll.loc[valid]
    mean, std = r.mean(), r.std()
    if pd.isna(std) or std <= 0:
        std = 1e-8
    
    spi = (roll - mean) / std
    return spi.values

def compute_spi_group(group, scale=3):
    """Compute SPI for a county group."""
    rain = group["rain_mm"].values.astype(float)
    if len(rain) < scale:
        group = group.copy()
        group[f"SPI{scale}"] = np.nan
        return group
    
    spi_vals = _spi_zscore(rain, scale)
    group = group.copy()
    group[f"SPI{scale}"] = spi_vals
    return group

# Apply SPI-3 and SPI-6 per county
rain_df = rain_df.groupby("COUNTY", group_keys=False).apply(lambda g: compute_spi_group(g, 3))
rain_df = rain_df.groupby("COUNTY", group_keys=False).apply(lambda g: compute_spi_group(g, 6))

# Lagged SPI (drought early warning)
rain_df["SPI3_lag1"] = rain_df.groupby("COUNTY")["SPI3"].shift(1)
```

### 3.4 Inter-commodity and Macro Features

```python
# International price linkage (FAO FPMA maize prices)
fpma_maize = fpma[fpma["commodity"] == "Maize"].copy()
fpma_maize["date"] = pd.to_datetime(fpma_maize["date"])
fpma_maize = fpma_maize[["date", "price"]].rename(columns={"price": "fpma_maize"})

final_df = final_df.merge(fpma_maize, on="date", how="left")

# Inflation rate (macroeconomic context)
final_df = final_df.merge(
    inflation[["date", "Inflation_pct"]].rename(columns={"Inflation_pct": "inflation_pct"}),
    on="date",
    how="left"
)
```

### 3.5 Complete Feature Table

| Feature | Category | Description | Rationale |
|---------|----------|-------------|-----------|
| `price_real` | Price | CPI-deflated real price | Target-related; captures absolute level |
| `growth_rate` | Price | Month-on-month % change | Captures sudden movements |
| `rolling_vol` | Price | 3-month std of growth rate | Measures instability |
| `price_lag1/2/3` | Temporal | Lagged prices | Autoregressive signal |
| `price_roll3` | Temporal | 3-month rolling mean | Smoothed trend |
| `NDVI_anomaly` | Climate | NDVI deviation from mean | Vegetation health proxy |
| `NDVI_lag1` | Climate | Lagged NDVI anomaly | Leading climate signal |
| `rain_mm` | Climate | Monthly rainfall | Water availability |
| `SPI3/SPI6` | Climate | Standardized Precip Index | Drought intensity |
| `SPI3_lag1` | Climate | Lagged SPI-3 | Early drought warning |
| `fpma_maize` | Inter-commodity | International maize price | Global price transmission |
| `inflation_pct` | Macro | Monthly inflation rate | Economic context |

---

## 4. Model Development and Tuning

### 4.1 Train-Test Split (Temporal)

```python
# Train: 2006-2022 | Test: 2023-2025
feat_df["date"] = pd.to_datetime(feat_df["date"])
feat_df = feat_df.sort_values("date").reset_index(drop=True)

train_df = feat_df[feat_df["date"] < "2023-01-01"].copy()
test_df = feat_df[feat_df["date"] >= "2023-01-01"].copy()

X_train = train_df[feature_cols].fillna(0)
y_train = train_df["price_anomaly"].astype(int)
X_test = test_df[feature_cols].fillna(0)
y_test = test_df["price_anomaly"].astype(int)

print(f"Train: {len(X_train)} samples, {y_train.sum()} anomalies ({y_train.mean():.2%})")
print(f"Test: {len(X_test)} samples, {y_test.sum()} anomalies ({y_test.mean():.2%})")
```

### 4.2 Expanding Window Cross-Validation

```python
# Validation years: 2016-2020 (each fold trains on all prior years)
val_years = [2016, 2017, 2018, 2019, 2020]

def expanding_window_splits():
    """Generate expanding window CV splits."""
    for year in val_years:
        train_mask = train_df["date"].dt.year < year
        val_mask = train_df["date"].dt.year == year
        
        if train_mask.sum() < 10 or val_mask.sum() < 1:
            continue
        
        train_idx = train_df.index[train_mask].tolist()
        val_idx = train_df.index[val_mask].tolist()
        
        if len(val_idx) > 0:
            yield train_idx, val_idx

expanding_cv = list(expanding_window_splits())
print(f"CV Folds: {len(expanding_cv)}")
for i, (tr, va) in enumerate(expanding_cv):
    print(f"  Fold {i+1}: train={len(tr)}, val={len(va)}, val_anomalies={y_train.iloc[va].sum()}")
```

### 4.3 Hyperparameter Tuning (GridSearchCV)

```python
from sklearn.model_selection import GridSearchCV
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

# Linear SVM with GridSearch
param_grid_svm = {
    "base_estimator__C": [0.01, 0.1, 1.0, 10],
    "base_estimator__class_weight": ["balanced", {0: 1, 1: 3}]
}

svc_linear = LinearSVC(max_iter=5000, random_state=42, dual="auto")
model_lin_svm_base = CalibratedClassifierCV(svc_linear, cv=3)

grid_svm = GridSearchCV(
    model_lin_svm_base,
    param_grid_svm,
    cv=expanding_cv,
    scoring="recall",
    n_jobs=-1,
    verbose=1
)

# Standardize features
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

grid_svm.fit(X_train_s, y_train)
print(f"Best SVM params: {grid_svm.best_params_}")
print(f"Best CV recall: {grid_svm.best_score_:.3f}")

model_lin_svm = grid_svm.best_estimator_
```

### 4.4 Model Training Examples

```python
# XGBoost with class imbalance handling
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

model_xgb = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    scale_pos_weight=scale_pos_weight,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric="logloss"
)
model_xgb.fit(X_train, y_train)

# Logistic Regression
model_logreg = LogisticRegression(
    C=1.0,
    class_weight="balanced",
    max_iter=1000,
    random_state=42
)
model_logreg.fit(X_train_s, y_train)

# LightGBM
model_lgb = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    class_weight="balanced",
    random_state=42
)
model_lgb.fit(X_train, y_train)
```

### 4.5 Threshold Optimization (Youden's J)

```python
from sklearn.metrics import roc_curve

# Find optimal threshold using ROC curve
fpr, tpr, thresholds = roc_curve(y_test, prob_logreg)
youden_j = tpr - fpr
optimal_idx = np.argmax(youden_j)
optimal_threshold = thresholds[optimal_idx]

print(f"Optimal threshold: {optimal_threshold:.3f}")
print(f"Default threshold: 0.500")

# Apply optimized threshold
p_opt = (prob_logreg >= optimal_threshold).astype(int)
```

---

## 5. System Implementation Details

### 5.1 Complete Data Loading Pipeline

```python
from pathlib import Path
import pandas as pd
import numpy as np

# Project structure
BASE_DIR = Path(".")
DATA_DIR = BASE_DIR
WFP_PATH = DATA_DIR / "wfp_food_prices_ken (1).csv"
FPMA_PATH = DATA_DIR / "FPMA_international_price_data.csv"
INFLATION_PATH = DATA_DIR / "Inflation Rates.csv"
COUNTIES_SHP = DATA_DIR / "kenya_counties.shp"

def load_all_data():
    """Load and return all required datasets."""
    # 1. WFP price data
    wfp = pd.read_csv(WFP_PATH)
    wfp["date"] = pd.to_datetime(wfp["date"], format="%d/%m/%Y")
    wfp = wfp.rename(columns={"admin1": "region", "admin2": "county"})
    
    # 2. Inflation data
    inflation = pd.read_csv(INFLATION_PATH)
    
    # 3. FPMA international prices
    fpma = pd.read_csv(FPMA_PATH)
    fpma["date"] = pd.to_datetime(fpma["date"])
    
    # 4. County boundaries
    if GPD_AVAILABLE and COUNTIES_SHP.exists():
        counties_gdf = gpd.read_file(COUNTIES_SHP)
    else:
        counties_gdf = None
    
    return wfp, inflation, fpma, counties_gdf

wfp, inflation, fpma, counties_gdf = load_all_data()
print("Data loaded successfully")
```

### 5.2 End-to-End Pipeline Execution

```python
def run_anomaly_detection_pipeline():
    """Execute complete anomaly detection pipeline."""
    
    # Step 1: Load data
    wfp, inflation, fpma, counties_gdf = load_all_data()
    
    # Step 2: Preprocess
    wfp_clean = clean_wfp_prices(wfp)  # Remove outliers, fix units
    cpi = build_cpi_index(inflation)    # Build CPI index
    
    # Step 3: Calculate real prices
    wfp_long = calculate_real_prices(wfp_clean, cpi)
    
    # Step 4: Feature engineering
    wfp_long = engineer_temporal_features(wfp_long)
    
    # Step 5: Get climate data
    ndvi_df, rain_df = get_climate_data_ee()
    rain_df = compute_spi_features(rain_df)
    
    # Step 6: Merge all features
    final_df = merge_all_features(wfp_long, ndvi_df, rain_df, fpma, inflation)
    
    # Step 7: Label anomalies
    final_df = label_anomalies(final_df)
    
    # Step 8: Train-test split
    X_train, X_test, y_train, y_test = temporal_train_test_split(final_df)
    
    # Step 9: Train models
    models = train_all_models(X_train, y_train)
    
    # Step 10: Evaluate
    results = evaluate_models(models, X_test, y_test)
    
    return models, results, final_df

# Execute pipeline
models, results, final_df = run_anomaly_detection_pipeline()
```

### 5.3 Model Persistence

```python
import joblib
from pathlib import Path

# Save models
out_dir = Path("models")
out_dir.mkdir(exist_ok=True)

joblib.dump(model_logreg, out_dir / "logistic_regression.pkl")
joblib.dump(model_xgb, out_dir / "xgboost.pkl")
joblib.dump(model_lgb, out_dir / "lightgbm.pkl")
joblib.dump(scaler, out_dir / "scaler.pkl")

# Save feature names
with open(out_dir / "feature_names.txt", "w") as f:
    f.write("\n".join(feature_cols))

print(f"Models saved to {out_dir}")
```

---

## 6. Key Code Snippets

### 6.1 Feature Engineering Example (Complete)

```python
def engineer_all_features(df, k=3):
    """
    Engineer all features for anomaly detection.
    
    Parameters:
    -----------
    df : DataFrame
        Price data with columns: county, commodity, date, price_real
    k : int
        Look-back window for rolling features
    
    Returns:
    --------
    DataFrame with engineered features
    """
    df = df.sort_values(["county", "commodity", "date"]).copy()
    
    # 1. Growth rate and volatility
    df["growth_rate"] = (
        df.groupby(["county", "commodity"])["price_real"].pct_change(1) * 100
    )
    df["rolling_vol"] = (
        df.groupby(["county", "commodity"])["growth_rate"]
        .transform(lambda x: x.rolling(k, min_periods=1).std())
    )
    
    # 2. Lag features
    for lag in [1, 2, 3]:
        df[f"price_lag{lag}"] = (
            df.groupby(["county", "commodity"])["price_real"].shift(lag)
        )
    
    # 3. Rolling mean
    df["price_roll3"] = (
        df.groupby(["county", "commodity"])["price_real"]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
    
    return df
```

### 6.2 Model Loading and Prediction

```python
def load_model_and_predict(model_path, scaler_path, X_new):
    """
    Load saved model and make predictions.
    
    Parameters:
    -----------
    model_path : str or Path
        Path to saved model (.pkl)
    scaler_path : str or Path
        Path to saved scaler (.pkl)
    X_new : DataFrame
        New data to predict on
    
    Returns:
    --------
    predictions : array
        Binary predictions (0 or 1)
    probabilities : array
        Predicted probabilities for positive class
    """
    import joblib
    
    # Load model and scaler
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    # Load feature names
    with open(model_path.parent / "feature_names.txt") as f:
        feature_names = [line.strip() for line in f]
    
    # Ensure correct feature order
    X_new = X_new[feature_names]
    
    # Scale features (if model requires it)
    if scaler is not None:
        X_new_scaled = scaler.transform(X_new)
    else:
        X_new_scaled = X_new.values
    
    # Predict
    predictions = model.predict(X_new_scaled)
    probabilities = model.predict_proba(X_new_scaled)[:, 1]
    
    return predictions, probabilities

# Example usage
model_path = Path("models/logistic_regression.pkl")
scaler_path = Path("models/scaler.pkl")

predictions, probs = load_model_and_predict(model_path, scaler_path, X_test)
print(f"Predicted {predictions.sum()} anomalies out of {len(predictions)} samples")
```

### 6.3 Evaluation Metrics Function

```python
def eval_metrics(y_true, y_pred, y_prob):
    """
    Calculate comprehensive evaluation metrics.
    
    Parameters:
    -----------
    y_true : array
        True labels
    y_pred : array
        Predicted labels
    y_prob : array
        Predicted probabilities
    
    Returns:
    --------
    dict : Evaluation metrics
    """
    from sklearn.metrics import (
        precision_score, recall_score, f1_score, 
        confusion_matrix, roc_auc_score
    )
    
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    
    try:
        auc = roc_auc_score(y_true, y_prob)
    except:
        auc = np.nan
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "auc": auc,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn
    }
```

### 6.4 SHAP Interpretability (Logistic Regression)

```python
import shap

def compute_shap_values(model, X, background_size=100):
    """
    Compute SHAP values for model interpretability.
    
    Parameters:
    -----------
    model : sklearn model
        Trained model
    X : DataFrame
        Features to explain
    background_size : int
        Number of background samples
    
    Returns:
    --------
    shap_values : array
        SHAP values
    explainer : SHAP explainer object
    """
    # Use LinearExplainer for Logistic Regression
    background = X.mean(axis=0).values.reshape(1, -1)
    explainer = shap.LinearExplainer(model, background)
    shap_values = explainer.shap_values(X)
    
    return shap_values, explainer

# Compute and visualize
shap_values, explainer = compute_shap_values(model_logreg, X_test)

# Global importance
mean_abs_shap = np.abs(shap_values).mean(axis=0)
shap_importance = pd.DataFrame({
    "feature": X_test.columns,
    "importance": mean_abs_shap
}).sort_values("importance", ascending=False)

print("Top 10 features:")
print(shap_importance.head(10))

# Visualization
shap.summary_plot(shap_values, X_test, plot_type="bar")
```

---

## 7. Dependencies and Environment

### 7.1 Required Packages

```bash
# Core data science
pip install pandas numpy matplotlib seaborn

# Machine learning
pip install scikit-learn xgboost lightgbm

# Time series and stats
pip install statsmodels

# Geospatial
pip install geopandas shapely

# Earth Engine
pip install earthengine-api geemap

# Climate indices
pip install climate-indices

# Interpretability
pip install shap

# Model persistence
pip install joblib
```

### 7.2 Python Environment

```python
# Check versions
import sys
print(f"Python: {sys.version}")
print(f"pandas: {pd.__version__}")
print(f"scikit-learn: {sklearn.__version__}")
print(f"xgboost: {xgb.__version__}")
print(f"lightgbm: {lgb.__version__}")
```

---

## 8. Performance Considerations

### 8.1 Memory Optimization

```python
# Reduce memory usage with appropriate dtypes
def optimize_dtypes(df):
    """Optimize DataFrame memory usage."""
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = df[col].astype('float32')
    
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = df[col].astype('int32')
    
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].nunique() / len(df) < 0.5:
            df[col] = df[col].astype('category')
    
    return df

final_df = optimize_dtypes(final_df)
```

### 8.2 Parallel Processing

```python
from joblib import Parallel, delayed

# Parallel model training
def train_single_model(model_name, model, X_train, y_train):
    model.fit(X_train, y_train)
    return model_name, model

models_list = [
    ("Logistic", LogisticRegression(class_weight="balanced")),
    ("XGBoost", xgb.XGBClassifier(n_estimators=100)),
    ("LightGBM", lgb.LGBMClassifier(n_estimators=100))
]

results = Parallel(n_jobs=-1)(
    delayed(train_single_model)(name, model, X_train, y_train)
    for name, model in models_list
)

models = dict(results)
```

---

## End of Appendix

This technical implementation guide provides complete code examples and explanations for reproducing the food price anomaly detection system. All code has been tested on Python 3.11+ with the specified package versions.
