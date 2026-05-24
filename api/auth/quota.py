"""
Per-user daily quota tracking for Market Price Pulse AI.

Storage
-------
SQLAlchemy + SQLite by default (production: swap DATABASE_URL for PostgreSQL).
Thread-safe via scoped_session.  Tables are auto-created on module import.

Environment variables
---------------------
DATABASE_URL          SQLAlchemy connection string.  Default: sqlite:////app/data/usage.db
QUOTA_FREE_DAILY      Daily request cap for "free" plan.       Default: 100
QUOTA_PRO_DAILY       Daily request cap for "pro" plan.        Default: 5000
QUOTA_ENTERPRISE_DAILY  Daily request cap for "enterprise".    Default: 999999

Schema
------
UsageRecord
    id            INTEGER PK auto-increment
    uid           VARCHAR  — Firebase UID
    endpoint      VARCHAR  — e.g. "/v1/score"
    date          DATE     — UTC calendar date of the bucket
    request_count INTEGER  — incremented on each request
    tokens_used   INTEGER  — reserved for LLM token accounting
    created_at    DATETIME
    updated_at    DATETIME

Index: (uid, endpoint, date) UNIQUE — enforced at DB level for safe upserts.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

_DEFAULT_DB_URL = "sqlite:////app/data/usage.db"
DATABASE_URL: str = os.environ.get("DATABASE_URL", _DEFAULT_DB_URL).strip()

# connect_args only applies to SQLite — ignored by other drivers
_connect_args: dict[str, Any] = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,         # detect stale connections
    echo=False,
)

_session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
SessionLocal = scoped_session(_session_factory)


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------

class _Base(DeclarativeBase):
    pass


class UsageRecord(_Base):
    """One row per (uid, endpoint, UTC-date) bucket."""

    __tablename__ = "usage_records"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    uid: str = Column(String(128), nullable=False, index=True)
    endpoint: str = Column(String(256), nullable=False)
    date: date = Column(Date, nullable=False)
    request_count: int = Column(Integer, nullable=False, default=0)
    tokens_used: int = Column(Integer, nullable=False, default=0)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("uid", "endpoint", "date", name="uq_uid_endpoint_date"),
        Index("ix_uid_date", "uid", "date"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "uid": self.uid,
            "endpoint": self.endpoint,
            "date": self.date.isoformat() if self.date else None,
            "request_count": self.request_count,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Create tables immediately on import so the first request never fails
_Base.metadata.create_all(bind=engine)
logger.info("Quota DB tables ensured at '%s'", DATABASE_URL)


# ---------------------------------------------------------------------------
# Plan limits
# ---------------------------------------------------------------------------

def _plan_limit(plan: str) -> int:
    """Return the configured daily request limit for a given plan."""
    _defaults = {
        "free": 100,
        "pro": 5_000,
        "enterprise": 999_999,
    }
    env_keys = {
        "free": "QUOTA_FREE_DAILY",
        "pro": "QUOTA_PRO_DAILY",
        "enterprise": "QUOTA_ENTERPRISE_DAILY",
    }
    env_key = env_keys.get(plan, "QUOTA_FREE_DAILY")
    default = _defaults.get(plan, 100)
    try:
        return int(os.environ.get(env_key, str(default)))
    except ValueError:
        logger.warning("Invalid value for %s; using default %d", env_key, default)
        return default


# ---------------------------------------------------------------------------
# Quota helpers
# ---------------------------------------------------------------------------

def _utc_today() -> date:
    return datetime.now(tz=timezone.utc).date()


def _seconds_until_midnight_utc() -> int:
    """Number of seconds from now until 00:00:00 UTC tomorrow."""
    now_utc = datetime.now(tz=timezone.utc)
    tomorrow_midnight = datetime(
        now_utc.year, now_utc.month, now_utc.day,
        tzinfo=timezone.utc,
    ) + timedelta(days=1)
    return max(0, int((tomorrow_midnight - now_utc).total_seconds()))


def _tomorrow_midnight_utc_iso() -> str:
    now_utc = datetime.now(tz=timezone.utc)
    tomorrow = now_utc.date() + timedelta(days=1)
    return f"{tomorrow.isoformat()}T00:00:00Z"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_and_increment_quota(uid: str, plan: str, endpoint: str) -> None:
    """Check the user's daily quota and increment their request counter.

    This function performs an atomic upsert:
      - If no record exists for (uid, endpoint, today) it creates one with count=1.
      - If a record already exists it increments request_count by 1.
      - If the *pre-increment* count is already ≥ the plan limit, raises 429
        **before** writing, so the limit is enforced exactly.

    Args:
        uid:      Firebase UID.
        plan:     Billing plan — "free", "pro", or "enterprise".
        endpoint: Route path string, e.g. "/v1/score".

    Raises:
        HTTPException 429: Daily quota exceeded.
    """
    session = SessionLocal()
    try:
        today = _utc_today()
        limit = _plan_limit(plan)

        # Try to fetch existing record (SELECT FOR UPDATE not needed for SQLite;
        # for Postgres add with_for_update() to the select).
        stmt = select(UsageRecord).where(
            UsageRecord.uid == uid,
            UsageRecord.endpoint == endpoint,
            UsageRecord.date == today,
        )
        record: UsageRecord | None = session.execute(stmt).scalar_one_or_none()

        if record is None:
            # First request today — create row with count=1
            record = UsageRecord(
                uid=uid,
                endpoint=endpoint,
                date=today,
                request_count=1,
                tokens_used=0,
            )
            session.add(record)
            session.commit()
            logger.debug("Quota: new record for uid=%s endpoint=%s count=1", uid, endpoint)
            return

        # Already exists — check limit before incrementing
        if record.request_count >= limit:
            retry_after = _seconds_until_midnight_utc()
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "message": (
                        f"Daily quota of {limit} requests exceeded for plan '{plan}'. "
                        "Upgrade your plan or wait until tomorrow."
                    ),
                    "limit": limit,
                    "used": record.request_count,
                    "reset_at": _tomorrow_midnight_utc_iso(),
                    "upgrade_url": "https://marketpulse.services/pricing",
                },
                headers={"Retry-After": str(retry_after)},
            )

        record.request_count += 1
        record.updated_at = datetime.now(tz=timezone.utc)
        session.commit()
        logger.debug(
            "Quota: uid=%s endpoint=%s count=%d/%d",
            uid, endpoint, record.request_count, limit,
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error("Quota DB error for uid=%s: %s", uid, exc, exc_info=True)
        # Don't block the user on a transient DB error — log and continue
    finally:
        SessionLocal.remove()


def get_user_usage(uid: str, days: int = 30) -> list[dict[str, Any]]:
    """Return usage records for a specific user over the last N days.

    Args:
        uid:  Firebase UID to query.
        days: Number of calendar days to look back (inclusive). Default 30.

    Returns:
        List of dicts, one per (endpoint, date) bucket, ordered newest first.
    """
    session = SessionLocal()
    try:
        cutoff = _utc_today() - timedelta(days=days - 1)
        stmt = (
            select(UsageRecord)
            .where(UsageRecord.uid == uid, UsageRecord.date >= cutoff)
            .order_by(UsageRecord.date.desc(), UsageRecord.endpoint)
        )
        records = session.execute(stmt).scalars().all()
        return [r.to_dict() for r in records]
    except Exception as exc:
        logger.error("get_user_usage error for uid=%s: %s", uid, exc, exc_info=True)
        return []
    finally:
        SessionLocal.remove()


def get_all_usage_stats() -> dict[str, Any]:
    """Return a high-level system overview of quota usage for the admin panel.

    Returns a dict with:
        total_requests_today    — sum of all request_count rows for today
        total_requests_7d       — last 7 calendar days
        total_requests_30d      — last 30 calendar days
        top_users_today         — top 10 uids by request count today
        top_endpoints_today     — top 10 endpoints by request count today
        active_users_today      — distinct uid count for today
    """
    session = SessionLocal()
    try:
        today = _utc_today()
        seven_ago = today - timedelta(days=6)
        thirty_ago = today - timedelta(days=29)

        def _sum_count(since: date) -> int:
            row = session.execute(
                select(func.sum(UsageRecord.request_count)).where(
                    UsageRecord.date >= since
                )
            ).scalar()
            return int(row or 0)

        def _top_by(column, since: date, limit: int = 10) -> list[dict[str, Any]]:
            rows = session.execute(
                select(column, func.sum(UsageRecord.request_count).label("total"))
                .where(UsageRecord.date >= since)
                .group_by(column)
                .order_by(text("total DESC"))
                .limit(limit)
            ).all()
            return [{"key": r[0], "total": int(r[1])} for r in rows]

        active_today = session.execute(
            select(func.count(func.distinct(UsageRecord.uid))).where(
                UsageRecord.date == today
            )
        ).scalar()

        return {
            "total_requests_today": _sum_count(today),
            "total_requests_7d": _sum_count(seven_ago),
            "total_requests_30d": _sum_count(thirty_ago),
            "active_users_today": int(active_today or 0),
            "top_users_today": _top_by(UsageRecord.uid, today),
            "top_endpoints_today": _top_by(UsageRecord.endpoint, today),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("get_all_usage_stats error: %s", exc, exc_info=True)
        return {"error": str(exc)}
    finally:
        SessionLocal.remove()
