import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import { getPrices } from '../api/client';

const PLOTLY_DARK = {
  template: 'plotly_dark',
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, system-ui, sans-serif', color: '#9ca3af', size: 11 },
  margin: { t: 40, r: 20, b: 50, l: 60 },
  xaxis: {
    gridcolor: 'rgba(255,255,255,0.06)',
    linecolor: 'rgba(255,255,255,0.1)',
    tickfont: { size: 10 },
  },
  yaxis: {
    gridcolor: 'rgba(255,255,255,0.06)',
    linecolor: 'rgba(255,255,255,0.1)',
    tickfont: { size: 10 },
  },
  legend: { bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(255,255,255,0.1)', borderwidth: 1 },
};

export default function PriceChart({ commodity, county, fromDate, sensitivity = 50 }) {
  const containerRef = useRef(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [records, setRecords]   = useState([]);
  const [granularity, setGranularity] = useState('daily'); // daily | weekly | monthly

  const fetchData = useCallback(async () => {
    if (!commodity) return;
    setLoading(true);
    setError(null);
    try {
      const params = { commodity };
      if (county)    params.county    = county;
      if (fromDate)  params.from_date = fromDate;
      const data = await getPrices(params);
      setRecords(data?.records ?? []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [commodity, county, fromDate]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Helpers for week / month keys
  const getWeekDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    const mon = new Date(d.setDate(diff));
    return mon.toISOString().split('T')[0];
  };

  const getMonthDate = (dateStr) => {
    if (!dateStr) return '';
    return dateStr.substring(0, 7) + "-01";
  };

  // Frontend resampling/aggregation logic
  const resampled = useMemo(() => {
    if (granularity === 'daily' || !records.length) return records;

    const groups = {};
    records.forEach((r) => {
      if (!r.date) return;
      const key = granularity === 'weekly' ? getWeekDate(r.date) : getMonthDate(r.date);
      if (!groups[key]) {
        groups[key] = {
          date: key,
          price_real_sum: 0,
          expected_price_sum: 0,
          rolling_vol_sum: 0,
          count: 0,
          pred_anomaly: 0,
          prob_anomaly_max: 0,
          severity: null,
          record_type: r.record_type
        };
      }
      groups[key].price_real_sum += r.price_real ?? 0;
      groups[key].expected_price_sum += r.expected_price ?? r.price_real ?? 0;
      groups[key].rolling_vol_sum += r.rolling_vol ?? 0;
      groups[key].count += 1;
      if (r.pred_anomaly) {
        groups[key].pred_anomaly = 1;
        if (!groups[key].severity || r.severity === 'High') {
          groups[key].severity = r.severity;
        }
      }
      groups[key].prob_anomaly_max = Math.max(groups[key].prob_anomaly_max, r.prob_anomaly ?? 0);
    });

    return Object.values(groups)
      .map((g) => ({
        date: g.date,
        price_real: g.price_real_sum / g.count,
        expected_price: g.expected_price_sum / g.count,
        rolling_vol: g.rolling_vol_sum / g.count,
        pred_anomaly: g.pred_anomaly,
        prob_anomaly: g.prob_anomaly_max,
        severity: g.severity,
        record_type: g.record_type
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [records, granularity]);

  useEffect(() => {
    if (!containerRef.current || loading) return;
    if (!resampled.length) return;

    const dates = resampled.map((r) => r.date);
    const actuals = resampled.map((r) => r.price_real);
    const baselines = resampled.map((r) => r.expected_price ?? r.price_real);
    
    // Compute ±15% bands
    const upperBand = baselines.map((val) => val * 1.15);
    const lowerBand = baselines.map((val) => val * 0.85);

    // Compute dynamic sensitivity filter
    const threshold = 1 - (sensitivity / 100);
    const anomalies = resampled.filter((r) => (r.prob_anomaly ?? r.prob_ensemble ?? r.pred_anomaly ?? 0) >= threshold);

    const traces = [
      // 1. Shaded Confidence Bands
      {
        x: [...dates, ...[...dates].reverse()],
        y: [...upperBand, ...[...lowerBand].reverse()],
        fill: 'toself',
        fillcolor: 'rgba(99, 102, 241, 0.05)',
        line: { color: 'transparent' },
        name: 'Confidence Band (±15%)',
        hoverinfo: 'none',
        showlegend: true
      },
      // 2. Expected Price seasonal baseline
      {
        x: dates,
        y: baselines,
        type: 'scatter',
        mode: 'lines',
        name: 'Expected Baseline',
        line: { color: 'rgba(156, 163, 175, 0.45)', width: 1.5, dash: 'dash' },
        hovertemplate: 'Expected KES %{y:.2f}<extra></extra>'
      },
      // 3. Observed Price
      {
        x: dates,
        y: actuals,
        type: 'scatter',
        mode: 'lines',
        name: 'Observed Price',
        line: { color: '#6366f1', width: 2.5, shape: 'spline' },
        hovertemplate: 'Observed KES %{y:.2f}<extra></extra>'
      },
      // 4. Anomaly Markers
      {
        x: anomalies.map((r) => r.date),
        y: anomalies.map((r) => r.price_real),
        type: 'scatter',
        mode: 'markers',
        name: 'Anomaly Flagged',
        marker: {
          color: anomalies.map((r) => {
            const s = (r.severity || '').toLowerCase();
            return s === 'high' ? '#ef4444' : s === 'medium' ? '#f59e0b' : '#f97316';
          }),
          size: 11,
          symbol: 'diamond',
          line: { color: 'rgba(255,255,255,0.7)', width: 1.5 },
        },
        hovertemplate: '<b>%{x}</b><br>Flagged Price: KES %{y:.2f}<br>Risk Score: %{customdata:.3f}<extra></extra>',
        customdata: anomalies.map((r) => r.prob_anomaly ?? 0),
      }
    ];

    // Optional Volatility Overlay
    if (resampled.some((r) => r.rolling_vol != null)) {
      const vol = resampled.map((r) => r.rolling_vol);
      traces.push({
        x: dates,
        y: vol,
        type: 'scatter',
        mode: 'lines',
        name: 'Rolling Volatility',
        line: { color: 'rgba(245,158,11,0.5)', width: 1.2, dash: 'dot' },
        yaxis: 'y2',
        hovertemplate: 'Volatility: %{y:.4f}<extra></extra>'
      });
    }

    const layout = {
      ...PLOTLY_DARK,
      title: {
        text: `${commodity}${county ? ` — ${county}` : ''} Price Anomaly Monitor`,
        font: { size: 13, color: '#f9fafb', family: 'Inter, sans-serif', weight: 600 },
        x: 0,
        xanchor: 'left',
      },
      yaxis2: {
        overlaying: 'y',
        side: 'right',
        title: { text: 'Volatility', font: { size: 10, color: '#f59e0b' } },
        showgrid: false,
        tickfont: { size: 9, color: '#f59e0b' },
      },
      hovermode: 'x unified',
      hoverlabel: { bgcolor: '#1f2937', bordercolor: '#374151', font: { color: '#f9fafb', size: 12 } },
      shapes: anomalies.map((r) => ({
        type: 'line',
        x0: r.date, x1: r.date,
        y0: 0, y1: 1,
        xref: 'x', yref: 'paper',
        line: { color: 'rgba(239,68,68,0.14)', width: 1, dash: 'dot' },
      })),
      legend: {
        orientation: 'h',
        x: 0.5,
        xanchor: 'center',
        y: -0.18,
        bgcolor: 'rgba(0,0,0,0)',
        bordercolor: 'rgba(255,255,255,0.06)',
        borderwidth: 1
      }
    };

    Plotly.react(containerRef.current, traces, layout, {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d'],
    });
  }, [resampled, loading, commodity, county]);

  // Resize observer
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      if (containerRef.current) Plotly.Plots.resize(containerRef.current);
    });
    ro.observe(containerRef.current.parentElement);
    return () => ro.disconnect();
  }, []);

  return (
    <div className="chart-container">
      <div className="chart-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
        <div className="chart-title" style={{ marginBottom: 0 }}>
          📈 Price Intelligence Time-Series {commodity ? `— ${commodity}` : ''} {county ? `/ ${county}` : ''}
        </div>
        <div className="btn-group" style={{ display: 'flex', gap: 4, background: 'rgba(255,255,255,0.03)', padding: 3, borderRadius: 6, border: '1px solid var(--border-glass)' }}>
          {['daily', 'weekly', 'monthly'].map((g) => (
            <button
              key={g}
              className={`btn ${granularity === g ? 'btn-primary' : 'btn-ghost'}`}
              style={{ padding: '4px 10px', fontSize: '0.72rem', borderRadius: 4, height: 'auto', minHeight: 0 }}
              onClick={() => setGranularity(g)}
            >
              {g.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="alert alert-error">⚠ {error}</div>}

      {loading && (
        <div className="loading-overlay">
          <div className="spinner" />
          <span>Loading price data…</span>
        </div>
      )}

      {!loading && !error && !records.length && commodity && (
        <div className="empty-state" style={{ minHeight: 200 }}>
          <span className="empty-state-icon">📊</span>
          <span className="empty-state-title">No price data available</span>
          <span className="empty-state-desc">Try adjusting your filters.</span>
        </div>
      )}

      {!commodity && (
        <div className="empty-state" style={{ minHeight: 200 }}>
          <span className="empty-state-icon">🌾</span>
          <span className="empty-state-title">Select a commodity</span>
          <span className="empty-state-desc">Choose a commodity above to view the price trend chart.</span>
        </div>
      )}

      <div
        ref={containerRef}
        style={{ display: resampled.length && !loading ? 'block' : 'none', minHeight: 340 }}
      />
    </div>
  );
}
