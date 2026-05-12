"""
Interactive Plotly in Streamlit: zoom (toolbar + scroll), pan, box/lasso, reset.

Plotly often ships with scrollZoom disabled in embedded contexts; we enable it explicitly.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

# https://plotly.com/python/configuration-options/
DEFAULT_INTERACTIVE_CONFIG: dict[str, Any] = {
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False,
    "doubleClick": "reset",
    "showTips": True,
    "toImageButtonOptions": {
        "format": "png",
        "filename": "chart",
        "height": None,
        "width": None,
        "scale": 2,
    },
}


def plotly_chart_interactive(
    fig: Any,
    *,
    config: dict[str, Any] | None = None,
    use_container_width: bool = True,
    **kwargs: Any,
) -> None:
    """Render a Plotly figure with full default interactivity."""
    merged = {**DEFAULT_INTERACTIVE_CONFIG, **(config or {})}
    st.plotly_chart(
        fig,
        use_container_width=use_container_width,
        config=merged,
        **kwargs,
    )
