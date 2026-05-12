# FastAPI scoring service (scalable deployment)

The **Food Price Anomaly API** exposes the same scoring pipeline as the Streamlit app over HTTP. Run **multiple Uvicorn workers** or **multiple containers** behind a load balancer to scale throughput.

## Run locally

From the project root (where `outputs/`, `data/`, and `src/` live):

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Open **http://127.0.0.1:8000/docs** for interactive OpenAPI docs.

### Multiple workers (single machine)

Each worker loads the model and reference CSVs into memory once at startup:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Use **2–4 workers** per CPU core for mixed I/O + inference; tune under load.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness; `ready` indicates FPMA/inflation/model pipeline loaded |
| GET | `/v1/model` | Deployed model name, threshold, feature count |
| POST | `/v1/score` | JSON body: `{ "records": [ { ... WFP columns ... }, ... ] }` |
| POST | `/v1/score/csv` | `multipart/form-data` file field with CSV (same columns as WFP upload) |

Required CSV/JSON columns match Streamlit ingestion:  
`date`, `admin1`, `admin2`, `market`, `market_id`, `latitude`, `longitude`, `category`, `commodity`, `commodity_id`, `unit`, `priceflag`, `pricetype`, `currency`, `price`, `usdprice`.

## Streamlit UI → API

On **Anomaly Detection**, enable **Score via FastAPI** and set the API base URL. You can pre-fill the URL with:

- Environment: `STREAMLIT_SCORING_API_URL=http://your-api:8000`
- Or Streamlit secrets: `SCORING_API_URL = "https://..."` in `.streamlit/secrets.toml`

The UI sends harmonized market rows to `POST /v1/score` and merges shock/infrastructure locally.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_MAX_SCORE_ROWS` | `50000` | Max rows per `/v1/score` or `/v1/score/csv` request |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins (e.g. `https://app.example.com`) |
| `STREAMLIT_SCORING_API_URL` | (empty) | Default API base URL in the Streamlit Anomaly page |

Artifact and data paths follow `src.config` (`OUTPUTS_DIR`, `FPMA_PATH`, `INFLATION_PATH`, etc.). Override by mounting files or setting env if you extend config.

## Docker (example)

```bash
docker build -f Dockerfile.api -t anomaly-api .
docker run -p 8000:8000 anomaly-api
```

Mount `outputs/` or full project dir if artifacts live outside the image.

## Architecture notes

- **Stateless requests**: no server-side session; safe to scale horizontally.
- **Heavy startup**: first request after boot is fast; cold starts load joblib + pandas merges.
- **Streamlit**: can stay on Community Cloud; point a separate API deployment (Railway, Fly.io, ECS, etc.) and call `/v1/score` from Python `httpx` if you want UI + API split.
