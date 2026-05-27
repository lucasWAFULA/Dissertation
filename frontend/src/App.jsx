import React, { useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

// Auth
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute   from './components/ProtectedRoute';
import { useAuth }      from './contexts/AuthContext';

// Public pages
import Landing from './pages/Landing';
import Login   from './pages/Login';

// App shell components
import Navbar  from './components/Navbar';
import Sidebar from './components/Sidebar';

// Protected pages
import MarketIntelligence from './pages/MarketIntelligence';
import ForensicAudit      from './pages/ForensicAudit';
import Explainability     from './pages/Explainability';

// ── Not-found page ─────────────────────────────────────────────────────────────
const NotFound = () => (
  <div className="empty-state" style={{ minHeight: '60vh' }}>
    <span className="empty-state-icon">🔍</span>
    <span className="empty-state-title">Page not found</span>
    <span className="empty-state-desc">The page you're looking for doesn't exist.</span>
  </div>
);

// ── App shell (Navbar + Sidebar + content) — only for /app/* routes ────────────
const AppShell = () => {
  const { user } = useAuth();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.innerWidth <= 768);
  const [severity, setSeverity]                 = useState('All');
  const [sensitivity, setSensitivity]           = useState(50);
  const [selectedAnomaly, setSelectedAnomaly]   = useState(null);

  const [ensembleWeights, setEnsembleWeights] = useState({
    lr:      60,
    xgb:     40,
    iforest: 0,
    lgbm:    0,
  });

  const toggleSidebar = () => setSidebarCollapsed((c) => !c);
  const closeSidebar = () => setSidebarCollapsed(true);

  const handleWeightChange = (key, val) => {
    const newVal    = Math.min(100, Math.max(0, Number(val)));
    const otherKeys = Object.keys(ensembleWeights).filter((k) => k !== key);
    const otherSum  = otherKeys.reduce((s, k) => s + ensembleWeights[k], 0);

    let newWeights    = { ...ensembleWeights };
    newWeights[key]   = newVal;

    if (otherSum === 0) {
      const shared = (100 - newVal) / otherKeys.length;
      otherKeys.forEach((k) => { newWeights[k] = Math.round(shared); });
    } else {
      const scale = (100 - newVal) / otherSum;
      otherKeys.forEach((k) => { newWeights[k] = Math.round(ensembleWeights[k] * scale); });
    }

    // Fix rounding drift
    const currentSum = Object.values(newWeights).reduce((s, v) => s + v, 0);
    if (currentSum !== 100) {
      const diff        = 100 - currentSum;
      const keyToAdjust = key !== 'lr' ? 'lr' : 'xgb';
      newWeights[keyToAdjust] = Math.max(0, newWeights[keyToAdjust] + diff);
    }

    setEnsembleWeights(newWeights);
  };

  return (
    <div className="app-shell">
      <Navbar onToggleSidebar={toggleSidebar} />

      <div className="app-body">
        <Sidebar
          collapsed={sidebarCollapsed}
          severity={severity}
          sensitivity={sensitivity}
          ensembleWeights={ensembleWeights}
          onSeverityChange={setSeverity}
          onSensitivityChange={setSensitivity}
          onWeightChange={handleWeightChange}
          onCloseSidebar={closeSidebar}
        />

        <main className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
          <Routes>
            {/* /app → Market Intelligence */}
            <Route
              index
              element={
                <MarketIntelligence
                  severity={severity}
                  sensitivity={sensitivity}
                  ensembleWeights={ensembleWeights}
                  onSelectAnomaly={setSelectedAnomaly}
                />
              }
            />
            {/* /app/forensic */}
            <Route
              path="forensic"
              element={<ForensicAudit ensembleWeights={ensembleWeights} />}
            />
            {/* /app/explainability */}
            <Route
              path="explainability"
              element={
                <Explainability
                  ensembleWeights={ensembleWeights}
                  selectedAnomaly={selectedAnomaly}
                  onSelectAnomaly={setSelectedAnomaly}
                />
              }
            />
            {/* Catch-all inside /app */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

// ── Root router (no auth dependency — safe to render before AuthProvider) ──────
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public — full-screen pages (no app shell) */}
        <Route path="/"      element={<Landing />} />
        <Route path="/login" element={<Login   />} />

        {/* Redirect bare paths to protected /app/ versions */}
        <Route path="/forensic" element={<Navigate to="/app/forensic" replace />} />
        <Route path="/explainability" element={<Navigate to="/app/explainability" replace />} />

        {/* Protected — app shell + nested routes */}
        <Route
          path="/app/*"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        />

        {/* Global 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AuthProvider>
  );
}
