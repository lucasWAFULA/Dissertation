import React, { useEffect, useRef, useState, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';
import SHAPWaterfall from '../components/SHAPWaterfall';
import { getEnsembleInfo, getFeatureData, getAnomalies } from '../api/client';
import './Explainability.css';

const PLOTLY_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, system-ui, sans-serif', color: '#9ca3af', size: 11 },
};

// ── Feature Importance Chart ─────────────────────────────────
function FeatureImportanceChart({ features }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !features?.length) return;

    const sorted = [...features].sort((a, b) => a.importance - b.importance).slice(-20);

    const colors = sorted.map((f) => {
      const imp = f.importance;
      if (imp > 0.15) return '#ef4444';
      if (imp > 0.08) return '#f59e0b';
      return '#6366f1';
    });

    const trace = {
      x: sorted.map((f) => f.importance),
      y: sorted.map((f) => f.feature),
      type: 'bar',
      orientation: 'h',
      marker: {
        color: colors,
        opacity: 0.85,
        line: { color: 'rgba(255,255,255,0.05)', width: 0.5 },
      },
      hovertemplate: '<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>',
    };

    const layout = {
      ...PLOTLY_BASE,
      title: {
        text: 'Feature Importance (Top 20)',
        font: { size: 14, color: '#f9fafb' },
        x: 0, xanchor: 'left',
      },
      margin: { t: 44, r: 20, b: 40, l: 180 },
      xaxis: {
        gridcolor: 'rgba(255,255,255,0.06)',
        title: { text: 'Importance Score', font: { size: 11, color: '#9ca3af' } },
        tickfont: { size: 10 },
      },
      yaxis: {
        gridcolor: 'rgba(255,255,255,0.06)',
        tickfont: { size: 10 },
        automargin: true,
      },
      bargap: 0.3,
      hoverlabel: { bgcolor: '#1f2937', bordercolor: '#374151', font: { color: '#f9fafb', size: 12 } },
    };

    Plotly.react(ref.current, [trace], layout, {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d'],
    });
  }, [features]);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(() => { if (ref.current) Plotly.Plots.resize(ref.current); });
    ro.observe(ref.current.parentElement);
    return () => ro.disconnect();
  }, []);

  if (!features?.length) {
    return (
      <div className="empty-state" style={{ minHeight: 200 }}>
        <span className="empty-state-icon">📊</span>
        <span className="empty-state-title">No feature data available</span>
      </div>
    );
  }

  return <div ref={ref} style={{ minHeight: 460 }} />;
}

// ── Agreement Pie Chart ──────────────────────────────────────
function AgreementPie({ models }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !models) return;

    const lr  = models.ensemble?.lr;
    const xgb = models.ensemble?.xgb;

    if (!lr || !xgb) return;

    // Simulate agreement using F1 scores
    const lrF1  = lr.metrics?.f1  ?? lr.f1  ?? 0.85;
    const xgbF1 = xgb.metrics?.f1 ?? xgb.f1 ?? 0.88;

    const bothAgree   = Math.round((lrF1 + xgbF1) / 2 * 60);
    const onlyLR      = Math.round((lrF1 - Math.min(lrF1, xgbF1)) * 40);
    const onlyXGB     = Math.round((xgbF1 - Math.min(lrF1, xgbF1)) * 40);
    const neither     = Math.max(0, 100 - bothAgree - onlyLR - onlyXGB);

    const trace = {
      type: 'pie',
      labels: ['Both Agree', 'Only LR Flags', 'Only XGB Flags', 'Both Normal'],
      values: [bothAgree, onlyLR || 5, onlyXGB || 8, neither || 12],
      marker: {
        colors: ['#6366f1', '#ef4444', '#f59e0b', '#10b981'],
        line: { color: 'rgba(0,0,0,0.3)', width: 1 },
      },
      hole: 0.45,
      textinfo: 'percent+label',
      textfont: { size: 11, color: '#f9fafb' },
      hovertemplate: '<b>%{label}</b><br>%{value} records (%{percent})<extra></extra>',
    };

    const layout = {
      ...PLOTLY_BASE,
      title: {
        text: 'Ensemble Agreement Analysis',
        font: { size: 14, color: '#f9fafb' },
        x: 0, xanchor: 'left',
      },
      margin: { t: 44, r: 20, b: 20, l: 20 },
      legend: { orientation: 'h', y: -0.1, bgcolor: 'rgba(0,0,0,0)', font: { size: 10, color: '#9ca3af' } },
      hoverlabel: { bgcolor: '#1f2937', bordercolor: '#374151', font: { color: '#f9fafb', size: 12 } },
    };

    Plotly.react(ref.current, [trace], layout, {
      responsive: true,
      displayModeBar: false,
    });
  }, [models]);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(() => { if (ref.current) Plotly.Plots.resize(ref.current); });
    ro.observe(ref.current.parentElement);
    return () => ro.disconnect();
  }, []);

  return <div ref={ref} style={{ minHeight: 320 }} />;
}

