import axios from 'axios';

// ── Axios Instance ──────────────────────────────────────────
const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request Interceptor ─────────────────────────────────────
client.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// ── Response Interceptor ────────────────────────────────────
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.error ||
      error?.message ||
      'Unknown API error';
    const status = error?.response?.status;
    const enhanced = new Error(msg);
    enhanced.status = status;
    enhanced.original = error;
    return Promise.reject(enhanced);
  }
);

// ── Health & Model ──────────────────────────────────────────
export const getHealth = () => client.get('/health');

export const getModelInfo = () => client.get('/v1/model');

export const getEnsembleInfo = () => client.get('/v1/models');

// ── Dashboard Data ──────────────────────────────────────────
export const getDashboardData = () => client.get('/v1/data/dashboard');

// ── Prices ─────────────────────────────────────────────────
export const getPrices = (params = {}) => {
  const query = {};
  if (params.commodity) query.commodity = params.commodity;
  if (params.county)    query.county    = params.county;
  if (params.from_date) query.from_date  = params.from_date;
  return client.get('/v1/data/prices', { params: query });
};

// ── Anomalies ───────────────────────────────────────────────
export const getAnomalies = (params = {}) => {
  const query = {};
  if (params.severity) query.severity = params.severity;
  if (params.limit)    query.limit    = params.limit;
  return client.get('/v1/data/anomalies', { params: query });
};

// ── Geo Data ────────────────────────────────────────────────
export const getGeoData = () => client.get('/v1/data/geo');

// ── Feature Importance / SHAP ───────────────────────────────
export const getFeatureData = () => client.get('/v1/data/features');

// ── Score CSV ───────────────────────────────────────────────
export const scoreCsv = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return client.post('/v1/score/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
};

export default client;
