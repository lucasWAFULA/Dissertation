# Market Price Pulse AI — Frontend

> Production React + Node.js dashboard for the food price anomaly detection platform.

## Tech Stack

| Layer       | Tech                          |
|-------------|-------------------------------|
| UI          | React 18, React Router v6     |
| Charts      | Plotly.js                     |
| HTTP Client | Axios                         |
| Build Tool  | Vite 5                        |
| Server      | Express 4 (production)        |
| Styling     | Vanilla CSS (no Tailwind)     |

## Getting Started

### Development

```bash
npm install
npm run dev          # starts Vite dev server on :5173, proxies /api → :8000
```

### Production Build

```bash
npm run build        # outputs to dist/
npm start            # serves dist/ via Express on :3000
```

### Docker

```bash
docker build -t market-pulse-ai .
docker run -p 3000:3000 -e API_BASE_URL=http://your-backend:8000 market-pulse-ai
```

## Environment Variables

| Variable       | Default                  | Description                  |
|----------------|--------------------------|------------------------------|
| `PORT`         | `3000`                   | Express server port          |
| `API_BASE_URL` | `http://localhost:8000`  | FastAPI backend base URL     |

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js          # Axios API client
│   ├── components/
│   │   ├── Navbar.jsx/.css    # Top navigation + health indicator
│   │   ├── Sidebar.jsx/.css   # Left sidebar with model info + filters
│   │   ├── KpiCard.jsx        # Animated KPI metric card
│   │   ├── AnomalyTable.jsx   # Sortable/filterable anomaly table
│   │   ├── PriceChart.jsx     # Plotly price trend + anomaly markers
│   │   ├── GeoMap.jsx         # Plotly geo bubble map of Kenya
│   │   └── ModelComparePanel.jsx # Bar + pie chart model comparison
│   ├── pages/
│   │   ├── MarketIntelligence.jsx/.css  # Main dashboard
│   │   ├── ForensicAudit.jsx/.css       # CSV upload + scoring
│   │   └── Explainability.jsx/.css      # Model transparency
│   ├── App.jsx                # Router + layout shell
│   ├── index.css              # Global dark-mode design system
│   └── main.jsx               # React entry point
├── index.html
├── vite.config.js
├── server.js                  # Express production server
├── Dockerfile
└── package.json
```

## Pages

### 📊 Market Intelligence (`/`)
- 4 KPI cards with animated counters
- Commodity/county/date filters
- Interactive price trend chart with anomaly markers
- Sortable anomaly alerts table
- Geographic hotspot bubble map (Kenya counties)
- Model intelligence comparison panel

### 🔍 Forensic Audit (`/forensic`)
- Drag-and-drop CSV upload
- Upload module status table
- One-click anomaly detection scoring
- Results: KPIs, anomaly table, model comparison
- Download scored CSV

### 🧠 Explainability (`/explainability`)
- Model metadata cards (LR + XGBoost)
- F1/Recall/Precision/AUC comparison table
- Feature importance horizontal bar chart
- SHAP summary cards
- Ensemble agreement pie chart
