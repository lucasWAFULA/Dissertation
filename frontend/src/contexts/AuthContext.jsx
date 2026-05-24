import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import axios from 'axios';
import { auth, isFirebaseConfigured } from '../firebase';

// ── Axios base URL ─────────────────────────────────────────────────────────────
axios.defaults.baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.marketpulse.services');

// ── Context ────────────────────────────────────────────────────────────────────
const AuthContext = createContext(null);

/** Hook — must be used inside <AuthProvider> */
export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};

// ── Provider ───────────────────────────────────────────────────────────────────
export const AuthProvider = ({ children }) => {
  const [user, setUser]         = useState(null);
  const [token, setToken]       = useState(null);
  const [loading, setLoading]   = useState(true);
  const [isAdmin, setIsAdmin]   = useState(false);
  const [userPlan, setUserPlan] = useState('free');

  const refreshTimerRef = useRef(null);

  // ── Refresh the ID token and sync it to axios headers ──────────────────────
  const refreshToken = async (firebaseUser) => {
    if (!firebaseUser) {
      setToken(null);
      setIsAdmin(false);
      setUserPlan('free');
      axios.defaults.headers.common['Authorization'] = '';
      return;
    }

    try {
      const idToken = await firebaseUser.getIdToken(/* forceRefresh */ true);
      setToken(idToken);
      axios.defaults.headers.common['Authorization'] = `Bearer ${idToken}`;

      // Read custom claims for role + plan
      const result = await firebaseUser.getIdTokenResult();
      setIsAdmin(result.claims.role === 'admin');
      setUserPlan(result.claims.plan || 'free');
    } catch (err) {
      console.error('[AuthContext] Token refresh failed:', err);
    }
  };

  // ── Schedule automatic token refresh every 50 minutes ─────────────────────
  const scheduleRefresh = (firebaseUser) => {
    if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    if (!firebaseUser) return;

    refreshTimerRef.current = setInterval(() => {
      refreshToken(firebaseUser);
    }, 50 * 60 * 1000); // 50 minutes
  };

  // ── Firebase auth state listener ──────────────────────────────────────────
  useEffect(() => {
    if (!isFirebaseConfigured) {
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      await refreshToken(firebaseUser);
      scheduleRefresh(firebaseUser);
      setLoading(false);
    });

    return () => {
      if (unsubscribe) unsubscribe();
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = {
    user,
    token,
    loading,
    isAdmin,
    userPlan,
    /** Force-refresh the token on demand (e.g. after plan upgrade) */
    refreshToken: () => refreshToken(user),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
