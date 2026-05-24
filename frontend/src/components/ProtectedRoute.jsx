import React, { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { resendVerification } from '../firebase';

// ── Loading Spinner ────────────────────────────────────────────────────────────
const spinnerStyles = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    background: '#0a0a0f',
    gap: '20px',
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: '3px solid rgba(139, 92, 246, 0.15)',
    borderTop: '3px solid #8b5cf6',
    borderRadius: '50%',
    animation: 'pr-spin 0.9s linear infinite',
  },
  text: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: '14px',
    fontFamily: 'system-ui, sans-serif',
    letterSpacing: '0.5px',
  },
};

// ── Verify-Email Notice ────────────────────────────────────────────────────────
const VerifyEmailNotice = ({ user }) => {
  const [sent, setSent]     = useState(false);
  const [error, setError]   = useState(null);
  const [busy, setBusy]     = useState(false);

  const handleResend = async () => {
    setBusy(true);
    setError(null);
    try {
      await resendVerification();
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <style>{`
        @keyframes pr-spin { to { transform: rotate(360deg); } }
        @keyframes pr-fadein { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .pr-verify-card {
          animation: pr-fadein 0.4s ease;
          display: flex; flex-direction: column; align-items: center;
          gap: 18px; max-width: 420px; width: 90%;
          background: rgba(255,255,255,0.05);
          border: 1px solid rgba(139,92,246,0.25);
          border-radius: 20px; padding: 48px 40px;
          backdrop-filter: blur(20px);
          font-family: system-ui, sans-serif;
          text-align: center;
        }
        .pr-verify-icon { font-size: 52px; line-height: 1; }
        .pr-verify-title { color: #fff; font-size: 22px; font-weight: 700; margin: 0; }
        .pr-verify-sub { color: rgba(255,255,255,0.55); font-size: 14px; line-height: 1.6; margin: 0; }
        .pr-verify-email { color: #a78bfa; font-weight: 600; word-break: break-all; }
        .pr-verify-btn {
          margin-top: 8px;
          padding: 12px 28px; border: none; border-radius: 10px; cursor: pointer;
          font-size: 14px; font-weight: 600; letter-spacing: 0.3px;
          background: linear-gradient(135deg, #8b5cf6, #06b6d4);
          color: #fff; transition: opacity 0.2s, transform 0.2s;
        }
        .pr-verify-btn:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
        .pr-verify-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .pr-verify-success { color: #34d399; font-size: 13px; font-weight: 500; }
        .pr-verify-error  { color: #f87171; font-size: 13px; }
        .pr-back-link { color: rgba(255,255,255,0.35); font-size: 12px; cursor: pointer; text-decoration: underline; }
        .pr-back-link:hover { color: rgba(255,255,255,0.6); }
      `}</style>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:'100vh', background:'#0a0a0f' }}>
        <div className="pr-verify-card">
          <div className="pr-verify-icon">📧</div>
          <h2 className="pr-verify-title">Verify your email</h2>
          <p className="pr-verify-sub">
            We sent a verification link to<br />
            <span className="pr-verify-email">{user?.email}</span>
            <br /><br />
            Please check your inbox and click the link to activate your account before continuing.
          </p>

          {sent && <p className="pr-verify-success">✓ Verification email resent successfully!</p>}
          {error && <p className="pr-verify-error">{error}</p>}

          <button
            className="pr-verify-btn"
            onClick={handleResend}
            disabled={busy || sent}
          >
            {busy ? 'Sending…' : sent ? 'Email sent ✓' : 'Resend verification email'}
          </button>

          <span className="pr-back-link" onClick={() => window.location.reload()}>
            I've verified — refresh page
          </span>
        </div>
      </div>
    </>
  );
};

// ── ProtectedRoute ─────────────────────────────────────────────────────────────
const ProtectedRoute = ({ children, requireAdmin = false }) => {
  const { user, loading, isAdmin } = useAuth();
  const location = useLocation();

  // 1. Auth state still resolving → spinner
  if (loading) {
    return (
      <>
        <style>{`@keyframes pr-spin { to { transform: rotate(360deg); } }`}</style>
        <div style={spinnerStyles.wrapper}>
          <div style={spinnerStyles.spinner} />
          <span style={spinnerStyles.text}>Loading…</span>
        </div>
      </>
    );
  }

  // 2. Not logged in → redirect to /login, preserve destination
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 3. Google sign-ins are always treated as verified.
  //    Email/password users must verify their address.
  const isGoogleUser = user.providerData?.some((p) => p.providerId === 'google.com');
  if (!isGoogleUser && !user.emailVerified) {
    return <VerifyEmailNotice user={user} />;
  }

  // 4. Admin-only route guard
  if (requireAdmin && !isAdmin) {
    return <Navigate to="/app" replace />;
  }

  // 5. All good
  return children;
};

export default ProtectedRoute;
