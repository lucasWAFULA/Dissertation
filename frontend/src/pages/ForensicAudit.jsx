import React, { useState, useRef, useCallback } from 'react';
import KpiCard from '../components/KpiCard';
import AnomalyTable from '../components/AnomalyTable';
import PriceChart from '../components/PriceChart';
import ModelComparePanel from '../components/ModelComparePanel';
import { scoreCsv } from '../api/client';
import './ForensicAudit.css';

const MODULE_CONFIG = [
  { key: 'market_prices', label: 'Market Prices',   required: true,  icon: '🌾', desc: 'Primary price data with commodity, county, date, price columns' },
  { key: 'economic',      label: 'Economic Data',    required: false, icon: '💹', desc: 'GDP, inflation, exchange rate indicators' },
  { key: 'global',        label: 'Global Markets',   required: false, icon: '🌍', desc: 'International commodity price benchmarks' },
  { key: 'climate',       label: 'Climate Data',     required: false, icon: '🌦', desc: 'Rainfall, temperature, drought indices' },
  { key: 'shocks',        label: 'Shock Events',     required: false, icon: '⚡', desc: 'Conflict, supply chain disruption events' },
  { key: 'infrastructure',label: 'Infrastructure',   required: false, icon: '🏗', desc: 'Road quality, market access indicators' },
];

