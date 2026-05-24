import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import KpiCard from '../components/KpiCard';
import PriceChart from '../components/PriceChart';
import AnomalyTable from '../components/AnomalyTable';
import GeoMap from '../components/GeoMap';
import ModelComparePanel from '../components/ModelComparePanel';
import AlertCards from '../components/AlertCards';
import { getDashboardData, getAnomalies, getGeoData } from '../api/client';
import './MarketIntelligence.css';

export default function MarketIntelligence({ severity = 'All', sensitivity = 50, ensembleWeights, onSelectAnomaly }) {
  const navigate = useNavigate();

  // ── State ──────────────────────────────────────────────────
  const [dashboard, setDashboard]       = useState(null);
  const [dashLoading, setDashLoading]   = useState(true);
  const [dashError, setDashError]       = useState(null);

  const [anomalies, setAnomalies]       = useState([]);
  const [aLoading, setALoading]         = useState(true);
  const [aError, setAError]             = useState(null);

  const [geoData, setGeoData]           = useState(null);
  const [geoLoading, setGeoLoading]     = useState(true);

  // ── Filters ─────────────────────────────────────────────────
  const [commodity, setCommodity]       = useState('');
  const [county, setCounty]             = useState('');
  const [fromDate, setFromDate]         = useState('');

  // ── Fetch Dashboard ─────────────────────────────────────────
  const fetchDashboard = useCallback(async () => {
    setDashLoading(true);
    setDashError(null);
    try {
      const data = await getDashboardData();
      setDashboard(data);
    } catch (err) {
      setDashError(err.message);
    } finally {
      setDashboard(prev => {
        if (!prev) return prev;
        // recalculate totals
        return prev;
      });
      setDashLoading(false);
    }
  }, []);

  // ── Fetch Anomalies ─────────────────────────────────────────
  const fetchAnomalies = useCallback(async () => {
    setALoading(true);
    setAError(null);
    try {
      const params = { limit: 500 };
      const data = await getAnomalies(params);
      setAnomalies(data?.records ?? []);
    } catch (err) {
      setAError(err.message);
      setAnomalies([]);
    } finally {
      setALoading(false);
    }
  }, []);

  // ── Fetch Geo ───────────────────────────────────────────────
  const fetchGeo = useCallback(async () => {
    setGeoLoading(true);
    try {
      const data = await getGeoData();
      setGeoData(data);
    } catch {
      setGeoData(null);
    } finally {
      setGeoLoading(false);
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);
  useEffect(() => { fetchAnomalies(); }, [fetchAnomalies]);
  useEffect(() => { fetchGeo(); }, [fetchGeo]);

  // ── KPI Values ───────────────────────────────────────────────
  const kpis = dashboard?.kpis ?? {};
  const commodities = dashboard?.commodities ?? [];
  const counties    = dashboard?.counties ?? [];

  // Compute metrics
  const hrm = kpis.highest_risk_market;
  const anomaliesTrend = kpis.anomalies_trend;

  // ── Filtered anomaly records dynamically based on sensitivity ──
  const filteredAnomalies = useMemo(() => {
    const threshold = 1 - (sensitivity / 100);
    return anomalies
      .map((r) => {
        const score = r.risk_score ?? r.prob_ensemble ?? r.prob_anomaly ?? 0;
        const active = score >= threshold ? 1 : 0;
        const priceSpike = r.price_spike_pct ?? (r.expected_price ? (((r.price_real - r.expected_price) / r.expected_price) * 100) : 0);
        
        let sev = 'Low';
        if (active) {
          if (score >= 0.99 || priceSpike >= 20.0) {
            sev = 'High';
          } else {
            sev = 'Medium';
          }
        }
        
        return {
          ...r,
          pred_anomaly: active,
          severity: sev
        };
      })
      .filter((r) => {
        if (severity !== 'All' && r.severity !== severity) return false;
        if (commodity && r.commodity !== commodity) return false;
        if (county    && r.county    !== county)    return false;
        return true;
      });
  }, [anomalies, commodity, county, severity, sensitivity]);

  // ── Alert Card Action Handlers ──────────────────────────────
  const handleAlertInvestigate = (comm, cnty) => {
    setCommodity(comm);
    setCounty(cnty);
    setTimeout(() => {
      document.querySelector('.chart-container')?.scrollIntoView({ behavior: 'smooth' });
    }, 120);
  };

  const handleAlertExplain = (alert) => {
    onSelectAnomaly(alert);
    navigate('/explainability');
  };

  // ── Reporting & Export Actions ──────────────────────────────
  const handleExportCSV = () => {
    if (!filteredAnomalies.length) return;
    const headers = ['Date', 'Commodity', 'County', 'Market', 'Observed Price (KES/kg)', 'Expected Price (KES/kg)', 'Risk Score', 'Severity'];
    const rows = filteredAnomalies.map((r) => [
      r.date, r.commodity, r.county, r.market, r.price_real, r.expected_price, r.risk_score, r.severity
    ]);
    const csvContent = [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `Market_Anomalies_Report_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportPDF = () => {
    window.print();
  };

  const handleGenerateReport = () => {
    alert("Food Price Intelligence forensic audit report generated successfully! Preparing document view.");
    window.print();
  };

  return (
    <div className="mi-page">
      {/* ── Page Header ── */}
      <div className="page-header" style={{ alignItems: 'center', marginBottom: 20 }}>
        <div style={{ flex: 1, minWidth: 280 }}>
          <h1 className="page-title gradient-text">Market Intelligence</h1>
          <p className="page-subtitle" style={{ marginBottom: 0 }}>
            Real-time food price anomaly detection and early warning platform across Kenya
          </p>
        </div>
        <div className="btn-group" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
          <button className="btn btn-outline" onClick={handleExportCSV} data-tooltip="Download current anomalies list in CSV format">
            📥 Export CSV
          </button>
          <button className="btn btn-outline" onClick={handleExportPDF} data-tooltip="Print the current dashboard page to PDF">
            📄 Export PDF
          </button>
          <button className="btn btn-primary" onClick={handleGenerateReport} data-tooltip="Generate institutional audit reports">
            ⚡ Generate Anomaly Report
          </button>
          <button className="btn btn-ghost" onClick={() => { fetchDashboard(); fetchAnomalies(); fetchGeo(); }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* ── Error Banners ── */}
      {dashError && <div className="alert alert-error">⚠ Dashboard error: {dashError}</div>}
      {aError    && <div className="alert alert-error">⚠ Anomalies error: {aError}</div>}

      {/* ── KPI Row ── */}
      <section className="page-section" style={{ marginBottom: 24 }}>
        {dashLoading ? (
          <div className="kpi-grid">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton skeleton-card" />
            ))}
          </div>
        ) : (
          <div className="kpi-grid">
            <KpiCard
              label="Tracked Markets"
              value={commodities.length * counties.length || kpis.total_commodities}
              icon="🌾"
              trend={`${commodities.length} commodities in ${counties.length} counties`}
              trendDirection="neutral"
            />
            <KpiCard
              label="Anomalies This Month"
              value={kpis.latest_month_anomalies ?? 0}
              icon="🚨"
              trend={anomaliesTrend ? anomaliesTrend.label : (kpis.latest_month_anomalies > 0 ? 'Requires attention' : 'All clear')}
              trendDirection={anomaliesTrend ? (anomaliesTrend.direction === 'up' ? 'down' : anomaliesTrend.direction === 'down' ? 'up' : 'neutral') : (kpis.latest_month_anomalies > 0 ? 'down' : 'up')}
              cardClass={kpis.latest_month_anomalies > 0 ? 'glow-danger' : ''}
            />
            <KpiCard
              label="Highest Risk Market"
              value={
                hrm ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {hrm.commodity} – {hrm.county}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--danger)', fontWeight: 600 }}>
                      Score: {Number(hrm.risk_score).toFixed(3)} ({hrm.severity})
                    </span>
                  </div>
                ) : (
                  '—'
                )
              }
              icon="📈"
              trend={hrm && hrm.deviation ? `${hrm.deviation > 0 ? '+' : ''}${hrm.deviation}% price deviation` : 'No active deviations'}
              trendDirection={hrm && hrm.deviation > 15 ? 'down' : 'neutral'}
              cardClass="glow-danger"
            />
            <KpiCard
              label="Avg Risk Score"
              value={
                kpis.avg_risk_score != null ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
                    <span style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>
                      {`${(Number(kpis.avg_risk_score) * 100).toFixed(1)}%`}
                    </span>
                    <div className="weight-bar-track" style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.08)', width: '100%' }}>
                      <div
                        className="weight-bar-fill"
                        style={{
                          width: `${(kpis.avg_risk_score * 100).toFixed(0)}%`,
                          height: '100%',
                          borderRadius: 2,
                          background: kpis.avg_risk_score > 0.5 ? 'var(--danger)' : kpis.avg_risk_score > 0.3 ? 'var(--warning)' : 'var(--success)'
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  '—'
                )
              }
              icon="⚠"
              trend={kpis.avg_risk_score > 0.5 ? 'Elevated alert level' : 'Stable market baseline'}
              trendDirection={kpis.avg_risk_score > 0.5 ? 'down' : 'up'}
            />
          </div>
        )}
      </section>

      {/* ── Active Warning Alerts ── */}
      <section className="page-section">
        <AlertCards
          records={anomalies}
          onInvestigate={handleAlertInvestigate}
          onExplain={handleAlertExplain}
        />
      </section>

      {/* ── Filters ── */}
      <section className="page-section" style={{ marginBottom: 24 }}>
        <div className="filter-row">
          <div className="form-group">
            <label className="form-label">Commodity</label>
            <select
              className="form-control"
              value={commodity}
              onChange={(e) => setCommodity(e.target.value)}
            >
              <option value="">All Commodities</option>
              {commodities.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">County</label>
            <select
              className="form-control"
              value={county}
              onChange={(e) => setCounty(e.target.value)}
            >
              <option value="">All Counties</option>
              {counties.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">From Date</label>
            <input
              type="date"
              className="form-control"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
            />
          </div>
          <div className="form-group" style={{ justifyContent: 'flex-end' }}>
            <button
              className="btn btn-ghost"
              onClick={() => { setCommodity(''); setCounty(''); setFromDate(''); }}
              style={{ marginTop: 'auto' }}
            >
              ✕ Clear
            </button>
          </div>
        </div>
      </section>

      {/* ── Price Chart ── */}
      <section className="page-section" style={{ marginBottom: 28 }}>
        <PriceChart
          commodity={commodity || (commodities[0] ?? '')}
          county={county || ''}
          fromDate={fromDate}
          sensitivity={sensitivity}
        />
      </section>

      {/* ── Anomaly Table ── */}
      <section className="page-section" style={{ marginBottom: 28 }}>
        <AnomalyTable records={filteredAnomalies} loading={aLoading} />
      </section>

      {/* ── Geo Map ── */}
      <section className="page-section" style={{ marginBottom: 28 }}>
        {geoLoading ? (
          <div className="chart-container">
            <div className="loading-overlay"><div className="spinner" /><span>Loading map…</span></div>
          </div>
        ) : (
          <GeoMap data={geoData} />
        )}
      </section>

      {/* ── Model Intelligence ── */}
      {filteredAnomalies.length > 0 && (
        <section className="page-section">
          <div className="section-header">
            <h2 className="section-title"><span className="icon">🤖</span> Model Intelligence</h2>
          </div>
          <ModelComparePanel records={filteredAnomalies.slice(0, 100)} />
        </section>
      )}

      {/* ── Data pipeline footer ── */}
      {dashboard?.pipeline && (
        <div className="pipeline-info">
          <span>📦 Data pipeline:</span>
          <span>{dashboard.pipeline.rows?.toLocaleString()} rows</span>
          <span>·</span>
          <span>{dashboard.pipeline.commodities} commodities</span>
          <span>·</span>
          <span>{dashboard.pipeline.counties} counties</span>
          <span>·</span>
          <span>{dashboard.pipeline.date_min} → {dashboard.pipeline.date_max}</span>
        </div>
      )}
    </div>
  );
}
