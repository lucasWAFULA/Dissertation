"""
Admin-only router for Market Price Pulse AI.

All routes require the "admin" Firebase custom claim (role == "admin").
Set this via: POST /v1/admin/users/{uid}/plan  with body {"plan": "admin"}
or directly via the Firebase Admin SDK / console.

Prefix : /v1/admin
Tags   : admin
Auth   : require_admin dependency (HTTP 401 + 403 enforced)
"""
from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import UserContext, require_admin
from api.auth.firebase import set_user_custom_claims
from api.auth.quota import get_all_usage_stats, get_user_usage

router = APIRouter(prefix="/v1/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class PlanUpdate(BaseModel):
    plan: Literal["free", "pro", "enterprise", "admin"]


class PlanUpdateResponse(BaseModel):
    success: bool
    uid: str
    plan: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/stats",
    summary="System-wide quota usage statistics",
    description=(
        "Returns aggregated request counts across all users and endpoints. "
        "Includes today, last 7 days, last 30 days, top users, and top endpoints."
    ),
)
def admin_stats(
    _admin: Annotated[UserContext, Depends(require_admin)],
) -> dict:
    """Return system-wide usage statistics.  Admin only."""
    return get_all_usage_stats()


@router.get(
    "/users/{uid}/usage",
    summary="Per-user quota usage history",
    description="Returns the request history for a specific Firebase UID over the last 30 days.",
)
def admin_user_usage(
    uid: str,
    days: int = 30,
    _admin: Annotated[UserContext, Depends(require_admin)] = None,
) -> list[dict]:
    """Return usage records for ``uid`` over the last ``days`` calendar days."""
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
    return get_user_usage(uid, days=days)


@router.post(
    "/users/{uid}/plan",
    summary="Update a user's subscription plan",
    description=(
        "Sets Firebase custom claims ``{role: plan, plan: plan}`` for the given UID. "
        "The user must refresh their ID token for the change to take effect (up to 1 hour)."
    ),
    response_model=PlanUpdateResponse,
)
def admin_set_user_plan(
    uid: str,
    body: PlanUpdate,
    _admin: Annotated[UserContext, Depends(require_admin)] = None,
) -> PlanUpdateResponse:
    """Set ``role`` and ``plan`` custom claims on a Firebase user.  Admin only."""
    set_user_custom_claims(uid, {"role": body.plan, "plan": body.plan})
    return PlanUpdateResponse(
        success=True,
        uid=uid,
        plan=body.plan,
        message=(
            f"User {uid} plan updated to '{body.plan}'. "
            "The change will be reflected in their ID token within 1 hour, "
            "or immediately if the client calls getIdToken(true)."
        ),
    )


@router.get(
    "/health",
    summary="Detailed system health for admin panel",
    description="Returns verbose system health including DB connectivity, Python version, and uptime.",
)
def admin_health(
    _admin: Annotated[UserContext, Depends(require_admin)] = None,
) -> dict:
    """Return detailed system health for the admin monitoring panel."""
    from api.auth.quota import engine, DATABASE_URL  # local import to avoid circular

    # Test DB connectivity
    db_ok = False
    db_error: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(engine.dialect.statement_compiler(
                engine.dialect, None
            ).__class__.__mro__[0].__new__(engine.dialect.__class__))
    except Exception:  # noqa: BLE001
        pass

    # Simpler DB ping
    try:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            conn.execute(_text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        db_error = str(exc)

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "database": {
            "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
            "connected": db_ok,
            "error": db_error,
        },
        "firebase": {
            "initialized": True,  # If this endpoint is reachable, Firebase auth worked
        },
    }
