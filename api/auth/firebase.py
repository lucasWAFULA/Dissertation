"""
Firebase Admin SDK integration for Market Price Pulse AI.

Credential resolution order:
  1. FIREBASE_CREDENTIALS_JSON  — JSON string of a service-account key (useful for K8s secrets / env injection)
  2. GOOGLE_APPLICATION_CREDENTIALS — path to a service-account JSON file (local dev / Cloud Run)
  3. Application Default Credentials — GKE Workload Identity, Cloud Run default SA, `gcloud auth application-default login`

Required env vars:
  FIREBASE_PROJECT_ID   — your Firebase project ID (e.g. "my-project-12345")

Optional env vars:
  FIREBASE_CREDENTIALS_JSON   — service-account JSON as a string
  GOOGLE_APPLICATION_CREDENTIALS — path to service-account JSON file

# firebase-admin>=6.0.0 required — add to requirements.txt
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import firebase_admin
import firebase_admin.auth
from firebase_admin import credentials
from firebase_admin.exceptions import FirebaseError
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# One-time Firebase app initialisation
# ---------------------------------------------------------------------------

_firebase_app: firebase_admin.App | None = None


def _get_firebase_app() -> firebase_admin.App:
    """Return the singleton Firebase app, initialising it if necessary."""
    global _firebase_app  # noqa: PLW0603

    if _firebase_app is not None:
        return _firebase_app

    project_id = os.environ.get("FIREBASE_PROJECT_ID")
    if not project_id:
        raise RuntimeError(
            "FIREBASE_PROJECT_ID environment variable is not set. "
            "Please set it to your Firebase project ID."
        )

    # --- credential resolution ------------------------------------------
    cred_json_str = os.environ.get("FIREBASE_CREDENTIALS_JSON", "").strip()
    gac_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if cred_json_str:
        # Inline JSON string — convenient for Kubernetes / Docker secrets
        try:
            cred_dict = json.loads(cred_json_str)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FIREBASE_CREDENTIALS_JSON is not valid JSON."
            ) from exc
        cred = credentials.Certificate(cred_dict)
        logger.info("Firebase: using credentials from FIREBASE_CREDENTIALS_JSON env var")

    elif gac_path and os.path.isfile(gac_path):
        # File path — local dev or Cloud Run with mounted secret
        cred = credentials.Certificate(gac_path)
        logger.info("Firebase: using credentials from file %s", gac_path)

    else:
        # Application Default Credentials — GKE Workload Identity et al.
        cred = credentials.ApplicationDefault()
        logger.info("Firebase: using Application Default Credentials")

    options: dict[str, Any] = {"projectId": project_id}
    _firebase_app = firebase_admin.initialize_app(cred, options)
    logger.info("Firebase app initialised for project '%s'", project_id)
    return _firebase_app


# Eagerly trigger initialisation at import time so startup errors are surfaced
# immediately (not on the first request).  We swallow the error here because
# the module can still be imported in test environments without Firebase.
try:
    _get_firebase_app()
except Exception as _init_err:  # noqa: BLE001
    logger.warning("Firebase initialisation deferred: %s", _init_err)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_firebase_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return the decoded claims.

    Args:
        token: The raw Firebase JWT ID token from the Authorization header.

    Returns:
        Decoded token payload as a dict.  Guaranteed keys: ``uid``, ``email``,
        ``email_verified``.  Custom claims (``role``, ``plan``) may also be present.

    Raises:
        HTTPException 401: Token is missing, malformed, expired, or revoked.
        HTTPException 403: Email address is not verified (applies to
            email/password sign-in providers; OAuth providers are implicitly
            verified).
    """
    app = _get_firebase_app()

    try:
        decoded: dict[str, Any] = firebase_admin.auth.verify_id_token(
            token,
            app=app,
            check_revoked=True,
        )
    except firebase_admin.auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked. Please sign in again.")
    except firebase_admin.auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token has expired. Please sign in again.")
    except firebase_admin.auth.InvalidIdTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
    except FirebaseError as exc:
        logger.error("Firebase token verification error: %s", exc)
        raise HTTPException(status_code=401, detail="Authentication failed.") from exc

    # Enforce email verification for email/password sign-in users.
    # OAuth providers (Google, GitHub, etc.) set email_verified=True automatically.
    sign_in_provider: str = decoded.get("firebase", {}).get("sign_in_provider", "")
    is_email_password = sign_in_provider == "password"
    if is_email_password and not decoded.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail=(
                "Email address is not verified. "
                "Please check your inbox and verify your email before continuing."
            ),
        )

    logger.debug("Verified token for uid=%s email=%s", decoded.get("uid"), decoded.get("email"))
    return decoded


def set_user_custom_claims(uid: str, claims: dict[str, Any]) -> None:
    """Set custom claims on a Firebase user.  Admin-only operation.

    Custom claims are included in the Firebase ID token after the user's next
    token refresh (up to 1 hour).  To force an immediate refresh, instruct the
    client to call ``firebase.auth().currentUser.getIdToken(true)``.

    Args:
        uid:    Firebase UID of the target user.
        claims: Dict of claims to set, e.g. ``{"role": "pro", "plan": "pro"}``.
                Pass an empty dict to clear all custom claims.

    Raises:
        HTTPException 500: If the Firebase Admin SDK call fails.
    """
    app = _get_firebase_app()
    try:
        firebase_admin.auth.set_custom_user_claims(uid, claims, app=app)
        logger.info("Custom claims set for uid=%s: %s", uid, claims)
    except FirebaseError as exc:
        logger.error("Failed to set custom claims for uid=%s: %s", uid, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user claims: {exc}",
        ) from exc
