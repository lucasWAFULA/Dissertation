import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

// Proxy /api/* → FastAPI backend
app.use(
  '/api',
  createProxyMiddleware({
    target: API_BASE_URL,
    changeOrigin: true,
    pathRewrite: { '^/api': '' },
    on: {
      error: (err, req, res) => {
        console.error('[Proxy Error]', err.message);
        res.status(502).json({ error: 'Backend unavailable', detail: err.message });
      },
    },
  })
);

// Serve React build
app.use(express.static(join(__dirname, 'dist')));

// SPA fallback — all other routes serve index.html
app.get('*', (req, res) => {
  res.sendFile(join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`✅ Market Price Pulse AI server running on http://localhost:${PORT}`);
  console.log(`📡 Proxying /api/* → ${API_BASE_URL}`);
});
