"""
FastAPI dependency functions for authentication and authorisation.

Usage in route handlers
-----------------------
from typing import Annotated
from fastapi import Depends
from api.auth.dependencies import get_current_user, require_admin, UserContext

# Any authenticated user:
@app.get("/protected")
def protected(user: Annotated[UserContext, Depends(get_current_user)]):
    return {"uid": user.uid}

# Admin only:
@app.get("/admin")
def admin_only(user: Annotated[UserContext, Depends(require_admin)]):
    return {"uid": user.uid}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from api.auth.firebase import verify_firebase_token

# ---------------------------------------------------------------------------
# UserContext dataclass
# ---------------------------------------------------------------------------

VALID_ROLES = frozenset({"free", "pro", "enterprise", "admin"})
VALID_PLANS = frozenset({"free", "pro", "enterprise"})


@dataclass
class UserContext:
    """Authenticated user context injected into route handlers via FastAPI Depends."""

    uid: str
    email: str
    role: str           # "free" | "pro" | "enterprise" | "admin"
    plan: str           # "free" | "pro" | "enterprise"  (mirrors role for billing)
    email_verified: bool

    # Optional extra claims forwarded verbatim from the Firebase token
    extra_claims: dict = field(default_factory=dict)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_pro_or_above(self) -> bool:
        return self.role in {"pro", "enterprise", "admin"}


# ---------------------------------------------------------------------------
# Dependency: get_current_user
# ---------------------------------------------------------------------------

def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> UserContext:
    """FastAPI dependency that extracts and verifies the Firebase JWT from the
    ``Authorization: Bearer <token>`` header.

    Returns:
        A :class:`UserContext` populated from the decoded token claims.

    Raises:
        HTTPException 401: Header is missing or token is invalid/expired.
        HTTPException 403: Email not verified (for email/password providers).
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required. Expected: 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Split "Bearer <token>"
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authorization header must be in format: 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Bearer token is empty.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify via Firebase Admin SDK — raises 401/403 on failure
    decoded = verify_firebase_token(token)

    # Extract well-known fields
    uid: str = decoded.get("uid", "")
    email: str = decoded.get("email", "")
    email_verified: bool = bool(decoded.get("email_verified", False))

    # Role: custom claim set via set_user_custom_claims, default "free"
    raw_role: str = decoded.get("role", "free")
    role = raw_role if raw_role in VALID_ROLES else "free"

    # Plan: mirrors role for billing purposes; strip "admin" → "enterprise"
    if role == "admin":
        plan = "enterprise"
    else:
        plan = role if role in VALID_PLANS else "free"

    # Capture any extra claims for downstream use (e.g. tenant_id, org_id)
    known_keys = {"uid", "email", "email_verified", "role", "plan",
                  "iss", "aud", "auth_time", "iat", "exp", "sub", "firebase"}
    extra = {k: v for k, v in decoded.items() if k not in known_keys}

    return UserContext(
        uid=uid,
        email=email,
        role=role,
        plan=plan,
        email_verified=email_verified,
        extra_claims=extra,
    )


# ---------------------------------------------------------------------------
# Dependency: require_admin
# ---------------------------------------------------------------------------

def require_admin(
    user: Annotated[UserContext, Depends(get_current_user)],
) -> UserContext:
    """FastAPI dependency that extends ``get_current_user`` with an admin role check.

    Raises:
        HTTPException 403: Authenticated user does not have the ``admin`` role.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail=(
                "Administrator privileges are required to access this resource. "
                f"Your current role is '{user.role}'."
            ),
        )
    return user
