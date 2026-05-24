import React, { useEffect, useRef, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';

const PLOTLY_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, system-ui, sans-serif', color: '#9ca3af', size: 11 },
};

function agreementLabel(r) {
  const lr  = r.prob_lr  != null ? r.prob_lr  > 0.5 : null;
  const xgb = r.prob_xgb != null ? r.prob_xgb > 0.5 : null;
  if (lr === null || xgb === null) return 'Unknown';
  if (lr && xgb)   return 'Both Agree (Anomaly)';
  if (!lr && !xgb) return 'Both Agree (Normal)';
  if (lr && !xgb)  return 'Only LR Flags';
  return 'Only XGB Flags';
}

export default function ModelComparePanel({ records = [] }) {
  const barRef = useRef(null);
  const pieRef = useRef(null);

  const sample = records.slice(0, 30);

  const renderBar = useCallback(() => {
    if (!barRef.current || !sample.length) return;

    const labels = sample.map((r, i) =>
      `${r.commodity || r.date || `#${i + 1}`}`.slice(0, 20)
    );

    const traces = [
      {
        x: labels,
        y: sample.map((r) => (r.prob_lr ?? 0) * 100),
        type: 'bar',
        name: 'Logistic Regression',
        marker: { color: 'rgba(99,102,241,0.75)' },
        hovertemplate: '%{x}<br>LR: %{y:.1f}%<extra></extra>',
      },
      {
        x: labels,
        y: sample.map((r) => (r.prob_xgb ?? 0) * 100),
        type: 'bar',
        name: 'XGBoost',
        marker: { color: 'rgba(245,158,11,0.75)' },
        hovertemplate: '%{x}<br>XGB: %{y:.1f}%<extra></extra>',
      },
      {
        x: labels,
        y: sample.map((r) => (r.prob_ensemble ?? 0) * 100),
        type: 'bar',
        name: 'Ensemble',
        marker: { color: 'rgba(16,185,129,0.75)' },
        hovertemplate: '%{x}<br>Ensemble: %{y:.1f}%<extra></extra>',
      },
    ];

    const layout = {
      ...PLOTLY_BASE,
      title: {
        text: 'Model Probability Comparison (Top 30 Records)',
        font: { size: 13, color: '#f9fafb' },
        x: 0, xanchor: 'left',
      },
      barmode: 'group',
      margin: { t: 44, r: 20, b: 100, l: 50 },
      xaxis: {
        gridcolor: 'rgba(255,255,255,0.06)',
        tickangle: -35,
        tickfont: { size: 9 },
      },
      yaxis: {
        gridcolor: 'rgba(255,255,255,0.06)',
        title: { text: 'P(Anomaly) %', font: { size: 11, color: '#9ca3af' } },
        range: [0, 105],
      },
      legend: { orientation: 'h', y: 1.12, bgcolor: 'rgba(0,0,0,0)' },
      shapes: [
        {
          type: 'line', y0: 50, y1: 50, x0: 0, x1: 1,
          xref: 'paper', yref: 'y',
          line: { color: 'rgba(239,68,68,0.4)', width: 1, dash: 'dash' },
        },
      ],
      hoverlabel: { bgcolor: '#1f2937', bordercolor: '#374151', font: { color: '#f9fafb', size: 12 } },
    };

    Plotly.react(barRef.current, traces, layout, {
      responsive: true,
      displayModeBar: false,
    });
  }, [sample]);

  const renderPie = useCallback(() => {
    if (!pieRef.current || !records.length) return;

    const counts = {};
    records.forEach((r) => {
      const label = agreementLabel(r);
      counts[label] = (counts[label] || 0) + 1;
    });

    const labels = Object.keys(counts);
    const values = Object.values(counts);
    const colors = {
      'Both Agree (Anomaly)': '#ef4444',
      'Both Agree (Normal)':  '#10b981',
      'Only LR Flags':        '#6366f1',
      'Only XGB Flags':       '#f59e0b',
      'Unknown':              '#6b7280',
    };

    const trace = {
      type: 'pie',
      labels,
      values,
      marker: { colors: labels.map((l) => colors[l] || '#6b7280') },
      hole: 0.45,
      textinfo: 'percent+label',
      textfont: { size: 10, color: '#f9fafb' },
      hovertemplate: '<b>%{label}</b><br>%{value} records (%{percent})<extra></extra>',
      insidetextorientation: 'radial',
    };

    const layout = {
      ...PLOTLY_BASE,
      title: {
        text: 'Model Agreement Analysis',
        font: { size: 13, color: '#f9fafb' },
        x: 0, xanchor: 'left',
      },
      margin: { t: 44, r: 10, b: 10, l: 10 },
      showlegend: true,
      legend: {
        orientation: 'v',
        font: { size: 10, color: '#9ca3af' },
        bgcolor: 'rgba(0,0,0,0)',
      },
      hoverlabel: { bgcolor: '#1f2937', bordercolor: '#374151', font: { color: '#f9fafb', size: 12 } },
    };

    Plotly.react(pieRef.current, [trace], layout, {
      responsive: true,
      displayModeBar: false,
    });
  }, [records]);

  useEffect(() => { renderBar(); }, [renderBar]);
  useEffect(() => { renderPie(); }, [renderPie]);

  useEffect(() => {
    const observers = [];
    [barRef, pieRef].forEach((ref) => {
      if (!ref.current) return;
      const ro = new ResizeObserver(() => {
        if (ref.current) Plotly.Plots.resize(ref.current);
      });
      ro.observe(ref.current.parentElement);
      observers.push(ro);
    });
    return () => observers.forEach((ro) => ro.disconnect());
  }, []);

  if (!records.length) {
    return (
      <div className="chart-container">
        <div className="chart-title">🤖 Model Intelligence</div>
        <div className="empty-state" style={{ minHeight: 200 }}>
          <span className="empty-state-icon">🤖</span>
          <span className="empty-state-title">No records to compare</span>
          <span className="empty-state-desc">Load anomaly data to view model comparison.</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="chart-container">
        <div ref={barRef} style={{ minHeight: 340 }} />
      </div>
      <div className="chart-container">
        <div ref={pieRef} style={{ minHeight: 300 }} />
      </div>
    </div>
  );
}