function downloadScoredCsv(results) {
  if (!results?.length) return;
  const keys = Object.keys(results[0]);
  const header = keys.join(',');
  const rows = results.map((r) =>
    keys.map((k) => {
      const v = r[k];
      if (v === null || v === undefined) return '';
      const s = String(v);
      return s.includes(',') ? `"${s}"` : s;
    }).join(',')
  );
  const csv = [header, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `scored_anomalies_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ForensicAudit() {
  const [file, setFile]           = useState(null);
  const [dragging, setDragging]   = useState(false);
  const [running, setRunning]     = useState(false);
  const [error, setError]         = useState(null);
  const [results, setResults]     = useState(null);
  const [uploadPct, setUploadPct] = useState(0);
  const fileInputRef              = useRef(null);

  // ── Drag & Drop ──────────────────────────────────────────────
  const onDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);
  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.name.endsWith('.csv')) {
      setFile(dropped);
      setError(null);
      setResults(null);
    } else {
      setError('Only CSV files are supported.');
    }
  };

  const onFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setError(null);
      setResults(null);
    }
  };

  // ── Run Detection ────────────────────────────────────────────
  const runDetection = useCallback(async () => {
    if (!file) return;
    setRunning(true);
    setError(null);
    setUploadPct(0);

    try {
      const data = await scoreCsv(file);
      setResults(data);
    } catch (err) {
      setError(err.message || 'Scoring failed. Please check your CSV format.');
    } finally {
      setRunning(false);
      setUploadPct(100);
    }
  }, [file]);

  // ── Derived Stats ─────────────────────────────────────────────
  const anomalyRecords = results?.results?.filter((r) => r.pred_anomaly) ?? [];
  const totalScored    = results?.n_scored_rows ?? 0;
  const highCount      = results?.results?.filter((r) => r.severity === 'High').length ?? 0;
  const avgRisk        = results?.results?.length
    ? (results.results.reduce((s, r) => s + (r.risk_score || r.prob_ensemble || 0), 0) / results.results.length).toFixed(3)
    : null;

  const firstCommodity = results?.results?.[0]?.commodity ?? '';

  return (
    <div className="fa-page">
      <div className="page-header">
        <div>
          <h1 className="page-title gradient-text">Forensic Audit</h1>
          <p className="page-subtitle">Upload market data CSV for instant anomaly detection scoring</p>
        </div>
      </div>

      {/* ── Upload Area ── */}
      <section className="page-section">
        <div
          className={`upload-dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => !file && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={onFileChange}
          />
          {file ? (
            <div className="upload-file-info">
              <span className="upload-icon-large">📄</span>
              <div>
                <div className="upload-filename">{file.name}</div>
                <div className="upload-filesize">
                  {(file.size / 1024).toFixed(1)} KB
                </div>
              </div>
              <button
                className="btn btn-ghost"
                onClick={(e) => { e.stopPropagation(); setFile(null); setResults(null); setError(null); }}
              >
                ✕ Remove
              </button>
            </div>
          ) : (
            <div className="upload-prompt">
              <span className="upload-icon-large">📤</span>
              <span className="upload-main-text">Drop your CSV here</span>
              <span className="upload-sub-text">or click to browse · CSV only</span>
              <div className="upload-format-hint">
                Required columns: <code>commodity</code>, <code>county</code>, <code>date</code>, <code>price_real</code>
              </div>
            </div>
          )}
        </div>

        {error && <div className="alert alert-error" style={{ marginTop: 12 }}>⚠ {error}</div>}
      </section>

      {/* ── Module Status Table ── */}
      <section className="page-section">
        <div className="section-header">
          <h2 className="section-title"><span className="icon">📋</span> Upload Module Status</h2>
        </div>
        <div className="module-grid">
          {MODULE_CONFIG.map((mod) => {
            const isUploaded = mod.key === 'market_prices' && !!file;
            const status = isUploaded ? 'ready' : mod.required ? 'required' : 'optional';
            return (
              <div key={mod.key} className={`module-card module-${status}`}>
                <div className="module-header">
                  <span className="module-icon">{mod.icon}</span>
                  <span className="module-name">{mod.label}</span>
                  <span className={`module-status-badge status-${status}`}>
                    {isUploaded ? '✓ Loaded' : mod.required ? 'Required' : 'Optional'}
                  </span>
                </div>
                <div className="module-desc">{mod.desc}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Run Button ── */}
      <section className="page-section" style={{ textAlign: 'center' }}>
        <button
          className="btn btn-primary run-btn"
          disabled={!file || running}
          onClick={runDetection}
        >
          {running ? (
            <><span className="spinner" style={{ width: 16, height: 16 }} /> Running Detection…</>
          ) : (
            <><span>🔍</span> Run Anomaly Detection</>
          )}
        </button>
        {running && (
          <div className="progress-bar-track" style={{ marginTop: 16 }}>
            <div className="progress-bar-fill" style={{ width: '70%' }} />
          </div>
        )}
      </section>

      {/* ── Results ── */}
      {results && !running && (
        <>
          <div className="results-divider">
            <span>📊 Detection Results</span>
          </div>

          {/* KPI Row */}
          <section className="page-section">
            <div className="kpi-grid">
              <KpiCard label="Rows Scored"    value={totalScored}        icon="📄" />
              <KpiCard label="Anomalies Found" value={anomalyRecords.length} icon="🚨"
                trend={`${((anomalyRecords.length / totalScored) * 100).toFixed(1)}% rate`}
                trendDirection={anomalyRecords.length > 0 ? 'down' : 'up'}
              />
              <KpiCard
                label="High Severity"
                value={totalScored ? `${((highCount / totalScored) * 100).toFixed(1)}%` : '0.0%'}
                icon="🔴"
                trend={`${highCount.toLocaleString()} records`}
                trendDirection={highCount > 0 ? 'down' : 'up'}
              />
              <KpiCard
                label="Avg Risk Score"
                value={avgRisk ? `${(Number(avgRisk) * 100).toFixed(1)}%` : '—'}
                icon="⚠"
                trend={Number(avgRisk) > 0.5 ? 'Elevated risk level' : 'Stable baseline'}
                trendDirection={Number(avgRisk) > 0.5 ? 'down' : 'up'}
              />
            </div>
          </section>

          {/* Download */}
          <section className="page-section" style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn btn-success" onClick={() => downloadScoredCsv(results.results)}>
              ⬇ Download Scored CSV
            </button>
          </section>

          {/* Anomaly Table */}
          <section className="page-section">
            <AnomalyTable records={anomalyRecords} loading={false} />
          </section>

          {/* Model Compare */}
          {results.results?.length > 0 && (
            <section className="page-section">
              <div className="section-header">
                <h2 className="section-title"><span className="icon">🤖</span> Model Comparison</h2>
              </div>
              <ModelComparePanel records={results.results.slice(0, 100)} />
            </section>
          )}

          {/* Summary */}
          {results.summary && (
            <section className="page-section">
              <div className="glass-card" style={{ padding: 20 }}>
                <div className="section-title" style={{ marginBottom: 12 }}>📋 Scoring Summary</div>
                <div className="summary-grid">
                  {Object.entries(results.summary).map(([k, v]) => (
                    <div key={k} className="summary-item">
                      <span className="summary-key">{k.replace(/_/g, ' ')}</span>
                      <span className="summary-val">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
