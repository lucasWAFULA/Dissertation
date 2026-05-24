import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/* ─────────────────────────────────────────────────────────────────────────────
   LANDING PAGE — MarketPulse AI
   Full-screen dark hero, animated mesh, stats, features, pricing, footer.
   All styles are vanilla CSS injected via a <style> tag.
───────────────────────────────────────────────────────────────────────────── */

// ── Animated count-up hook ────────────────────────────────────────────────────
function useCountUp(target, duration = 1600, started = false) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!started) return;
    let start = null;
    const step = (ts) => {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [started, target, duration]);
  return value;
}

// ── Scroll-reveal hook (IntersectionObserver) ─────────────────────────────────
function useScrollReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('[data-reveal]');
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
}

// ── Abstract chart mockup (pure CSS-drawn) ────────────────────────────────────
const DashboardMockup = () => (
  <div className="ld-mockup">
    <div className="ld-mockup-header">
      <div className="ld-mockup-dot red" />
      <div className="ld-mockup-dot yellow" />
      <div className="ld-mockup-dot green" />
      <span className="ld-mockup-title">Market Intelligence Dashboard</span>
    </div>
    <div className="ld-mockup-body">
      {/* Mini KPI cards */}
      <div className="ld-mini-kpis">
        {[
          { label: 'Anomalies', value: '23', up: true },
          { label: 'Accuracy',  value: '98.7%', up: true },
          { label: 'Markets',   value: '47', up: false },
        ].map((k) => (
          <div key={k.label} className="ld-mini-kpi">
            <span className="ld-mini-kpi-val">{k.value}</span>
            <span className="ld-mini-kpi-label">{k.label}</span>
            <span className={`ld-mini-kpi-badge ${k.up ? 'up' : 'neutral'}`}>
              {k.up ? '↑' : '→'}
            </span>
          </div>
        ))}
      </div>
      {/* Animated chart bars */}
      <div className="ld-chart">
        {[55,70,45,88,62,95,78,52,85,91,65,74].map((h, i) => (
          <div
            key={i}
            className={`ld-bar ${h > 80 ? 'anomaly' : ''}`}
            style={{ '--h': `${h}%`, animationDelay: `${i * 0.06}s` }}
          />
        ))}
        {/* Alert spike overlay */}
        <div className="ld-spike" style={{ left: '62%' }} />
      </div>
      {/* Legend */}
      <div className="ld-chart-legend">
        <span className="ld-legend-dot normal" />Normal
        <span className="ld-legend-dot anomaly" style={{marginLeft:'12px'}} />Anomaly Detected
      </div>
    </div>
  </div>
);

// ── Stats section ─────────────────────────────────────────────────────────────
const StatsBar = () => {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold: 0.3 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const accuracy  = useCountUp(987,  1800, visible);
  const records   = useCountUp(50000, 1800, visible);
  const commodities = useCountUp(47, 1200, visible);

  return (
    <div ref={ref} className="ld-stats-bar" data-reveal>
      {[
        { num: `${(accuracy / 10).toFixed(1)}%`, label: 'Detection Accuracy',    suffix: '' },
        { num: records.toLocaleString(),          label: 'Price Records Analyzed', suffix: '+' },
        { num: commodities,                        label: 'Market Commodities',     suffix: '' },
      ].map((s, i) => (
        <div key={i} className="ld-stat-item">
          <span className="ld-stat-num">{s.num}{s.suffix}</span>
          <span className="ld-stat-label">{s.label}</span>
        </div>
      ))}
    </div>
  );
};

// ── Feature cards ─────────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: '🧠',
    title: 'AI Ensemble Models',
    desc: 'Logistic Regression + XGBoost work in concert to catch price anomalies across all market conditions. Configurable ensemble weights for precision tuning.',
    tag: 'ML-Powered',
  },
  {
    icon: '📊',
    title: 'Real-Time Intelligence',
    desc: 'Live market data ingestion with sub-minute processing. Automated alerts notify your team the moment a price deviation is detected.',
    tag: 'Live Data',
  },
  {
    icon: '🔬',
    title: 'Forensic Audit Trail',
    desc: 'Full explainability with SHAP values for every flagged anomaly. Every decision is traceable, defensible, and audit-ready.',
    tag: 'Explainable AI',
  },
];

