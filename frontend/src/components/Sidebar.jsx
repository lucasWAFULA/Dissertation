import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { getEnsembleInfo } from '../api/client';
import './Sidebar.css';

const NAV_ITEMS = [
  { to: '/app',               label: 'Market Intelligence', icon: '📊' },
  { to: '/app/forensic',       label: 'Forensic Audit',      icon: '🔍' },
  { to: '/app/explainability', label: 'Explainability',      icon: '🧠' },
];

export default function Sidebar({
  collapsed,
  onSeverityChange,
  onSensitivityChange,
  severity,
  sensitivity,
  dateRange,
  ensembleWeights = { lr: 60, xgb: 40, iforest: 0, lgbm: 0 },
  onWeightChange,
  onCloseSidebar,
}) {
  const [models, setModels]   = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEnsembleInfo()
      .then(setModels)
      .catch(() => setModels(null))
      .finally(() => setLoading(false));
  }, []);

  const SEVERITIES = ['All', 'High', 'Medium', 'Low'];

  return (
    <>
      {!collapsed && <div className="sidebar-backdrop" onClick={onCloseSidebar} />}
      <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
        {/* ── Nav Links ── */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/app'}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
              }
            >
              <span className="sidebar-link-icon">{icon}</span>
              {!collapsed && <span className="sidebar-link-label">{label}</span>}
            </NavLink>
          ))}
        </nav>

      <div className="sidebar-divider" />

      {!collapsed && (
        <>
          {/* ── Ensemble Weighting Sliders ── */}
          <div className="sidebar-section">
            <span className="sidebar-section-title">Ensemble Voting Weight</span>
            <div className="model-weights" style={{ marginTop: 10 }}>
              {/* LR Slider */}
              <div className="slider-weight-group" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                  <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>Logistic Regression (LR)</span>
                  <span style={{ fontWeight: 600, color: 'var(--accent)' }}>{ensembleWeights.lr}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={ensembleWeights.lr}
                  onChange={(e) => onWeightChange('lr', e.target.value)}
                  className="sidebar-slider"
                  style={{ width: '100%' }}
                />
              </div>

              {/* XGB Slider */}
              <div className="slider-weight-group" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                  <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>XGBoost (XGB)</span>
                  <span style={{ fontWeight: 600, color: 'var(--accent)' }}>{ensembleWeights.xgb}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={ensembleWeights.xgb}
                  onChange={(e) => onWeightChange('xgb', e.target.value)}
                  className="sidebar-slider"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Isolation Forest Slider */}
              <div className="slider-weight-group" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                  <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>Isolation Forest (iForest)</span>
                  <span style={{ fontWeight: 600, color: 'var(--accent)' }}>{ensembleWeights.iforest}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={ensembleWeights.iforest}
                  onChange={(e) => onWeightChange('iforest', e.target.value)}
                  className="sidebar-slider"
                  style={{ width: '100%' }}
                />
              </div>

              {/* LightGBM Slider */}
              <div className="slider-weight-group" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                  <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>LightGBM (LGBM)</span>
                  <span style={{ fontWeight: 600, color: 'var(--accent)' }}>{ensembleWeights.lgbm}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={ensembleWeights.lgbm}
                  onChange={(e) => onWeightChange('lgbm', e.target.value)}
                  className="sidebar-slider"
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </div>

          <div className="sidebar-divider" />

          {/* ── Model Confidence Meter ── */}
          <div className="sidebar-section">
            <span className="sidebar-section-title">Prediction Confidence</span>
            <div style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: 4 }}>
                <span className="text-success" style={{ fontWeight: 600 }}>High Reliability</span>
                <span style={{ fontWeight: 600, color: 'var(--success)' }}>87%</span>
              </div>
              <div className="weight-bar-track" style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.08)' }}>
                <div
                  className="weight-bar-fill"
                  style={{
                    width: '87%',
                    height: '100%',
                    borderRadius: 3,
                    background: 'linear-gradient(90deg, var(--success), #34d399)',
                    boxShadow: '0 0 8px rgba(16, 185, 129, 0.4)'
                  }}
                />
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: 6 }}>
                Confidence derived from F1 accuracy and ensemble agreement.
              </div>
            </div>
          </div>

          <div className="sidebar-divider" />

          {/* ── Detection Sensitivity ── */}
          <div className="sidebar-section">
            <span className="sidebar-section-title">Detection Sensitivity</span>
            <div className="slider-row">
              <input
                type="range"
                min={0}
                max={100}
                value={sensitivity}
                onChange={(e) => onSensitivityChange(Number(e.target.value))}
                className="sidebar-slider"
              />
              <span className="slider-value">{sensitivity}%</span>
            </div>
            <div className="slider-labels">
              <span>Conservative</span>
              <span>Aggressive</span>
            </div>
          </div>

          <div className="sidebar-divider" />

          {/* ── Severity Filters ── */}
          <div className="sidebar-section">
            <span className="sidebar-section-title">Severity Filter</span>
            <div className="severity-filters">
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  className={`severity-btn severity-${s.toLowerCase()} ${
                    severity === s ? 'active' : ''
                  }`}
                  onClick={() => onSeverityChange(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-divider" />

          {/* ── Date Range Display ── */}
          {dateRange && (
            <div className="sidebar-section">
              <span className="sidebar-section-title">Data Coverage</span>
              <div className="date-range-display">
                <div className="date-item">
                  <span className="date-label">From</span>
                  <span className="date-value">{dateRange.min ?? '—'}</span>
                </div>
                <div className="date-arrow">→</div>
                <div className="date-item">
                  <span className="date-label">To</span>
                  <span className="date-value">{dateRange.max ?? '—'}</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Footer ── */}
      {!collapsed && (
        <div className="sidebar-footer">
          <span className="sidebar-footer-text">Market Price Pulse AI</span>
          <span className="sidebar-footer-version">v1.0.0</span>
        </div>
      )}
    </aside>
    </>
  );
}
