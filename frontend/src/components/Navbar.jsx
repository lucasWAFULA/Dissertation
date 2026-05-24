import React, { useEffect, useState, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { getHealth } from '../api/client';
import './Navbar.css';

const NAV_LINKS = [
  { to: '/',           label: 'Market Intelligence', icon: '📊' },
  { to: '/forensic',   label: 'Forensic Audit',      icon: '🔍' },
  { to: '/explainability', label: 'Explainability',  icon: '🧠' },
];

export default function Navbar({ onToggleSidebar }) {
  const [health, setHealth]     = useState(null);
  const [checking, setChecking] = useState(true);

  const checkHealth = useCallback(async () => {
    try {
      const data = await getHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, 30000);
    return () => clearInterval(id);
  }, [checkHealth]);

  const isOk = health?.status === 'ok' || health?.ready === true;

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <button className="navbar-toggle" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          <span className="toggle-bar" />
          <span className="toggle-bar" />
          <span className="toggle-bar" />
        </button>
        <div className="navbar-brand">
          <span className="brand-icon">🌾</span>
          <span className="brand-name gradient-text">Market Price Pulse AI</span>
        </div>
      </div>

      <div className="navbar-center">
        {NAV_LINKS.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `nav-link ${isActive ? 'nav-link-active' : ''}`
            }
          >
            <span className="nav-icon">{icon}</span>
            <span className="nav-label">{label}</span>
          </NavLink>
        ))}
      </div>

      <div className="navbar-right">
        <div
          className={`health-indicator ${checking ? 'checking' : isOk ? 'healthy' : 'unhealthy'}`}
          data-tooltip={
            checking
              ? 'Checking backend...'
              : isOk
              ? `Backend OK · Model: ${health?.model_loaded ? 'Loaded' : 'Not loaded'}`
              : 'Backend unreachable'
          }
        >
          <span className="health-dot" />
          <span className="health-label">
            {checking ? 'Checking…' : isOk ? 'System OK' : 'Offline'}
          </span>
        </div>
      </div>
    </nav>
  );
}