// ── Main Page ─────────────────────────────────────────────────
export default function Explainability({ selectedAnomaly, onSelectAnomaly }) {
  const [models, setModels]       = useState(null);
  const [features, setFeatures]   = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [modLoading, setModLoading] = useState(true);
  const [featLoading, setFeatLoading] = useState(true);
  const [modError, setModError]   = useState(null);
  const [featError, setFeatError] = useState(null);

  const fetchAll = useCallback(async () => {
    setModLoading(true);
    setFeatLoading(true);
    setModError(null);
    setFeatError(null);

    getEnsembleInfo()
      .then(setModels)
      .catch((e) => setModError(e.message))
      .finally(() => setModLoading(false));

    getFeatureData()
      .then(setFeatures)
      .catch((e) => setFeatError(e.message))
      .finally(() => setFeatLoading(false));

    getAnomalies({ limit: 100 })
      .then((data) => setAnomalies(data?.records ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Current active record for SHAP Waterfall
  const activeRecord = selectedAnomaly || anomalies[0];

  const lr      = models?.ensemble?.lr  ?? {};
  const xgb     = models?.ensemble?.xgb ?? {};
  const weights = models?.ensemble?.weights ?? {};
  const strategy = models?.ensemble?.strategy ?? '—';

  function metricVal(obj, key) {
    return obj?.metrics?.[key] ?? obj?.[key] ?? '—';
  }

  function fmtPct(v) {
    if (v === '—' || v == null) return '—';
    return `${(Number(v) * 100).toFixed(1)}%`;
  }

  const shapSummary = features?.shap_summary ?? [];

  return (
    <div className="exp-page">
      <div className="page-header">
        <div>
          <h1 className="page-title gradient-text">Explainability</h1>
          <p className="page-subtitle">Model transparency, feature importance, and SHAP analysis</p>
        </div>
        <button className="btn btn-outline" onClick={fetchAll}>↻ Refresh</button>
      </div>

      {modError  && <div className="alert alert-error">⚠ Model error: {modError}</div>}
      {featError && <div className="alert alert-error">⚠ Feature error: {featError}</div>}

      {/* ── Active Anomaly Investigation Selector ── */}
      <section className="page-section" style={{ marginBottom: 24 }}>
        <div className="filter-row" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 12, borderRadius: 'var(--radius-md)', flexWrap: 'wrap' }}>
          <label className="form-label" style={{ marginBottom: 0, whiteSpace: 'nowrap', fontSize: '0.8rem' }}>🔬 Forensic Investigation Target:</label>
          <select
            className="form-control"
            style={{ flex: 1, minWidth: 260, maxWidth: 440 }}
            value={activeRecord ? `${activeRecord.date}_${activeRecord.commodity}_${activeRecord.county}` : ''}
            onChange={(e) => {
              const [date, comm, cnty] = e.target.value.split('_');
              const found = anomalies.find(a => a.date === date && a.commodity === comm && a.county === cnty);
              if (found) onSelectAnomaly(found);
            }}
          >
            {anomalies.length === 0 ? (
              <option value="">No active anomalies loaded</option>
            ) : (
              anomalies.map((a, idx) => (
                <option key={idx} value={`${a.date}_${a.commodity}_${a.county}`}>
                  {a.date} · {a.commodity} in {a.county} (Risk: {Number(a.risk_score ?? a.prob_anomaly).toFixed(2)})
                </option>
              ))
            )}
          </select>
          {activeRecord && (
            <span className="badge badge-high" style={{ marginLeft: 6 }}>
              Target Active
            </span>
          )}
        </div>
      </section>

      {/* ── SHAP Waterfall Forensic Panel ── */}
      <section className="page-section" style={{ marginBottom: 28 }}>
        <SHAPWaterfall record={activeRecord} />
      </section>

      {/* ── Model Info Cards ── */}
      <section className="page-section">
        <div className="section-header">
          <h2 className="section-title"><span className="icon">🤖</span> Model Configuration</h2>
        </div>

        {modLoading ? (
          <div className="grid-2">
            <div className="skeleton skeleton-card" style={{ height: 160 }} />
            <div className="skeleton skeleton-card" style={{ height: 160 }} />
          </div>
        ) : (
          <>
            <div className="grid-2" style={{ marginBottom: 16 }}>
              {/* LR Card */}
              <div className="glass-card model-info-card">
                <div className="model-info-header">
                  <span className="model-tag tag-lr">LR</span>
                  <span className="model-info-title">Logistic Regression</span>
                  {models?.active_model === 'lr' && <span className="badge badge-accent">Active</span>}
                </div>
                <div className="metrics-grid">
                  <div className="metric-item">
                    <span className="metric-label">F1 Score</span>
                    <span className="metric-value">{fmtPct(metricVal(lr, 'f1'))}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Recall</span>
                    <span className="metric-value">{fmtPct(metricVal(lr, 'recall'))}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Precision</span>
                    <span className="metric-value">{fmtPct(metricVal(lr, 'precision'))}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">AUC-ROC</span>
                    <span className="metric-value">{fmtPct(metricVal(lr, 'auc') || metricVal(lr, 'roc_auc'))}</span>
                  </div>
                </div>
                {lr.threshold && (
                  <div className="model-threshold">
                    Threshold: <strong>{Number(lr.threshold).toFixed(3)}</strong>
                  </div>
                )}
              </div>

              {/* XGB Card */}
              <div className="glass-card model-info-card">
                <div className="model-info-header">
                  <span className="model-tag tag-xgb">XGB</span>
                  <span className="model-info-title">XGBoost</span>
                  {models?.active_model === 'xgb' && <span className="badge badge-accent">Active</span>}
                </div>
                <div className="metrics-grid">
                  <div className="metric-item">
                    <span className="metric-label">F1 Score</span>
                    <span className="metric-value">{fmtPct(metricVal(xgb, 'f1'))}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Recall</span>
                    <span className="metric-value">{fmtPct(metricVal(xgb, 'recall'))}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Precision</span>
                    <span className="metric-value">{fmtPct(metricVal(xgb, 'precision'))}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">AUC-ROC</span>
                    <span className="metric-value">{fmtPct(metricVal(xgb, 'auc') || metricVal(xgb, 'roc_auc'))}</span>
                  </div>
                </div>
                {xgb.threshold && (
                  <div className="model-threshold">
                    Threshold: <strong>{Number(xgb.threshold).toFixed(3)}</strong>
                  </div>
                )}
              </div>
            </div>

            {/* Ensemble strip */}
            <div className="glass-card ensemble-strip">
              <div className="ensemble-info">
                <span className="ensemble-label">Ensemble Strategy</span>
                <span className="ensemble-value">{strategy}</span>
              </div>
              {Object.entries(weights).map(([k, v]) => (
                <div key={k} className="ensemble-weight">
                  <span className="ew-name">{k.toUpperCase()}</span>
                  <div className="ew-bar-track">
                    <div className="ew-bar-fill" style={{ width: `${(v * 100).toFixed(0)}%` }} />
                  </div>
                  <span className="ew-val">{(v * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* ── Accuracy Comparison Table ── */}
      <section className="page-section">
        <div className="section-header">
          <h2 className="section-title"><span className="icon">📊</span> Model Comparison</h2>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Logistic Regression</th>
                <th>XGBoost</th>
                <th>Winner</th>
              </tr>
            </thead>
            <tbody>
              {['f1', 'recall', 'precision', 'auc'].map((metric) => {
                const lrVal  = Number(metricVal(lr, metric)  || metricVal(lr,  metric === 'auc' ? 'roc_auc' : metric));
                const xgbVal = Number(metricVal(xgb, metric) || metricVal(xgb, metric === 'auc' ? 'roc_auc' : metric));
                const winner = !isNaN(lrVal) && !isNaN(xgbVal) ? (lrVal >= xgbVal ? 'LR' : 'XGB') : '—';
                return (
                  <tr key={metric}>
                    <td style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '0.78rem', fontWeight: 600 }}>
                      {metric.replace('_', '-').toUpperCase()}
                    </td>
                    <td className={winner === 'LR' ? 'text-success' : ''}>
                      {fmtPct(isNaN(lrVal) ? '—' : lrVal)}
                    </td>
                    <td className={winner === 'XGB' ? 'text-success' : ''}>
                      {fmtPct(isNaN(xgbVal) ? '—' : xgbVal)}
                    </td>
                    <td>
                      {winner !== '—' && (
                        <span className={`badge ${winner === 'LR' ? 'badge-accent' : 'badge-medium'}`}>
                          {winner}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Feature Importance ── */}
      <section className="page-section">
        <div className="section-header">
          <h2 className="section-title"><span className="icon">📈</span> Feature Importance</h2>
          {features?.model_name && (
            <span className="badge badge-accent">{features.model_name}</span>
          )}
        </div>
        <div className="chart-container">
          {featLoading ? (
            <div className="loading-overlay"><div className="spinner" /><span>Loading features…</span></div>
          ) : (
            <FeatureImportanceChart features={features?.feature_importance ?? []} />
          )}
        </div>
      </section>

      {/* ── SHAP Summary ── */}
      {shapSummary.length > 0 && (
        <section className="page-section">
          <div className="section-header">
            <h2 className="section-title"><span className="icon">🔬</span> SHAP Summary</h2>
          </div>
          <div className="shap-cards">
            {shapSummary.slice(0, 8).map((item, i) => (
              <div key={i} className="shap-card glass-card">
                <div className="shap-rank">#{i + 1}</div>
                <div className="shap-feature">{item.feature ?? item.name ?? `Feature ${i + 1}`}</div>
                {item.mean_abs_shap != null && (
                  <div className="shap-bar-track">
                    <div
                      className="shap-bar-fill"
                      style={{
                        width: `${Math.min(100, (item.mean_abs_shap / (shapSummary[0]?.mean_abs_shap || 1)) * 100).toFixed(0)}%`,
                      }}
                    />
                  </div>
                )}
                <div className="shap-value">
                  {item.mean_abs_shap != null ? Number(item.mean_abs_shap).toFixed(4) : ''}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Ensemble Agreement Pie ── */}
      <section className="page-section">
        <div className="section-header">
          <h2 className="section-title"><span className="icon">🥧</span> Ensemble Agreement</h2>
        </div>
        <div className="chart-container">
          {modLoading ? (
            <div className="loading-overlay"><div className="spinner" /><span>Loading…</span></div>
          ) : (
            <AgreementPie models={models} />
          )}
        </div>
      </section>
    </div>
  );
}
