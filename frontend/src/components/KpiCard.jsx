import React, { useEffect, useRef, useState } from 'react';

function useAnimatedCounter(target, duration = 1200) {
  const [value, setValue] = useState(0);
  const frameRef = useRef(null);

  useEffect(() => {
    if (target === null || target === undefined || isNaN(Number(target))) {
      setValue(target);
      return;
    }
    const num = Number(target);
    const start = performance.now();
    const animate = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * num * 100) / 100;
      setValue(current);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };
    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration]);

  return value;
}

function formatValue(raw, animatedNum, decimals) {
  if (raw === null || raw === undefined) return '—';
  if (typeof raw === 'string' && isNaN(Number(raw))) return raw;
  const num = Number(raw);
  if (isNaN(num)) return raw;

  const display = animatedNum;
  if (decimals !== undefined) return display.toFixed(decimals);
  if (Number.isInteger(num)) return Math.round(display).toLocaleString();
  return display.toFixed(2);
}

export default function KpiCard({ label, value, trend, trendDirection = 'neutral', icon, decimals, cardClass = '' }) {
  const isNumeric = typeof value === 'number' || (typeof value === 'string' && value.trim() !== '' && !isNaN(Number(value)));
  const numericVal = isNumeric ? Number(value) : 0;
  
  const animated = useAnimatedCounter(numericVal);

  const displayValue = isNumeric ? formatValue(value, animated, decimals) : value;

  const trendClass =
    trendDirection === 'up'
      ? 'up'
      : trendDirection === 'down'
      ? 'down'
      : 'neutral';

  const trendIcon =
    trendDirection === 'up' ? '↑' : trendDirection === 'down' ? '↓' : '→';

  return (
    <div className={`kpi-card ${cardClass}`}>
      <div className="kpi-card-header">
        <div className="kpi-label">{label}</div>
        {icon && <div className="kpi-icon">{icon}</div>}
      </div>
      <div className="kpi-value">{displayValue}</div>
      {trend !== undefined && trend !== null && (
        <div className={`kpi-trend ${trendClass}`}>
          <span>{trendIcon}</span>
          <span>{trend}</span>
        </div>
      )}
    </div>
  );
}
