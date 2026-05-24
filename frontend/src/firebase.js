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

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

googleProvider.setCustomParameters({ prompt: 'select_account' });

// ── Helper functions ──────────────────────────────────────────────────────────

/** Sign in with Google popup */
export const signInWithGoogle = () => signInWithPopup(auth, googleProvider);

/** Sign in with email + password */
export const signInWithEmail = (email, password) =>
  signInWithEmailAndPassword(auth, email, password);

/** Register a new user with email + password and send verification email */
export const registerWithEmail = async (email, password) => {
  const credential = await createUserWithEmailAndPassword(auth, email, password);
  await sendEmailVerification(credential.user);
  return credential;
};

/** Send a password-reset email */
export const sendPasswordReset = (email) =>
  sendPasswordResetEmail(auth, email);

/** Resend email verification to the currently signed-in user */
export const resendVerification = () =>
  sendEmailVerification(auth.currentUser);

/** Sign out */
export const logOut = () => signOut(auth);

/** Get the current user's ID token (force-refresh optional) */
export const getIdToken = (forceRefresh = false) =>
  auth.currentUser ? auth.currentUser.getIdToken(forceRefresh) : Promise.resolve(null);
