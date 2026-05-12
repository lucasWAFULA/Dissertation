from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
# Full-bleed background for Streamlit main (right) panel — commit this file for Cloud deploy
MAIN_PANEL_BACKGROUND_IMAGE = BASE_DIR / "wp1950213.png"
OUTPUTS_DIR = BASE_DIR / "outputs"
STREAMLIT_DIR = BASE_DIR / ".streamlit"

WFP_PATH = BASE_DIR / "wfp_food_prices_ken (1).csv"
FPMA_PATH = BASE_DIR / "FPMA_international_price_data.csv"
INFLATION_PATH = BASE_DIR / "Inflation Rates.csv"
COUNTIES_SHP_PATH = BASE_DIR / "kenya_counties.shp"
KENYA_ADM1_GEOJSON_PATH = BASE_DIR / "geoBoundaries-KEN-ADM1.geojson"
KENYA_ADM0_GEOJSON_PATH = BASE_DIR / "geoBoundaries-KEN-ADM0.geojson"

DEFAULT_FEATURE_NAMES = [
    "price_real",
    "growth_rate",
    "rolling_vol",
    "NDVI_anomaly",
    "rain_mm",
    "SPI3",
    "SPI6",
    "price_lag1",
    "price_lag2",
    "price_lag3",
    "price_roll3",
    "NDVI_lag1",
    "SPI3_lag1",
    "fpma_maize",
    "inflation_pct",
]

MODEL_CANDIDATES = [
    "best_model.joblib",
    "best_model.pkl",
    "model.joblib",
    "model.pkl",
    "xgboost_model.joblib",
    "xgboost_model.pkl",
    "model_xgb_anomaly.joblib",
    "model_xgb_anomaly.pkl",
]

SCALER_CANDIDATES = [
    "scaler.joblib",
    "scaler.pkl",
    "standard_scaler.joblib",
    "standard_scaler.pkl",
]

THRESHOLD_CANDIDATES = [
    "best_threshold.joblib",
    "best_threshold.pkl",
]

# Database Configuration
DATABASE_URL = "sqlite:////app/market_intelligence.db"

# API Endpoints (WFP VAM)
WFP_API_URL = "https://api.vam.wfp.org/8.1.0/Public/Price"

