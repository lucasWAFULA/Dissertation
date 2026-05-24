import React, { useState, useMemo, useCallback } from 'react';

const SEVERITY_ORDER = { High: 0, Medium: 1, Low: 2, Normal: 3 };

function severityBadge(severity) {
  const s = (severity || 'normal').toLowerCase();
  const cls = s === 'high' ? 'badge-high' : s === 'medium' ? 'badge-medium' : s === 'low' ? 'badge-low' : 'badge-normal';
  return <span className={`badge ${cls}`}>{severity || 'Normal'}</span>;
}

function downloadCsv(records) {
  if (!records?.length) return;
  const keys = Object.keys(records[0]);
  const header = keys.join(',');
  const rows = records.map((r) =>
    keys.map((k) => {
      const v = r[k];
      if (v === null || v === undefined) return '';
      const s = String(v);
      return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(',')
  );
  const csv = [header, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `anomalies_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

const COLUMNS = [
  { key: 'date',          label: 'Date' },
  { key: 'commodity',     label: 'Commodity' },
  { key: 'county',        label: 'County' },
  { key: 'market',        label: 'Market' },
  { key: 'price_real',    label: 'Price (Real)', format: (v) => v != null ? `KES ${Number(v).toFixed(2)}` : '—' },
  { key: 'expected_price',label: 'Expected',     format: (v) => v != null ? `KES ${Number(v).toFixed(2)}` : '—' },
  { key: 'risk_score',    label: 'Risk Score',   format: (v) => v != null ? Number(v).toFixed(3) : '—' },
  { key: 'prob_ensemble', label: 'P(Anomaly)',   format: (v) => v != null ? `${(Number(v)*100).toFixed(1)}%` : '—' },
  { key: 'severity',      label: 'Severity',     format: (v) => severityBadge(v) },
];

const PAGE_SIZE = 20;

export default function AnomalyTable({ records = [], loading = false }) {
  const [sortKey, setSortKey]   = useState('date');
  const [sortDir, setSortDir]   = useState('desc');
  const [filter, setFilter]     = useState('');
  const [page, setPage]         = useState(1);

  const handleSort = useCallback((key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
    setPage(1);
  }, [sortKey]);

  const filtered = useMemo(() => {
    if (!filter.trim()) return records;
    const q = filter.toLowerCase();
    return records.filter((r) =>
      Object.values(r).some((v) => String(v ?? '').toLowerCase().includes(q))
    );
  }, [records, filter]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let va = a[sortKey];
      let vb = b[sortKey];

      if (sortKey === 'severity') {
        va = SEVERITY_ORDER[va] ?? 99;
        vb = SEVERITY_ORDER[vb] ?? 99;
      } else if (typeof va === 'string' && !isNaN(Date.parse(va)) && sortKey === 'date') {
        va = new Date(va).getTime();
        vb = new Date(vb).getTime();
      } else {
        va = Number(va) || va;
        vb = Number(vb) || vb;
      }

      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const paginated  = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (loading) {
    return (
      <div className="table-container">
        <div className="table-header">
          <span className="section-title">Anomaly Alerts</span>
        </div>
        <div style={{ padding: 24 }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton skeleton-text" style={{ marginBottom: 12, width: `${80 + (i % 3) * 7}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (!records.length) {
    return (
      <div className="table-container">
        <div className="table-header">
          <span className="section-title">🚨 Anomaly Alerts</span>
        </div>
        <div className="empty-state">
          <span className="empty-state-icon">✅</span>
          <span className="empty-state-title">No anomalies found</span>
          <span className="empty-state-desc">No records match the current filter criteria.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="table-container">
      <div className="table-header">
        <span className="section-title">🚨 Anomaly Alerts <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: '0.85rem' }}>({filtered.length.toLocaleString()} records)</span></span>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            className="form-control"
            style={{ width: 200 }}
            placeholder="Search…"
            value={filter}
            onChange={(e) => { setFilter(e.target.value); setPage(1); }}
          />
          <button className="btn btn-outline" onClick={() => downloadCsv(sorted)}>
            ⬇ CSV
          </button>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className={sortKey === col.key ? 'sorted' : ''}
                >
                  {col.label}
                  {sortKey === col.key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ' ↕'}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map((row, i) => (
              <tr key={i}>
                {COLUMNS.map((col) => {
                  const raw = row[col.key];
                  const content = col.format ? col.format(raw) : (raw ?? '—');
                  return (
                    <td key={col.key} className={!col.format && (raw === null || raw === undefined) ? 'muted' : ''}>
                      {content}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span>
          Showing {((page - 1) * PAGE_SIZE + 1).toLocaleString()}–{Math.min(page * PAGE_SIZE, sorted.length).toLocaleString()} of {sorted.length.toLocaleString()}
        </span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <button
            className="btn btn-ghost"
            style={{ padding: '5px 10px' }}
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            ‹ Prev
          </button>
          <span style={{ fontSize: '0.8rem' }}>
            {page} / {totalPages}
          </span>
          <button
            className="btn btn-ghost"
            style={{ padding: '5px 10px' }}
            disabled={page === totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next ›
          </button>
        </div>
      </div>
    </div>
  );
}
