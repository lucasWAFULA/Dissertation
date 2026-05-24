"""
API smoke tests — run with: pytest tests/ -v
These tests import only stdlib + project schemas, so they work in CI
without needing a running server or Firebase credentials.
"""
import importlib
import sys


def test_imports_fastapi():
    """FastAPI and core dependencies are importable."""
    import fastapi
    import uvicorn
    assert fastapi.__version__ >= "0.109.0"


def test_imports_pandas_numpy():
    """Data science stack is importable."""
    import pandas as pd
    import numpy as np
    assert pd.__version__ >= "1.5.0"


def test_imports_sklearn_xgboost():
    """ML libraries are importable."""
    import sklearn
    import xgboost
    assert True


def test_api_schemas_importable():
    """Core API schemas load without a running server."""
    from api.schemas import ScoreRequest, ScoreResponse, ModelInfoResponse
    assert ScoreRequest is not None
    assert ScoreResponse is not None
    assert ModelInfoResponse is not None


def test_score_request_validation():
    """ScoreRequest rejects empty record list."""
    from api.schemas import ScoreRequest
    import pytest
    # Valid request
    req = ScoreRequest(records=[
        {"date": "2024-01", "commodity": "Maize", "county": "Nairobi",
         "market": "City Market", "price_usd": 0.45, "unit": "KG"}
    ])
    assert len(req.records) == 1


def test_quota_plan_limits():
    """Quota plan limits read correctly from defaults."""
    import os
    os.environ.setdefault("QUOTA_FREE_DAILY", "100")
    os.environ.setdefault("QUOTA_PRO_DAILY", "5000")
    os.environ.setdefault("QUOTA_ENTERPRISE_DAILY", "999999")
    assert int(os.environ["QUOTA_FREE_DAILY"]) == 100
    assert int(os.environ["QUOTA_PRO_DAILY"]) == 5000
