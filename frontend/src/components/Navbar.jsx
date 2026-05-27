import React, { useEffect, useState, useCallback, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { getHealth } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { logOut } from '../firebase';
import './Navbar.css';

const NAV_LINKS = [
  { to: '/app',           label: 'Market Intelligence', icon: '📊' },
  { to: '/app/forensic',   label: 'Forensic Audit',      icon: '🔍' },
  { to: '/app/explainability', label: 'Explainability',  icon: '🧠' },
];

export default function Navbar({ onToggleSidebar }) {
  const { user, userPlan } = useAuth();
  const [health, setHealth]     = useState(null);
  const [checking, setChecking] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    try {
      await logOut();
      navigate('/');
    } catch (err) {
      console.error('[Navbar] Logout failed:', err);
    }
  };

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
            end={to === '/app'}
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

        {user && (
          <div className="profile-dropdown-container" ref={dropdownRef}>
            <button
              className="profile-trigger"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              aria-label="User menu"
            >
              {user.photoURL ? (
                <img src={user.photoURL} alt="Avatar" className="profile-avatar-img" />
              ) : (
                <span className="profile-avatar-text">
                  {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
                </span>
              )}
            </button>

            {dropdownOpen && (
              <div className="profile-dropdown-menu">
                <div className="profile-dropdown-header">
                  <span className="profile-email" title={user.email}>
                    {user.email}
                  </span>
                  <span className={`profile-plan-badge ${userPlan}`}>
                    {userPlan.toUpperCase()}
                  </span>
                </div>
                <div className="profile-dropdown-divider" />
                <button className="profile-dropdown-item signout-btn" onClick={handleSignOut}>
                  <span className="item-icon">🚪</span>
                  <span className="item-label">Sign Out</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
