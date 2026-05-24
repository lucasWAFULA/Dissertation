import React, { useEffect, useRef, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';

const PLOTLY_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, system-ui, sans-serif', color: '#9ca3af', size: 11 },
};

function riskColor(score) {
  if (score >= 0.7) return '#ef4444';
  if (score >= 0.4) return '#f59e0b';
  return '#10b981';
}

export default function GeoMap({ data }) {
  const containerRef = useRef(null);

  const renderMap = useCallback(() => {
    if (!containerRef.current || !data?.counties?.length) return;

    const counties = data.counties;

    const trace = {
      type: 'scattergeo',
      mode: 'markers+text',
      lat: counties.map((c) => c.latitude),
      lon: counties.map((c) => c.longitude),
      text: counties.map((c) => c.COUNTY),
      textposition: 'top center',
      textfont: { size: 9, color: 'rgba(249,250,251,0.7)' },
      marker: {
        size: counties.map((c) => Math.max(8, Math.min(40, (c.anomaly_count || 1) * 1.5))),
        color: counties.map((c) => c.avg_risk_score ?? 0),
        colorscale: [
          [0.0, '#10b981'], // Stable Green
          [0.4, '#f59e0b'], // Warning Amber
          [0.7, '#f97316'], // Critical Orange
          [1.0, '#ef4444'], // Anomaly Red
        ],
        cmin: 0,
        cmax: 1,
        showscale: true,
        colorbar: {
          title: { text: 'Risk Score', font: { color: '#9ca3af', size: 10 } },
          tickfont: { color: '#9ca3af', size: 9 },
          bgcolor: 'rgba(17,24,39,0.8)',
          bordercolor: 'rgba(255,255,255,0.1)',
          borderwidth: 1,
          thickness: 12,
          len: 0.6,
        },
        opacity: 0.85,
        line: { color: 'rgba(255,255,255,0.2)', width: 1 },
        sizemode: 'area',
      },
      hovertemplate:
        '<b>%{text}</b><br>' +
        'Anomalies: %{customdata[0]}<br>' +
        'Avg Risk: %{customdata[1]:.3f}<br>' +
        'Lat: %{lat:.3f} | Lon: %{lon:.3f}' +
        '<extra></extra>',
      customdata: counties.map((c) => [c.anomaly_count ?? 0, c.avg_risk_score ?? 0]),
      name: 'Counties',
    };

    const layout = {
      ...PLOTLY_BASE,
      title: {
        text: 'Geographic Anomaly Hotspots — Kenya',
        font: { size: 14, color: '#f9fafb', family: 'Inter, sans-serif' },
        x: 0,
        xanchor: 'left',
      },
      margin: { t: 44, r: 10, b: 10, l: 10 },
      geo: {
        scope: 'africa',
        resolution: 50,
        center: { lat: 0.02, lon: 37.9 },
        projection: { type: 'mercator', scale: 5.5 },
        showland: true,
        landcolor: 'rgba(30,40,60,0.9)',
        showocean: true,
        oceancolor: 'rgba(10,14,26,0.95)',
        showlakes: true,
        lakecolor: 'rgba(10,14,26,0.8)',
        showcountries: true,
        countrycolor: 'rgba(255,255,255,0.12)',
        showcoastlines: true,
        coastlinecolor: 'rgba(255,255,255,0.15)',
        bgcolor: 'rgba(0,0,0,0)',
        framecolor: 'rgba(255,255,255,0.08)',
        framewidth: 1,
      },
      hoverlabel: {
        bgcolor: '#1f2937',
        bordercolor: '#374151',
        font: { color: '#f9fafb', size: 12 },
      },
    };

    Plotly.react(containerRef.current, [trace], layout, {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d'],
    });
  }, [data]);

  useEffect(() => { renderMap(); }, [renderMap]);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      if (containerRef.current) Plotly.Plots.resize(containerRef.current);
    });
    ro.observe(containerRef.current.parentElement);
    return () => ro.disconnect();
  }, []);

  if (!data?.counties?.length) {
    return (
      <div className="chart-container">
        <div className="chart-title">🗺 Geographic Hotspots</div>
        <div className="empty-state" style={{ minHeight: 300 }}>
          <span className="empty-state-icon">🗺</span>
          <span className="empty-state-title">No geographic data</span>
          <span className="empty-state-desc">Geographic data is not available.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-container">
      <div className="chart-title">🗺 Geographic Anomaly Hotspots</div>
      <div ref={containerRef} style={{ minHeight: 420 }} />

      {/* Legend */}
      <div style={{
        display: 'flex', gap: 16, flexWrap: 'wrap',
        marginTop: 12, fontSize: '0.75rem', color: 'var(--text-muted)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
          Low Risk
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b', display: 'inline-block' }} />
          Medium Risk
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} />
          High Risk
        </span>
        <span style={{ marginLeft: 'auto', color: 'var(--text-dim)' }}>
          Bubble size ∝ anomaly count
        </span>
      </div>
    </div>
  );
}
