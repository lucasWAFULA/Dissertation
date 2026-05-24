import { initializeApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  sendEmailVerification,
  sendPasswordResetEmail,
} from 'firebase/auth';

// Firebase config — all sensitive values come from Vite env vars (injected via GitHub Secrets at build time)
const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN        || 'marketpulseai-496112.firebaseapp.com',
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID         || 'marketpulseai-496112',
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET     || 'marketpulseai-496112.appspot.com',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId:             import.meta.env.VITE_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = !!(firebaseConfig.apiKey && firebaseConfig.appId);

let app = null;
let auth = null;
let googleProvider = null;

if (isFirebaseConfigured) {
  try {
    app = initializeApp(firebaseConfig);
    auth = getAuth(app);
    googleProvider = new GoogleAuthProvider();
    googleProvider.setCustomParameters({ prompt: 'select_account' });
  } catch (err) {
    console.error('[Firebase] Initialization failed:', err);
  }
} else {
  console.warn(
    '[Firebase] Missing VITE_FIREBASE_API_KEY or VITE_FIREBASE_APP_ID. ' +
    'Local development will run in offline mode. Please create a .env.local ' +
    'file in the /frontend folder containing your Firebase configuration to enable authentication.'
  );
}

// ── Helper functions ──────────────────────────────────────────────────────────

/** Sign in with Google popup */
export const signInWithGoogle = () => {
  if (!isFirebaseConfigured) {
    alert('Google authentication is offline (missing Firebase config).');
    return Promise.reject(new Error('Firebase not configured'));
  }
  return signInWithPopup(auth, googleProvider);
};

/** Sign in with email + password */
export const signInWithEmail = (email, password) => {
  if (!isFirebaseConfigured) {
    alert('Email authentication is offline (missing Firebase config).');
    return Promise.reject(new Error('Firebase not configured'));
  }
  return signInWithEmailAndPassword(auth, email, password);
};

/** Register a new user with email + password and send verification email */
export const registerWithEmail = async (email, password) => {
  if (!isFirebaseConfigured) {
    alert('Registration is offline (missing Firebase config).');
    return Promise.reject(new Error('Firebase not configured'));
  }
  const credential = await createUserWithEmailAndPassword(auth, email, password);
  await sendEmailVerification(credential.user);
  return credential;
};

/** Send a password-reset email */
export const sendPasswordReset = (email) => {
  if (!isFirebaseConfigured) {
    alert('Password reset is offline (missing Firebase config).');
    return Promise.reject(new Error('Firebase not configured'));
  }
  return sendPasswordResetEmail(auth, email);
};

/** Resend email verification to the currently signed-in user */
export const resendVerification = () => {
  if (!isFirebaseConfigured || !auth?.currentUser) return Promise.resolve();
  return sendEmailVerification(auth.currentUser);
};

/** Sign out */
export const logOut = () => {
  if (!isFirebaseConfigured) return Promise.resolve();
  return signOut(auth);
};

/** Get the current user's ID token (force-refresh optional) */
export const getIdToken = (forceRefresh = false) => {
  if (!isFirebaseConfigured || !auth?.currentUser) return Promise.resolve(null);
  return auth.currentUser.getIdToken(forceRefresh);
};

export { auth, googleProvider };
