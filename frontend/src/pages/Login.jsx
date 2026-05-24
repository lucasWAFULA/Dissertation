import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  signInWithGoogle,
  signInWithEmail,
  registerWithEmail,
  sendPasswordReset,
} from '../firebase';
import { useAuth } from '../contexts/AuthContext';

// ── Google Logo SVG ────────────────────────────────────────────────────────────
const GoogleLogo = () => (
  <svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.36-8.16 2.36-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    <path fill="none" d="M0 0h48v48H0z"/>
  </svg>
);

// ── Animated particle canvas ───────────────────────────────────────────────────
const ParticleBackground = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let animId;
    let particles = [];
    const NUM = 60;

    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    class Particle {
      constructor() { this.reset(); }
      reset() {
        this.x  = Math.random() * canvas.width;
        this.y  = Math.random() * canvas.height;
        this.r  = Math.random() * 1.6 + 0.4;
        this.vx = (Math.random() - 0.5) * 0.35;
        this.vy = (Math.random() - 0.5) * 0.35;
        this.alpha = Math.random() * 0.5 + 0.1;
      }
      step() {
        this.x += this.vx;
        this.y += this.vy;
        if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) this.reset();
      }
      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(139,92,246,${this.alpha})`;
        ctx.fill();
      }
    }

    const drawConnections = () => {
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(139,92,246,${0.12 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }
    };

    resize();
    for (let i = 0; i < NUM; i++) particles.push(new Particle());
    window.addEventListener('resize', resize);

    const loop = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => { p.step(); p.draw(); });
      drawConnections();
      animId = requestAnimationFrame(loop);
    };
    loop();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}
    />
  );
};

// ── Inline styles object (all vanilla CSS via React style props) ───────────────
const S = {
  page: {
    minHeight: '100vh',
    background: 'radial-gradient(ellipse at 20% 50%, rgba(91,33,182,0.18) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(6,182,212,0.12) 0%, transparent 55%), #0a0a0f',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
    position: 'relative',
    overflow: 'hidden',
  },
  card: {
    position: 'relative',
    zIndex: 1,
    width: '100%',
    maxWidth: '440px',
    margin: '24px 16px',
    background: 'rgba(255,255,255,0.04)',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '24px',
    padding: '44px 40px 36px',
    boxShadow: '0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(139,92,246,0.08), inset 0 1px 0 rgba(255,255,255,0.06)',
  },
  brandRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    marginBottom: '8px',
  },
  brandIcon: { fontSize: '32px', lineHeight: 1 },
  brandName: {
    fontSize: '26px',
    fontWeight: 800,
    background: 'linear-gradient(135deg, #a78bfa 0%, #06b6d4 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    letterSpacing: '-0.5px',
  },
  tagline: {
    textAlign: 'center',
    color: 'rgba(255,255,255,0.4)',
    fontSize: '12.5px',
    letterSpacing: '0.4px',
    marginBottom: '28px',
    textTransform: 'uppercase',
  },
  tabs: {
    display: 'flex',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '12px',
    padding: '4px',
    marginBottom: '28px',
    gap: '4px',
  },
  tabBtn: (active) => ({
    flex: 1,
    padding: '9px 0',
    border: 'none',
    borderRadius: '9px',
    cursor: 'pointer',
    fontSize: '13.5px',
    fontWeight: 600,
    transition: 'all 0.22s ease',
    background: active
      ? 'linear-gradient(135deg, rgba(139,92,246,0.85), rgba(6,182,212,0.7))'
      : 'transparent',
    color: active ? '#fff' : 'rgba(255,255,255,0.45)',
    boxShadow: active ? '0 2px 12px rgba(139,92,246,0.35)' : 'none',
  }),
  googleBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '12px 0',
    background: '#fff',
    border: 'none',
    borderRadius: '12px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    color: '#3c4043',
    letterSpacing: '0.2px',
    transition: 'transform 0.18s ease, box-shadow 0.18s ease',
    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    margin: '20px 0',
  },
  dividerLine: { flex: 1, height: '1px', background: 'rgba(255,255,255,0.08)' },
  dividerText: { color: 'rgba(255,255,255,0.25)', fontSize: '12px', whiteSpace: 'nowrap' },
  formGroup: { marginBottom: '14px' },
  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 600,
    color: 'rgba(255,255,255,0.55)',
    marginBottom: '6px',
    letterSpacing: '0.4px',
    textTransform: 'uppercase',
  },
  input: {
    width: '100%',
    padding: '12px 14px',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '10px',
    color: '#fff',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    boxSizing: 'border-box',
  },
  forgotLink: {
    display: 'block',
    textAlign: 'right',
    color: 'rgba(139,92,246,0.8)',
    fontSize: '12px',
    textDecoration: 'none',
    marginTop: '4px',
    marginBottom: '4px',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    fontFamily: 'inherit',
  },
  checkRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    margin: '10px 0 6px',
  },
  checkLabel: { color: 'rgba(255,255,255,0.5)', fontSize: '12.5px', lineHeight: 1.5 },
  submitBtn: (loading) => ({
    width: '100%',
    padding: '14px 0',
    marginTop: '10px',
    border: 'none',
    borderRadius: '12px',
    cursor: loading ? 'not-allowed' : 'pointer',
    fontSize: '15px',
    fontWeight: 700,
    letterSpacing: '0.3px',
    background: loading
      ? 'rgba(139,92,246,0.35)'
      : 'linear-gradient(135deg, #8b5cf6, #06b6d4)',
    color: '#fff',
    transition: 'opacity 0.2s, transform 0.2s',
    opacity: loading ? 0.7 : 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    boxShadow: loading ? 'none' : '0 4px 20px rgba(139,92,246,0.4)',
  }),
  errorBanner: {
    background: 'rgba(239,68,68,0.12)',
    border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: '10px',
    padding: '10px 14px',
    color: '#fca5a5',
    fontSize: '13px',
    lineHeight: 1.5,
    marginTop: '12px',
    animation: 'lg-shake 0.35s ease',
  },
  successBanner: {
    background: 'rgba(52,211,153,0.1)',
    border: '1px solid rgba(52,211,153,0.25)',
    borderRadius: '10px',
    padding: '10px 14px',
    color: '#6ee7b7',
    fontSize: '13px',
    lineHeight: 1.5,
    marginTop: '12px',
  },
  backLink: {
    display: 'block',
    textAlign: 'center',
    marginTop: '24px',
    color: 'rgba(255,255,255,0.3)',
    fontSize: '12.5px',
    textDecoration: 'none',
    transition: 'color 0.2s',
  },
};

// ── Tiny spinner SVG ───────────────────────────────────────────────────────────
const Spinner = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
    style={{ animation: 'lg-spin 0.75s linear infinite', flexShrink: 0 }}>
    <circle cx="12" cy="12" r="10" strokeOpacity="0.25"/>
    <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/>
  </svg>
);

// ── Main Login component ───────────────────────────────────────────────────────
export default function Login() {
  const { user } = useAuth();
  const navigate  = useNavigate();
  const location  = useLocation();
  const from      = location.state?.from?.pathname || '/app';

  const [tab, setTab]               = useState('signin');
  const [name, setName]             = useState('');
  const [email, setEmail]           = useState('');
  const [password, setPassword]     = useState('');
  const [confirm, setConfirm]       = useState('');
  const [terms, setTerms]           = useState(false);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [success, setSuccess]       = useState('');
  const [focusField, setFocusField] = useState(null);
  const [forgotMode, setForgotMode] = useState(false);

  // Redirect if already logged-in
  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user, navigate, from]);

  const clearMessages = () => { setError(''); setSuccess(''); };

  const friendlyError = (code) => {
    const map = {
      'auth/user-not-found':       'No account found with this email.',
      'auth/wrong-password':       'Incorrect password. Try again.',
      'auth/email-already-in-use': 'An account with this email already exists.',
      'auth/weak-password':        'Password must be at least 6 characters.',
      'auth/invalid-email':        'Please enter a valid email address.',
      'auth/too-many-requests':    'Too many failed attempts. Please try again later.',
      'auth/popup-closed-by-user': 'Google sign-in was cancelled.',
      'auth/network-request-failed': 'Network error — check your connection.',
    };
    return map[code] || 'Something went wrong. Please try again.';
  };

  const handleGoogleSignIn = async () => {
    clearMessages();
    setLoading(true);
    try {
      await signInWithGoogle();
      // onAuthStateChanged will update user → useEffect redirects
    } catch (err) {
      setError(friendlyError(err.code));
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async () => {
    clearMessages();
    if (!email) { setError('Enter your email address above first.'); return; }
    setLoading(true);
    try {
      await sendPasswordReset(email);
      setSuccess(`Password reset link sent to ${email}. Check your inbox.`);
      setForgotMode(false);
    } catch (err) {
      setError(friendlyError(err.code));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearMessages();

    if (tab === 'register') {
      if (password !== confirm) { setError('Passwords do not match.'); return; }
      if (!terms) { setError('Please accept the terms of service to continue.'); return; }
    }

    setLoading(true);
    try {
      if (tab === 'signin') {
        await signInWithEmail(email, password);
      } else {
        await registerWithEmail(email, password);
        setSuccess('Account created! Check your inbox for a verification email.');
      }
    } catch (err) {
      setError(friendlyError(err.code));
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = (field) => ({
    ...S.input,
    borderColor: focusField === field ? 'rgba(139,92,246,0.7)' : 'rgba(255,255,255,0.1)',
    boxShadow: focusField === field ? '0 0 0 3px rgba(139,92,246,0.18)' : 'none',
  });

  return (
    <>
      <style>{`
        @keyframes lg-spin  { to { transform: rotate(360deg); } }
        @keyframes lg-shake {
          0%,100% { transform: translateX(0); }
          20%     { transform: translateX(-5px); }
          40%     { transform: translateX(5px); }
          60%     { transform: translateX(-4px); }
          80%     { transform: translateX(4px); }
        }
        @keyframes lg-fadein {
          from { opacity: 0; transform: translateY(16px) scale(0.98); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        .lg-card { animation: lg-fadein 0.45s cubic-bezier(0.22,1,0.36,1) both; }
        .lg-google-btn:hover { transform: scale(1.02); box-shadow: 0 4px 20px rgba(0,0,0,0.4) !important; }
        .lg-submit-btn:hover:not(:disabled) { transform: translateY(-1px); opacity: 0.92; }
        .lg-input::placeholder { color: rgba(255,255,255,0.2); }
        .lg-input::-webkit-autofill,
        .lg-input::-webkit-autofill:hover,
        .lg-input::-webkit-autofill:focus {
          -webkit-text-fill-color: #fff;
          -webkit-box-shadow: 0 0 0 1000px rgba(30,20,60,0.95) inset;
          transition: background-color 5000s ease-in-out 0s;
        }
        .lg-back-link:hover { color: rgba(255,255,255,0.6) !important; }
        .lg-tab-btn { font-family: inherit; }
        .lg-forgot { transition: color 0.2s; }
        .lg-forgot:hover { color: #a78bfa !important; }
        .lg-checkbox { accent-color: #8b5cf6; width: 15px; height: 15px; cursor: pointer; flex-shrink: 0; }
      `}</style>

      <div style={S.page}>
        <ParticleBackground />

        <div style={S.card} className="lg-card">
          {/* Brand */}
          <div style={S.brandRow}>
            <span style={S.brandIcon}>📈</span>
            <span style={S.brandName}>MarketPulse</span>
          </div>
          <p style={S.tagline}>AI-Powered Food Price Intelligence</p>

          {/* Tabs */}
          <div style={S.tabs}>
            {[['signin', 'Sign In'], ['register', 'Create Account']].map(([id, label]) => (
              <button
                key={id}
                className="lg-tab-btn"
                style={S.tabBtn(tab === id)}
                onClick={() => { setTab(id); clearMessages(); setForgotMode(false); }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Google SSO */}
          <button
            className="lg-google-btn"
            style={S.googleBtn}
            onClick={handleGoogleSignIn}
            disabled={loading}
          >
            <GoogleLogo />
            Continue with Google
          </button>

          {/* Divider */}
          <div style={S.divider}>
            <div style={S.dividerLine} />
            <span style={S.dividerText}>or continue with email</span>
            <div style={S.dividerLine} />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate>
            {/* Name (register only) */}
            {tab === 'register' && (
              <div style={S.formGroup}>
                <label style={S.label}>Full Name</label>
                <input
                  className="lg-input"
                  style={inputStyle('name')}
                  type="text"
                  placeholder="Jane Smith"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onFocus={() => setFocusField('name')}
                  onBlur={() => setFocusField(null)}
                  autoComplete="name"
                />
              </div>
            )}

            {/* Email */}
            <div style={S.formGroup}>
              <label style={S.label}>Email</label>
              <input
                className="lg-input"
                style={inputStyle('email')}
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onFocus={() => setFocusField('email')}
                onBlur={() => setFocusField(null)}
                autoComplete="email"
                required
              />
            </div>

            {/* Password */}
            {!forgotMode && (
              <div style={S.formGroup}>
                <label style={S.label}>Password</label>
                <input
                  className="lg-input"
                  style={inputStyle('password')}
                  type="password"
                  placeholder={tab === 'signin' ? '••••••••' : 'Min. 6 characters'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusField('password')}
                  onBlur={() => setFocusField(null)}
                  autoComplete={tab === 'signin' ? 'current-password' : 'new-password'}
                  required
                />
              </div>
            )}

            {/* Confirm password (register) */}
            {tab === 'register' && !forgotMode && (
              <div style={S.formGroup}>
                <label style={S.label}>Confirm Password</label>
                <input
                  className="lg-input"
                  style={inputStyle('confirm')}
                  type="password"
                  placeholder="••••••••"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  onFocus={() => setFocusField('confirm')}
                  onBlur={() => setFocusField(null)}
                  autoComplete="new-password"
                  required
                />
              </div>
            )}

            {/* Forgot password link (sign-in only) */}
            {tab === 'signin' && !forgotMode && (
              <button
                type="button"
                className="lg-forgot"
                style={S.forgotLink}
                onClick={() => { setForgotMode(true); clearMessages(); }}
              >
                Forgot password?
              </button>
            )}

            {/* Forgot password mode CTA */}
            {forgotMode && (
              <>
                <button
                  type="button"
                  style={{ ...S.forgotLink, color: 'rgba(255,255,255,0.35)', textAlign: 'left', marginBottom: '8px' }}
                  onClick={() => { setForgotMode(false); clearMessages(); }}
                >
                  ← Back to sign in
                </button>
                <button
                  type="button"
                  className="lg-submit-btn"
                  style={S.submitBtn(loading)}
                  onClick={handleForgotPassword}
                  disabled={loading}
                >
                  {loading ? <Spinner /> : null}
                  {loading ? 'Sending…' : 'Send reset link'}
                </button>
              </>
            )}

            {/* Terms (register) */}
            {tab === 'register' && !forgotMode && (
              <div style={S.checkRow}>
                <input
                  type="checkbox"
                  id="terms"
                  className="lg-checkbox"
                  checked={terms}
                  onChange={(e) => setTerms(e.target.checked)}
                />
                <label htmlFor="terms" style={S.checkLabel}>
                  I agree to the{' '}
                  <a href="https://marketpulse.services/terms" target="_blank" rel="noreferrer"
                    style={{ color: '#a78bfa', textDecoration: 'none' }}>
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a href="https://marketpulse.services/privacy" target="_blank" rel="noreferrer"
                    style={{ color: '#a78bfa', textDecoration: 'none' }}>
                    Privacy Policy
                  </a>
                </label>
              </div>
            )}

            {/* Submit */}
            {!forgotMode && (
              <button
                type="submit"
                className="lg-submit-btn"
                style={S.submitBtn(loading)}
                disabled={loading}
              >
                {loading ? <Spinner /> : null}
                {loading
                  ? (tab === 'signin' ? 'Signing in…' : 'Creating account…')
                  : (tab === 'signin' ? 'Sign In' : 'Create Account')}
              </button>
            )}

            {/* Error / Success banners */}
            {error   && <div style={S.errorBanner}  role="alert">⚠ {error}</div>}
            {success && <div style={S.successBanner} role="status">✓ {success}</div>}
          </form>

          {/* Back link */}
          <Link to="/" style={S.backLink} className="lg-back-link">
            ← Back to marketpulse.services
          </Link>
        </div>
      </div>
    </>
  );
}
