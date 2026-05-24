import React from 'react';

export default function AlertCards({ records = [], onInvestigate, onExplain }) {
  // Get top active anomalies sorted by risk_score
  const activeAlerts = (records || [])
    .filter((r) => r.pred_anomaly === 1)
    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
    .slice(0, 3);

  if (activeAlerts.length === 0) {
    return (
      <div className="alert alert-success" style={{ margin: '0 0 24px 0', borderLeft: '4px solid var(--success)' }}>
        <span style={{ fontSize: '1.2rem' }}>✅</span>
        <div>
          <strong style={{ display: 'block', fontSize: '0.88rem', color: '#6ee7b7' }}>All Systems Nominal</strong>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            No food price anomalies are currently active in any monitored Kenya markets.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="alert-cards-container" style={{ marginBottom: 28 }}>
      <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
        🚨 Active Early Warning Alerts ({activeAlerts.length})
      </div>
      <div className="alert-cards-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        {activeAlerts.map((alert, i) => {
          const isHigh = (alert.severity || '').toLowerCase() === 'high';
          const badgeClass = isHigh ? 'badge-high' : 'badge-medium';
          const alertBorderColor = isHigh ? 'rgba(239, 68, 68, 0.35)' : 'rgba(245, 158, 11, 0.35)';
          const alertGlowColor = isHigh ? 'rgba(239, 68, 68, 0.04)' : 'rgba(245, 158, 11, 0.04)';

          const deviation = alert.price_real && alert.expected_price
            ? ((alert.price_real - alert.expected_price) / alert.expected_price) * 100
            : null;

          return (
            <div
              key={i}
              className="glass-card alert-action-card"
              style={{
                padding: 18,
                border: `1px solid ${alertBorderColor}`,
                backgroundColor: alertGlowColor,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'all 0.3s ease',
                position: 'relative',
                overflow: 'hidden',
                borderRadius: 'var(--radius-lg)'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <span className={`badge ${badgeClass}`}>{alert.severity || 'Caution'}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500 }}>{alert.date}</span>
                </div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>
                  {alert.commodity} – {alert.county}
                </h4>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4, marginBottom: 14 }}>
                  Price flagged at <strong style={{ color: 'var(--text)' }}>KES {Number(alert.price_real).toFixed(1)}/kg</strong>{' '}
                  {deviation !== null && (
                    <span className={deviation > 0 ? 'text-danger' : 'text-success'} style={{ fontWeight: 600 }}>
                      ({deviation > 0 ? '+' : ''}{deviation.toFixed(1)}%)
                    </span>
                  )}{' '}
                  vs expected baseline of KES {Number(alert.expected_price).toFixed(1)}/kg.
                </p>
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 'auto' }}>
                <button
                  className="btn btn-outline"
                  style={{ padding: '6px 12px', fontSize: '0.75rem', flex: 1 }}
                  onClick={() => onInvestigate && onInvestigate(alert.commodity, alert.county)}
                >
                  🔍 Investigate
                </button>
                <button
                  className="btn btn-primary"
                  style={{ padding: '6px 12px', fontSize: '0.75rem', flex: 1 }}
                  onClick={() => onExplain && onExplain(alert)}
                >
                  🧠 Explain
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