// ── Pricing tiers ─────────────────────────────────────────────────────────────
const PLANS = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    highlight: false,
    badge: null,
    features: [
      '100 API calls / day',
      '1 user seat',
      'Basic dashboard',
      '7-day data history',
      'Community support',
    ],
    cta: 'Get Started Free',
    ctaTo: '/login',
  },
  {
    name: 'Pro',
    price: '$49',
    period: '/month',
    highlight: true,
    badge: 'Most Popular',
    features: [
      '5,000 API calls / day',
      '10 user seats',
      'Advanced analytics',
      'CSV & Excel exports',
      '90-day data history',
      'Priority support',
      'Custom alerts',
    ],
    cta: 'Start Free Trial',
    ctaTo: '/login',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    highlight: false,
    badge: null,
    features: [
      'Unlimited API calls',
      'Unlimited users',
      'Custom data integration',
      'Full data history',
      'Dedicated account manager',
      '99.9% SLA',
      'On-premise option',
    ],
    cta: 'Contact Sales',
    ctaTo: 'mailto:sales@marketpulse.services',
  },
];

// ── Main Landing component ────────────────────────────────────────────────────
export default function Landing() {
  const { user } = useAuth();
  const navigate  = useNavigate();

  // Redirect logged-in users to app
  useEffect(() => {
    if (user) navigate('/app', { replace: true });
  }, [user, navigate]);

  useScrollReveal();

  return (
    <>
      {/* ── Global styles ── */}
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body { background: #07070d; color: #e2e8f0; font-family: 'Inter', system-ui, -apple-system, sans-serif; }

        /* ── Scroll reveal ── */
        [data-reveal] { opacity: 0; transform: translateY(30px); transition: opacity 0.65s ease, transform 0.65s ease; }
        [data-reveal].revealed { opacity: 1; transform: translateY(0); }

        /* ── Landing page ── */
        .ld-page { min-height: 100vh; background: #07070d; overflow-x: hidden; }

        /* ── Navbar ── */
        .ld-nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
          display: flex; align-items: center; justify-content: space-between;
          padding: 16px 48px;
          background: rgba(7,7,13,0.75);
          backdrop-filter: blur(16px);
          border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .ld-nav-brand { display: flex; align-items: center; gap: 8px; text-decoration: none; }
        .ld-nav-icon  { font-size: 22px; }
        .ld-nav-name  {
          font-size: 18px; font-weight: 800; letter-spacing: -0.4px;
          background: linear-gradient(135deg, #a78bfa, #06b6d4);
          -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        .ld-nav-links { display: flex; align-items: center; gap: 28px; }
        .ld-nav-link  { color: rgba(255,255,255,0.5); text-decoration: none; font-size: 14px; font-weight: 500; transition: color 0.2s; }
        .ld-nav-link:hover { color: #fff; }
        .ld-nav-cta {
          padding: 9px 22px; border-radius: 10px; text-decoration: none;
          font-size: 14px; font-weight: 600; transition: all 0.2s;
          background: linear-gradient(135deg, #8b5cf6, #06b6d4);
          color: #fff; box-shadow: 0 2px 12px rgba(139,92,246,0.35);
        }
        .ld-nav-cta:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(139,92,246,0.5); }

        /* ── Hero ── */
        .ld-hero {
          min-height: 100vh; display: flex; align-items: center;
          padding: 120px 48px 80px;
          position: relative; overflow: hidden;
        }

        /* Animated mesh gradient blobs */
        .ld-blob {
          position: absolute; border-radius: 50%; filter: blur(80px);
          animation: ld-float 8s ease-in-out infinite alternate;
          pointer-events: none;
        }
        .ld-blob-1 {
          width: 520px; height: 520px;
          background: radial-gradient(circle, rgba(139,92,246,0.22) 0%, transparent 70%);
          top: -100px; left: -80px;
          animation-duration: 10s;
        }
        .ld-blob-2 {
          width: 400px; height: 400px;
          background: radial-gradient(circle, rgba(6,182,212,0.16) 0%, transparent 70%);
          top: 20%; right: 5%;
          animation-duration: 12s; animation-delay: -3s;
        }
        .ld-blob-3 {
          width: 320px; height: 320px;
          background: radial-gradient(circle, rgba(236,72,153,0.12) 0%, transparent 70%);
          bottom: 0; left: 30%;
          animation-duration: 9s; animation-delay: -6s;
        }
        @keyframes ld-float {
          from { transform: translate(0,0) scale(1); }
          to   { transform: translate(30px, 20px) scale(1.08); }
        }

        /* Grid overlay */
        .ld-grid-overlay {
          position: absolute; inset: 0; pointer-events: none;
          background-image:
            linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
          background-size: 48px 48px;
        }

        .ld-hero-inner {
          position: relative; z-index: 1; max-width: 1200px; margin: 0 auto;
          display: flex; align-items: center; gap: 64px; width: 100%;
        }
        .ld-hero-text { flex: 1; min-width: 0; }
        .ld-hero-badge {
          display: inline-flex; align-items: center; gap: 8px;
          padding: 6px 14px; border-radius: 100px; margin-bottom: 24px;
          background: rgba(139,92,246,0.12); border: 1px solid rgba(139,92,246,0.3);
          font-size: 12px; font-weight: 600; color: #a78bfa; letter-spacing: 0.5px;
          text-transform: uppercase;
        }
        .ld-hero-badge-dot {
          width: 6px; height: 6px; border-radius: 50%; background: #8b5cf6;
          animation: ld-pulse 1.5s ease-in-out infinite;
        }
        @keyframes ld-pulse {
          0%,100% { opacity: 1; transform: scale(1); }
          50%      { opacity: 0.5; transform: scale(0.75); }
        }
        .ld-h1 {
          font-size: clamp(36px, 4.5vw, 58px); font-weight: 900;
          line-height: 1.08; letter-spacing: -1.5px;
          color: #fff; margin-bottom: 22px;
        }
        .ld-h1-grad {
          background: linear-gradient(135deg, #a78bfa 0%, #06b6d4 60%, #34d399 100%);
          -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        .ld-hero-sub {
          font-size: 17px; line-height: 1.65; color: rgba(255,255,255,0.52);
          max-width: 520px; margin-bottom: 38px;
        }
        .ld-hero-btns { display: flex; gap: 14px; flex-wrap: wrap; }
        .ld-btn-primary {
          padding: 14px 30px; border-radius: 12px; text-decoration: none;
          font-size: 15px; font-weight: 700; transition: all 0.22s;
          background: linear-gradient(135deg, #8b5cf6, #06b6d4);
          color: #fff; box-shadow: 0 4px 24px rgba(139,92,246,0.45);
          border: none; cursor: pointer; display: inline-block;
        }
        .ld-btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(139,92,246,0.55); }
        .ld-btn-outline {
          padding: 14px 30px; border-radius: 12px; text-decoration: none;
          font-size: 15px; font-weight: 700; transition: all 0.22s;
          background: transparent;
          border: 1.5px solid rgba(255,255,255,0.18);
          color: rgba(255,255,255,0.8); cursor: pointer; display: inline-block;
        }
        .ld-btn-outline:hover { border-color: rgba(139,92,246,0.6); color: #fff; transform: translateY(-2px); }

        /* ── Dashboard Mockup ── */
        .ld-mockup-wrap { flex: 0 0 auto; width: min(480px, 45vw); }
        .ld-mockup {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.09);
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 32px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(139,92,246,0.1);
          animation: ld-float-card 6s ease-in-out infinite alternate;
        }
        @keyframes ld-float-card {
          from { transform: translateY(0) rotateY(-2deg) rotateX(1deg); }
          to   { transform: translateY(-12px) rotateY(2deg) rotateX(-1deg); }
        }
        .ld-mockup-header {
          display: flex; align-items: center; gap: 6px;
          padding: 12px 16px;
          background: rgba(255,255,255,0.03);
          border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .ld-mockup-dot {
          width: 10px; height: 10px; border-radius: 50%;
        }
        .ld-mockup-dot.red    { background: #ef4444; }
        .ld-mockup-dot.yellow { background: #f59e0b; }
        .ld-mockup-dot.green  { background: #22c55e; }
        .ld-mockup-title {
          margin-left: 8px; font-size: 11px; color: rgba(255,255,255,0.3);
          font-weight: 500; letter-spacing: 0.3px;
        }
        .ld-mockup-body { padding: 16px; }
        .ld-mini-kpis { display: flex; gap: 8px; margin-bottom: 14px; }
        .ld-mini-kpi {
          flex: 1; background: rgba(255,255,255,0.05); border-radius: 10px;
          padding: 10px 12px; position: relative;
        }
        .ld-mini-kpi-val { display: block; font-size: 16px; font-weight: 800; color: #fff; }
        .ld-mini-kpi-label { display: block; font-size: 9px; color: rgba(255,255,255,0.35); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.4px; }
        .ld-mini-kpi-badge {
          position: absolute; top: 8px; right: 8px;
          font-size: 10px; font-weight: 700;
        }
        .ld-mini-kpi-badge.up      { color: #34d399; }
        .ld-mini-kpi-badge.neutral { color: rgba(255,255,255,0.3); }

        /* Chart */
        .ld-chart {
          height: 110px; display: flex; align-items: flex-end;
          gap: 5px; padding: 0 4px; position: relative;
          background: rgba(0,0,0,0.2); border-radius: 10px; padding: 10px 8px 4px;
        }
        .ld-bar {
          flex: 1; height: var(--h); border-radius: 4px 4px 0 0;
          background: linear-gradient(to top, rgba(139,92,246,0.6), rgba(6,182,212,0.4));
          animation: ld-bar-grow 0.8s ease both;
          min-width: 0;
        }
        .ld-bar.anomaly {
          background: linear-gradient(to top, rgba(239,68,68,0.8), rgba(251,146,60,0.7));
          box-shadow: 0 0 8px rgba(239,68,68,0.5);
        }
        @keyframes ld-bar-grow {
          from { height: 0; opacity: 0; }
          to   { height: var(--h); opacity: 1; }
        }
        .ld-spike {
          position: absolute; top: 4px; width: 1.5px;
          height: 60%; background: rgba(239,68,68,0.7);
          animation: ld-blink 1.2s ease-in-out infinite;
        }
        @keyframes ld-blink { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }
        .ld-chart-legend {
          display: flex; align-items: center; gap: 6px;
          margin-top: 10px; font-size: 10px; color: rgba(255,255,255,0.3);
        }
        .ld-legend-dot { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
        .ld-legend-dot.normal  { background: rgba(139,92,246,0.6); }
        .ld-legend-dot.anomaly { background: rgba(239,68,68,0.8); }

        /* ── Stats bar ── */
        .ld-stats-bar {
          max-width: 1200px; margin: 0 auto;
          display: flex; justify-content: center; gap: 0;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 20px; overflow: hidden;
        }
        .ld-stat-item {
          flex: 1; text-align: center; padding: 40px 20px;
          border-right: 1px solid rgba(255,255,255,0.06);
          position: relative;
        }
        .ld-stat-item:last-child { border-right: none; }
        .ld-stat-num {
          display: block; font-size: clamp(28px, 3.5vw, 44px);
          font-weight: 900; letter-spacing: -1px;
          background: linear-gradient(135deg, #a78bfa, #06b6d4);
          -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
          margin-bottom: 8px;
        }
        .ld-stat-label { display: block; font-size: 13px; color: rgba(255,255,255,0.45); font-weight: 500; }

        /* ── Section wrapper ── */
        .ld-section { padding: 100px 48px; max-width: 1200px; margin: 0 auto; }
        .ld-section-tag {
          display: inline-block; padding: 5px 14px; border-radius: 100px; margin-bottom: 14px;
          background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.25);
          font-size: 11px; font-weight: 700; color: #a78bfa; letter-spacing: 1px; text-transform: uppercase;
        }
        .ld-section-title {
          font-size: clamp(26px, 3vw, 40px); font-weight: 900; color: #fff;
          letter-spacing: -0.8px; margin-bottom: 14px;
        }
        .ld-section-sub { font-size: 16px; color: rgba(255,255,255,0.45); max-width: 520px; line-height: 1.65; }

        /* ── Feature cards ── */
        .ld-features-grid {
          display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 24px; margin-top: 56px;
        }
        .ld-feature-card {
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 20px; padding: 36px 32px;
          transition: border-color 0.25s, transform 0.25s, box-shadow 0.25s;
          position: relative; overflow: hidden;
        }
        .ld-feature-card::before {
          content: ''; position: absolute; inset: 0;
          background: linear-gradient(135deg, rgba(139,92,246,0.06), transparent 60%);
          opacity: 0; transition: opacity 0.3s;
        }
        .ld-feature-card:hover { border-color: rgba(139,92,246,0.35); transform: translateY(-4px); box-shadow: 0 16px 40px rgba(0,0,0,0.3); }
        .ld-feature-card:hover::before { opacity: 1; }
        .ld-feature-icon { font-size: 40px; margin-bottom: 20px; display: block; }
        .ld-feature-tag {
          display: inline-block; padding: 3px 10px; border-radius: 6px; margin-bottom: 12px;
          background: rgba(139,92,246,0.15); font-size: 10px; font-weight: 700;
          color: #a78bfa; letter-spacing: 0.8px; text-transform: uppercase;
        }
        .ld-feature-title { font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 12px; }
        .ld-feature-desc  { font-size: 14px; color: rgba(255,255,255,0.5); line-height: 1.7; }

        /* ── Pricing ── */
        .ld-pricing-grid {
          display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 24px; margin-top: 56px; align-items: start;
        }
        .ld-plan-card {
          border-radius: 22px; padding: 36px 30px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08);
          transition: transform 0.25s, box-shadow 0.25s;
          position: relative;
        }
        .ld-plan-card:hover { transform: translateY(-4px); box-shadow: 0 20px 50px rgba(0,0,0,0.4); }
        .ld-plan-card.highlight {
          background: rgba(139,92,246,0.07);
          border: 1.5px solid rgba(139,92,246,0.45);
          box-shadow: 0 0 0 1px rgba(139,92,246,0.15), 0 20px 60px rgba(139,92,246,0.15);
          transform: scale(1.03);
        }
        .ld-plan-card.highlight:hover { transform: scale(1.03) translateY(-4px); }
        .ld-plan-badge {
          position: absolute; top: -14px; left: 50%; transform: translateX(-50%);
          padding: 5px 18px; border-radius: 100px;
          background: linear-gradient(135deg, #8b5cf6, #06b6d4);
          font-size: 11px; font-weight: 700; color: #fff; white-space: nowrap;
          box-shadow: 0 4px 16px rgba(139,92,246,0.5);
        }
        .ld-plan-name  { font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
        .ld-plan-price {
          font-size: 48px; font-weight: 900; color: #fff; letter-spacing: -2px; line-height: 1;
        }
        .ld-plan-price .period { font-size: 16px; font-weight: 500; color: rgba(255,255,255,0.4); letter-spacing: 0; }
        .ld-plan-features { list-style: none; margin: 24px 0 28px; }
        .ld-plan-features li {
          display: flex; align-items: center; gap: 10px;
          font-size: 14px; color: rgba(255,255,255,0.65); padding: 7px 0;
          border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .ld-plan-features li::before { content: '✓'; color: #34d399; font-weight: 700; flex-shrink: 0; }
        .ld-plan-cta {
          display: block; width: 100%; padding: 13px 0; border-radius: 12px;
          text-align: center; text-decoration: none; font-size: 14px; font-weight: 700;
          transition: all 0.2s; border: none; cursor: pointer;
        }
        .ld-plan-cta.primary {
          background: linear-gradient(135deg, #8b5cf6, #06b6d4);
          color: #fff; box-shadow: 0 4px 20px rgba(139,92,246,0.4);
        }
        .ld-plan-cta.primary:hover { box-shadow: 0 6px 28px rgba(139,92,246,0.55); transform: translateY(-1px); }
        .ld-plan-cta.outline {
          background: transparent; color: rgba(255,255,255,0.65);
          border: 1.5px solid rgba(255,255,255,0.12);
        }
        .ld-plan-cta.outline:hover { border-color: rgba(255,255,255,0.3); color: #fff; }

        /* ── Stats section wrapper ── */
        .ld-stats-section { padding: 0 48px 100px; }

        /* ── Footer ── */
        .ld-footer {
          border-top: 1px solid rgba(255,255,255,0.06);
          padding: 60px 48px 40px;
          background: rgba(0,0,0,0.3);
        }
        .ld-footer-inner {
          max-width: 1200px; margin: 0 auto;
          display: flex; gap: 60px; flex-wrap: wrap;
        }
        .ld-footer-brand { flex: 0 0 240px; }
        .ld-footer-brand-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
        .ld-footer-brand-icon { font-size: 22px; }
        .ld-footer-brand-name {
          font-size: 18px; font-weight: 800;
          background: linear-gradient(135deg, #a78bfa, #06b6d4);
          -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        .ld-footer-tagline { font-size: 13px; color: rgba(255,255,255,0.35); line-height: 1.6; }
        .ld-footer-col { flex: 1; min-width: 140px; }
        .ld-footer-col-title { font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }
        .ld-footer-link { display: block; color: rgba(255,255,255,0.4); font-size: 13.5px; text-decoration: none; margin-bottom: 10px; transition: color 0.2s; }
        .ld-footer-link:hover { color: rgba(255,255,255,0.8); }
        .ld-footer-bottom {
          max-width: 1200px; margin: 40px auto 0;
          display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
          border-top: 1px solid rgba(255,255,255,0.05); padding-top: 24px;
          font-size: 12.5px; color: rgba(255,255,255,0.25);
        }

        /* ── Responsive ── */
        @media (max-width: 900px) {
          .ld-nav { padding: 14px 24px; }
          .ld-nav-links { gap: 16px; }
          .ld-hero { padding: 100px 24px 60px; }
          .ld-hero-inner { flex-direction: column; }
          .ld-mockup-wrap { width: 100%; }
          .ld-section, .ld-stats-section { padding-left: 24px; padding-right: 24px; }
          .ld-footer { padding: 48px 24px 32px; }
          .ld-footer-inner { gap: 36px; }
          .ld-footer-brand { flex: 0 0 100%; }
          .ld-plan-card.highlight { transform: scale(1); }
          .ld-plan-card.highlight:hover { transform: translateY(-4px); }
          .ld-stats-bar { flex-direction: column; }
          .ld-stat-item { border-right: none; border-bottom: 1px solid rgba(255,255,255,0.06); }
          .ld-stat-item:last-child { border-bottom: none; }
        }
        @media (max-width: 600px) {
          .ld-nav-links .ld-nav-link { display: none; }
          .ld-hero-btns { flex-direction: column; }
          .ld-btn-primary, .ld-btn-outline { text-align: center; }
        }
      `}</style>

      <div className="ld-page">
        {/* ── Navbar ── */}
        <nav className="ld-nav">
          <Link to="/" className="ld-nav-brand">
            <span className="ld-nav-icon">📈</span>
            <span className="ld-nav-name">MarketPulse</span>
          </Link>
          <div className="ld-nav-links">
            <a href="#features" className="ld-nav-link">Features</a>
            <a href="#pricing"  className="ld-nav-link">Pricing</a>
            <a href="https://docs.marketpulse.services" className="ld-nav-link" target="_blank" rel="noreferrer">Docs</a>
            <Link to="/login" className="ld-nav-cta">Sign In →</Link>
          </div>
        </nav>

        {/* ── Hero ── */}
        <section className="ld-hero">
          {/* Animated blobs */}
          <div className="ld-blob ld-blob-1" />
          <div className="ld-blob ld-blob-2" />
          <div className="ld-blob ld-blob-3" />
          {/* Grid */}
          <div className="ld-grid-overlay" />

          <div className="ld-hero-inner">
            <div className="ld-hero-text">
              <div className="ld-hero-badge">
                <div className="ld-hero-badge-dot" />
                Now in production — 47 markets tracked live
              </div>
              <h1 className="ld-h1">
                Detect Food Price Anomalies{' '}
                <span className="ld-h1-grad">Before They Become Crises</span>
              </h1>
              <p className="ld-hero-sub">
                AI-powered market intelligence for commodity traders, NGOs, and government analysts.
                Catch price spikes, supply shocks, and market manipulation in real time.
              </p>
              <div className="ld-hero-btns">
                <Link to="/login" className="ld-btn-primary">Start Free Trial →</Link>
                <a href="#features" className="ld-btn-outline">View Demo</a>
              </div>
            </div>

            <div className="ld-mockup-wrap">
              <DashboardMockup />
            </div>
          </div>
        </section>

        {/* ── Stats bar ── */}
        <div className="ld-stats-section">
          <StatsBar />
        </div>

        {/* ── Features ── */}
        <section id="features" className="ld-section">
          <span className="ld-section-tag" data-reveal>Capabilities</span>
          <h2 className="ld-section-title" data-reveal>Intelligence at every layer</h2>
          <p className="ld-section-sub" data-reveal>
            From raw market data to actionable anomaly alerts — fully automated, fully explainable.
          </p>
          <div className="ld-features-grid">
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className="ld-feature-card"
                data-reveal
                style={{ transitionDelay: `${i * 0.1}s` }}
              >
                <span className="ld-feature-icon">{f.icon}</span>
                <span className="ld-feature-tag">{f.tag}</span>
                <h3 className="ld-feature-title">{f.title}</h3>
                <p className="ld-feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Pricing ── */}
        <section id="pricing" style={{ padding: '100px 48px', background: 'rgba(0,0,0,0.2)' }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
            <span className="ld-section-tag" data-reveal>Pricing</span>
            <h2 className="ld-section-title" data-reveal>Simple, transparent pricing</h2>
            <p className="ld-section-sub" data-reveal>Start free. Scale as you grow. No surprises.</p>

            <div className="ld-pricing-grid" style={{ marginTop: '64px' }}>
              {PLANS.map((plan, i) => (
                <div
                  key={plan.name}
                  className={`ld-plan-card ${plan.highlight ? 'highlight' : ''}`}
                  data-reveal
                  style={{ transitionDelay: `${i * 0.1}s` }}
                >
                  {plan.badge && <div className="ld-plan-badge">{plan.badge}</div>}
                  <p className="ld-plan-name">{plan.name}</p>
                  <div className="ld-plan-price">
                    {plan.price}
                    {plan.period && <span className="period">{plan.period}</span>}
                  </div>
                  <ul className="ld-plan-features">
                    {plan.features.map((f) => <li key={f}>{f}</li>)}
                  </ul>
                  {plan.ctaTo.startsWith('mailto') ? (
                    <a href={plan.ctaTo} className="ld-plan-cta outline">{plan.cta}</a>
                  ) : (
                    <Link
                      to={plan.ctaTo}
                      className={`ld-plan-cta ${plan.highlight ? 'primary' : 'outline'}`}
                    >
                      {plan.cta}
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Footer ── */}
        <footer className="ld-footer">
          <div className="ld-footer-inner">
            <div className="ld-footer-brand">
              <div className="ld-footer-brand-row">
                <span className="ld-footer-brand-icon">📈</span>
                <span className="ld-footer-brand-name">MarketPulse AI</span>
              </div>
              <p className="ld-footer-tagline">
                AI-powered food price intelligence for traders, analysts, and policymakers worldwide.
              </p>
            </div>

            <div className="ld-footer-col">
              <p className="ld-footer-col-title">Product</p>
              <a href="#features" className="ld-footer-link">Features</a>
              <a href="#pricing"  className="ld-footer-link">Pricing</a>
              <Link to="/login"   className="ld-footer-link">Dashboard</Link>
              <a href="https://docs.marketpulse.services" className="ld-footer-link" target="_blank" rel="noreferrer">API Docs</a>
            </div>

            <div className="ld-footer-col">
              <p className="ld-footer-col-title">Company</p>
              <a href="https://marketpulse.services/about"   className="ld-footer-link">About</a>
              <a href="https://marketpulse.services/blog"    className="ld-footer-link">Blog</a>
              <a href="https://marketpulse.services/careers" className="ld-footer-link">Careers</a>
              <a href="mailto:hello@marketpulse.services"    className="ld-footer-link">Contact</a>
            </div>

            <div className="ld-footer-col">
              <p className="ld-footer-col-title">Legal</p>
              <a href="https://marketpulse.services/privacy" className="ld-footer-link">Privacy Policy</a>
              <a href="https://marketpulse.services/terms"   className="ld-footer-link">Terms of Service</a>
              <a href="https://marketpulse.services/sla"     className="ld-footer-link">SLA</a>
            </div>
          </div>

          <div className="ld-footer-bottom">
            <span>© 2025 MarketPulse AI. All rights reserved.</span>
            <span>Built with ❤️ for food security analysts worldwide</span>
          </div>
        </footer>
      </div>
    </>
  );
}
