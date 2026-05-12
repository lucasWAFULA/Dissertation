# Food Price Anomaly Detection Streamlit App

This project packages the notebook-based food price anomaly detection workflow into a Streamlit dashboard that can run locally and on Streamlit Community Cloud.

## What the app does

- loads historical WFP food price data, FPMA international maize prices, and KNBS inflation data
- rebuilds the monthly feature table used by the anomaly detection workflow
- loads the saved model threshold and feature ordering from `outputs/`
- scores anomalies when a serialized model artifact is present
- falls back to the notebook-derived anomaly label if the model file is not yet available

## Project structure

- `app.py`: Streamlit entry point
- `api/`: FastAPI service (`api.main:app`) for scalable REST scoring
- `src/data_loader.py`: loads raw datasets and deployment metadata
- `src/preprocessing.py`: data cleaning, monthly aggregation, CPI adjustment, lag features, and anomaly labels
- `src/inference.py`: artifact loading, feature alignment, thresholding, and fallback scoring
- `src/visuals.py`: charts and alert-table helpers
- `.streamlit/config.toml`: Streamlit runtime configuration

## Local run

1. Create or activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
streamlit run app.py
```

## Required deployment artifacts

The dashboard already reads:

- `outputs/best_model_meta.json`
- `outputs/feature_names.csv`
- `outputs/optimal_thresholds.csv`
- `outputs/optimized_test_metrics.csv`

For full ML scoring, add at least one serialized model artifact to `outputs/` using one of these supported names:

- `best_model.joblib`
- `best_model.pkl`
- `model.joblib`
- `model.pkl`
- `xgboost_model.joblib`
- `xgboost_model.pkl`

If the selected model requires scaling, also add a scaler artifact such as `scaler.joblib`.

## Streamlit Community Cloud deployment

1. Put the project in a GitHub repository.
2. Ensure `app.py`, `requirements.txt`, `.streamlit/config.toml`, the raw CSV data files, and the `outputs/` deployment artifacts are committed.
3. In Streamlit Community Cloud, create a new app and point it to:
   - repository: your project repository
   - branch: your deployment branch
   - main file path: `app.py`
4. Deploy the app.

## FastAPI (scalable scoring API)

A separate **HTTP API** reuses the same preprocessing and model as the dashboard. Use it for programmatic scoring, microservices, or horizontal scaling (multiple Uvicorn workers or containers behind a load balancer).

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

- Docs: `http://127.0.0.1:8000/docs`
- Details: [docs/API_DEPLOYMENT.md](docs/API_DEPLOYMENT.md)
- Docker: `docker build -f Dockerfile.api -t anomaly-api .`
- **Streamlit → API:** Anomaly Detection page → check **Score via FastAPI** and set the base URL (or `STREAMLIT_SCORING_API_URL` / `SCORING_API_URL` in secrets).

## Notes

- The current implementation does not require Earth Engine, notebook execution, or shapefile processing at runtime.
- If no serialized model artifact is present, the UI stays available and clearly reports that it is running in rule-based fallback mode.

