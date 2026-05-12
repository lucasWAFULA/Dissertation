from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


def _register_readable_plotly_template() -> None:
    """High-contrast figures for the professional intelligence panel."""
    try:
        spec = pio.templates["plotly_white"].to_plotly_json()
        L = spec.setdefault("layout", {})
        L["paper_bgcolor"] = "rgba(0,0,0,0)"
        L["plot_bgcolor"] = "rgba(0,0,0,0)"
        L["font"] = {"size": 13, "color": "#111827", "family": "Inter, sans-serif"}
        L.setdefault("title", {})["font"] = {
            "size": 18,
            "color": "#111827",
            "family": "Inter, sans-serif",
        }
        xa = L.setdefault("xaxis", {})
        xa["tickfont"] = {"size": 11, "color": "#4B5563"}
        xa["title"] = {"font": {"size": 12, "color": "#111827"}}
        xa.setdefault("gridcolor", "#F3F4F6")
        xa.setdefault("linecolor", "#E5E7EB")
        ya = L.setdefault("yaxis", {})
        ya["tickfont"] = {"size": 11, "color": "#4B5563"}
        ya["title"] = {"font": {"size": 12, "color": "#111827"}}
        ya.setdefault("gridcolor", "#F3F4F6")
        ya.setdefault("linecolor", "#E5E7EB")
        L.setdefault("legend", {})["font"] = {"size": 11, "color": "#4B5563"}
        L.setdefault("legend", {})["bgcolor"] = "rgba(255,255,255,0.8)"
        pio.templates["intel_theme"] = go.layout.Template(spec)
        pio.templates.default = "intel_theme"
    except Exception:
        pass


_register_readable_plotly_template()

SEVERITY_ORDER = ["Low", "Medium", "High"]
# Professional alert colors
SEVERITY_COLORS = {
    "Low": "#10B981",    # emerald
    "Medium": "#F59E0B", # amber
    "High": "#EF4444",   # red
}
# Shared professional palette for charts
CHART_ACCENT = "#10B981"
CHART_GOLD = "#F59E0B"
CHART_ANOMALY = "#EF4444"
CHART_FORECAST_BAND = "#F9FAFB"
CHART_GRID = "#F3F4F6"


def enrich_dashboard_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["expected_price"] = enriched.get("price_roll3", enriched["price_real"]).fillna(
        enriched["price_real"]
    )

    if "prob_anomaly" in enriched.columns and enriched["prob_anomaly"].notna().any():
        risk_score = enriched["prob_anomaly"].fillna(0)
    else:
        baseline = enriched["expected_price"].replace(0, np.nan)
        risk_score = ((enriched["price_real"] - baseline).abs() / baseline).fillna(0).clip(0, 1)

    enriched["risk_score"] = risk_score
    enriched["price_spike_pct"] = (
        (enriched["price_real"] - enriched["expected_price"])
        / enriched["expected_price"].replace(0, np.nan)
        * 100
    ).fillna(0)

    severity = np.select(
        [enriched["risk_score"] >= 0.75, enriched["risk_score"] >= 0.40],
        ["High", "Medium"],
        default="Low",
    )
    enriched["severity"] = pd.Categorical(severity, categories=SEVERITY_ORDER, ordered=True)
    return enriched


def build_kpi_summary(frame: pd.DataFrame, raw_frame: pd.DataFrame | None = None) -> dict[str, object]:
    total_records = int(len(frame))
    latest_month = frame["date"].max().to_period("M").to_timestamp()
    latest_period = frame[frame["date"].dt.to_period("M").dt.to_timestamp() == latest_month]

    anomaly_count = int(frame["pred_anomaly"].sum()) if "pred_anomaly" in frame else 0
    avg_score = float(frame["risk_score"].mean()) if "risk_score" in frame and total_records else np.nan
    markets_covered = int(raw_frame["market"].nunique()) if raw_frame is not None and "market" in raw_frame else 0

    commodity_summary = (
        frame.groupby("commodity")["pred_anomaly"].sum().sort_values(ascending=False)
        if "commodity" in frame
        else pd.Series(dtype=float)
    )
    most_affected = commodity_summary.index[0] if not commodity_summary.empty else "N/A"
    highest_spike = float(frame["price_spike_pct"].max()) if "price_spike_pct" in frame and total_records else 0.0

    return {
        "total_commodities": int(frame["commodity"].nunique()) if "commodity" in frame else 0,
        "total_markets": markets_covered,
        "latest_month_anomalies": int(latest_period["pred_anomaly"].sum()) if not latest_period.empty else 0,
        "most_affected_commodity": most_affected,
        "highest_price_spike": highest_spike,
        "avg_risk_score": avg_score,
        "total_records": total_records,
        "anomaly_count": anomaly_count,
    }


def make_price_trend_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    plot_source = frame.copy()
    if "record_type" not in plot_source.columns:
        plot_source["record_type"] = "historical"

    commodity_count = frame["commodity"].nunique()
    historical_end = None
    historical_rows = plot_source[plot_source["record_type"] == "historical"]
    if not historical_rows.empty:
        historical_end = pd.to_datetime(historical_rows["date"]).max()

    if commodity_count <= 4:
        plot_df = (
            plot_source.groupby(["date", "commodity", "record_type"], as_index=False)
            .agg(
                price_real=("price_real", "mean"),
                expected_price=("expected_price", "mean"),
                anomaly_count=("pred_anomaly", "sum"),
                avg_score=("risk_score", "mean"),
            )
            .sort_values(["commodity", "record_type", "date"])
        )
        for commodity, group in plot_df.groupby("commodity"):
            for record_type, segment in group.groupby("record_type"):
                is_forecast = record_type == "forecast"
                line_dash = "dot" if is_forecast else "solid"
                label_suffix = "forecast" if is_forecast else "observed"

                figure.add_trace(
                    go.Scatter(
                        x=segment["date"],
                        y=segment["price_real"],
                        mode="lines",
                        name=f"{commodity} {label_suffix}",
                        line={"width": 2, "dash": line_dash},
                    )
                )
                figure.add_trace(
                    go.Scatter(
                        x=segment["date"],
                        y=segment["expected_price"],
                        mode="lines",
                        name=f"{commodity} expected {label_suffix}",
                        line={"width": 1, "dash": "dash" if not is_forecast else "dot"},
                        opacity=0.6,
                    )
                )

            anomalies = group[group["anomaly_count"] > 0]
            if not anomalies.empty:
                figure.add_trace(
                    go.Scatter(
                        x=anomalies["date"],
                        y=anomalies["price_real"],
                        mode="markers",
                        name=f"{commodity} anomalies",
                        marker={"size": 9, "color": CHART_ANOMALY, "symbol": "diamond"},
                        hovertemplate=(
                            "Commodity: %{text}<br>Date: %{x|%Y-%m-%d}"
                            "<br>Observed: %{y:.2f}<br>Mean score: %{customdata[0]:.3f}<extra></extra>"
                        ),
                        text=anomalies["commodity"],
                        customdata=np.stack([anomalies["avg_score"]], axis=-1),
                    )
                )
    else:
        plot_df = (
            plot_source.groupby(["date", "record_type"], as_index=False)
            .agg(
                price_real=("price_real", "mean"),
                expected_price=("expected_price", "mean"),
                anomaly_count=("pred_anomaly", "sum"),
                avg_score=("risk_score", "mean"),
            )
            .sort_values(["record_type", "date"])
        )
        for record_type, segment in plot_df.groupby("record_type"):
            is_forecast = record_type == "forecast"
            label_suffix = "forecast" if is_forecast else "historical"
            line_dash = "dot" if is_forecast else "solid"

            figure.add_trace(
                go.Scatter(
                    x=segment["date"],
                    y=segment["price_real"],
                    mode="lines",
                    name=f"Observed price ({label_suffix})",
                    line={"width": 2, "dash": line_dash},
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=segment["date"],
                    y=segment["expected_price"],
                    mode="lines",
                    name=f"Expected range midpoint ({label_suffix})",
                    line={"width": 1, "dash": "dash" if not is_forecast else "dot"},
                    opacity=0.7,
                )
            )
        anomalies = plot_df[plot_df["anomaly_count"] > 0]
        if not anomalies.empty:
            figure.add_trace(
                go.Scatter(
                    x=anomalies["date"],
                    y=anomalies["price_real"],
                    mode="markers",
                    name="Detected anomalies",
                    marker={"size": 9, "color": CHART_ANOMALY, "symbol": "diamond"},
                    customdata=np.stack([anomalies["anomaly_count"], anomalies["avg_score"]], axis=-1),
                    hovertemplate=(
                        "Date: %{x|%Y-%m-%d}<br>Observed: %{y:.2f}<br>Anomalies: %{customdata[0]:.0f}"
                        "<br>Mean score: %{customdata[1]:.3f}<extra></extra>"
                    ),
                )
            )

    if historical_end is not None and (plot_source["record_type"] == "forecast").any():
        forecast_end = pd.to_datetime(plot_source["date"]).max()
        figure.add_vrect(
            x0=historical_end,
            x1=forecast_end,
            fillcolor=CHART_FORECAST_BAND,
            opacity=0.25,
            line_width=0,
            layer="below",
        )
        figure.add_shape(
            type="line",
            x0=historical_end,
            x1=historical_end,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line={
                "width": 1,
                "dash": "dash",
                "color": "#4A5D44",
            },
        )
        figure.add_annotation(
            x=historical_end,
            y=1,
            xref="x",
            yref="paper",
            text="Forecast starts",
            showarrow=False,
            yshift=10,
            font={"color": "#4A5D44"},
        )

    figure.update_layout(
        title="Price trend and detected anomalies",
        xaxis_title="Date",
        yaxis_title="Real price (per kg)",
        legend_title="Series",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        hovermode="x unified",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
        font={"color": "#2C3318", "family": "DM Sans, sans-serif"},
        xaxis={"gridcolor": CHART_GRID},
        yaxis={"gridcolor": CHART_GRID},
    )
    return figure


def make_alerts_table(
    frame: pd.DataFrame,
    limit: int | None = None,
    *,
    include_elevated: bool = True,
) -> pd.DataFrame:
    """Build scrollable alert rows: model-flagged anomalies plus optional watchlist.

    - **Model anomaly:** ``pred_anomaly == 1``
    - **Elevated risk** (if ``include_elevated``): Medium/High severity rows not already
      flagged, so more commodities appear. Same date×county×commodity keeps the model
      flag when both exist.

    ``limit=None`` returns all rows (use a tall ``st.dataframe(..., height=...)``).
    """
    out_cols = [
        "date",
        "commodity",
        "county",
        "observed_price",
        "expected_price",
        "anomaly_score",
        "status_level",
        "source",
    ]
    if frame.empty or "pred_anomaly" not in frame.columns:
        return pd.DataFrame(columns=out_cols)

    sev = frame["severity"].astype(str)
    flagged = frame[frame["pred_anomaly"] == 1].copy()
    flagged["_prio"] = 2

    parts: list[pd.DataFrame] = []
    if not flagged.empty:
        parts.append(flagged)
    if include_elevated:
        watch = frame[(frame["pred_anomaly"] != 1) & (sev.isin(["Medium", "High"]))].copy()
        if not watch.empty:
            watch["_prio"] = 1
            parts.append(watch)

    if not parts:
        return pd.DataFrame(columns=out_cols)

    alerts = pd.concat(parts, ignore_index=True)
    alerts["_dk"] = pd.to_datetime(alerts["date"], errors="coerce").dt.normalize()
    alerts = alerts.sort_values("_prio", ascending=False)
    alerts = alerts.drop_duplicates(subset=["_dk", "COUNTY", "commodity"], keep="first")
    alerts = alerts.drop(columns=["_prio", "_dk"], errors="ignore")

    alerts = alerts.sort_values(
        ["commodity", "risk_score", "date"],
        ascending=[True, False, False],
        na_position="last",
    )
    if limit is not None:
        alerts = alerts.head(int(limit)).copy()

    alerts["date"] = pd.to_datetime(alerts["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    alerts["observed_price"] = alerts["price_real"].round(2)
    alerts["expected_price"] = alerts["expected_price"].round(2)
    alerts["anomaly_score"] = alerts["risk_score"].round(3)
    alerts["status_level"] = alerts["severity"].astype(str)
    alerts["source"] = np.where(
        alerts["pred_anomaly"].astype(int) == 1,
        "Model anomaly",
        "Elevated risk",
    )

    columns = [
        "date",
        "commodity",
        "COUNTY",
        "observed_price",
        "expected_price",
        "anomaly_score",
        "status_level",
        "source",
    ]
    return alerts[columns].rename(columns={"COUNTY": "county"})


def _market_points_for_map(
    frame: pd.DataFrame,
    raw_market_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    """Build market markers from raw WFP coords + county-level risk.

    The dashboard scoring table is county+commodity aggregated and may not contain a
    `market` column. We still want market dots, so we:
    - compute county risk from `frame` (avg risk_score / anomaly rate)
    - compute market coordinates from `raw_market_frame`
    - join county risk onto each market (market inherits its county risk)
    """
    if raw_market_frame is None or raw_market_frame.empty:
        return pd.DataFrame()
    if "COUNTY" not in frame.columns:
        return pd.DataFrame()

    raw = raw_market_frame.copy()
    ccol = "county" if "county" in raw.columns else ("COUNTY" if "COUNTY" in raw.columns else None)
    if ccol is None or not {"market", "latitude", "longitude"}.issubset(raw.columns):
        return pd.DataFrame()

    # County risk summary from scored dataset
    county_risk = (
        frame.dropna(subset=["COUNTY"])
        .groupby("COUNTY", as_index=False)
        .agg(
            risk_score=("risk_score", "mean"),
            pred_anomaly=("pred_anomaly", "mean"),
            records=("pred_anomaly", "count"),
        )
    )
    county_risk["_county_key"] = county_risk["COUNTY"].astype(str).str.strip().str.lower()

    # Market coordinates + record counts from raw WFP market table
    raw["_county_key"] = raw[ccol].astype(str).str.strip().str.lower()
    coords = (
        raw.dropna(subset=["latitude", "longitude", "market"])
        .groupby(["market", "_county_key"], as_index=False)
        .agg(
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
            raw_rows=("market", "count"),
        )
    )

    out = coords.merge(county_risk, on="_county_key", how="left")
    out["COUNTY"] = out["COUNTY"].fillna(raw[ccol].astype(str))
    out["risk_score"] = out["risk_score"].fillna(0.0)
    out["pred_anomaly"] = out["pred_anomaly"].fillna(0.0)
    out["records"] = out["records"].fillna(out["raw_rows"]).fillna(1).astype(int)
    out = out.drop(columns=["_county_key"], errors="ignore")
    out = out[
        (out["latitude"].between(-5.5, 6.5)) & (out["longitude"].between(32.5, 42.5))
    ]
    return out


def make_geo_anomaly_map(
    frame: pd.DataFrame,
    county_reference: pd.DataFrame,
    all_47_counties: bool = True,
    map_height: int = 600,
    kenya_adm1_geojson: dict | None = None,
    kenya_adm0_geojson: dict | None = None,
    raw_market_frame: pd.DataFrame | None = None,
) -> go.Figure:
    """Enhanced interactive map using Mapbox for a Google Maps-like experience."""
    from . import kenya_counties as kc

    county_summary = (
        frame.groupby("COUNTY", as_index=False)
        .agg(
            anomaly_rate=("pred_anomaly", "mean"),
            anomaly_count=("pred_anomaly", "sum"),
            avg_price=("price_real", "mean"),
            avg_score=("risk_score", "mean"),
        )
    )
    
    if all_47_counties:
        names_47 = kc.get_all_47_county_names()
        county_summary["COUNTY_CANON"] = county_summary["COUNTY"].map(
            lambda x: kc.data_county_to_canonical(str(x)) or str(x)
        )
        summary_47 = (
            county_summary.groupby("COUNTY_CANON", as_index=False)
            .agg(
                anomaly_rate=("anomaly_rate", "mean"),
                avg_score=("avg_score", "mean"),
            )
        )
        
        geo_rows = []
        for name in names_47:
            row = {"COUNTY": name}
            match = summary_47[summary_47["COUNTY_CANON"] == name]
            if not match.empty:
                m = match.iloc[0]
                row["anomaly_rate"] = float(m["anomaly_rate"])
                row["avg_score"] = float(m["avg_score"])
            else:
                row["anomaly_rate"] = 0.0
                row["avg_score"] = 0.0
            geo_rows.append(row)
        map_df = pd.DataFrame(geo_rows)
    else:
        map_df = county_summary.copy()

    markets_df = _market_points_for_map(frame, raw_market_frame)

    fig = go.Figure()

    # Add Choropleth Layer
    if kenya_adm1_geojson:
        name_key = "shapeName" # Common default for geoBoundaries
        # Try to find the best key if not shapeName
        if "features" in kenya_adm1_geojson and kenya_adm1_geojson["features"]:
            props = kenya_adm1_geojson["features"][0]["properties"]
            for k in ["shapeName", "ADM1_EN", "NAME_1", "name", "COUNTY"]:
                if k in props:
                    name_key = k
                    break

        fig.add_trace(
            go.Choroplethmapbox(
                geojson=kenya_adm1_geojson,
                locations=map_df["COUNTY"],
                z=map_df["anomaly_rate"],
                featureidkey=f"properties.{name_key}",
                colorscale=[
                    [0.0, "#ECFDF5"], # Stable (emerald-50)
                    [0.2, "#D1FAE5"],
                    [0.5, "#FCD34D"], # Moderate (amber-300)
                    [1.0, "#EF4444"], # High (red-500)
                ],
                zmin=0,
                zmax=max(map_df["anomaly_rate"].max(), 0.1),
                marker_opacity=0.6,
                marker_line_width=1,
                marker_line_color="white",
                name="County Risk",
                hovertemplate="<b>%{location}</b><br>Anomaly Rate: %{z:.2%}<extra></extra>"
            )
        )

    # Add Market Scatter Layer
    if not markets_df.empty:
        fig.add_trace(
            go.Scattermapbox(
                lat=markets_df["latitude"],
                lon=markets_df["longitude"],
                mode="markers",
                marker=go.scattermapbox.Marker(
                    size=markets_df["risk_score"] * 25 + 5,
                    color="#111827",
                    opacity=0.8,
                ),
                text=markets_df["market"],
                hovertemplate="<b>Market: %{text}</b><br>Risk Score: %{marker.size}<extra></extra>",
                name="Market Hotspots"
            )
        )

    fig.update_layout(
        mapbox_style="carto-positron", # Professional clean Google-like aesthetic
        mapbox_zoom=5.2,
        mapbox_center={"lat": 0.0236, "lon": 37.9062}, # Center of Kenya
        margin={"r":0,"t":0,"l":0,"b":0},
        height=map_height,
        showlegend=False
    )

    return fig


def make_commodity_heatmap(frame: pd.DataFrame) -> go.Figure:
    top_commodities = (
        frame.groupby("commodity")["pred_anomaly"].sum().sort_values(ascending=False).head(10).index
    )
    top_counties = (
        frame.groupby("COUNTY")["pred_anomaly"].mean().sort_values(ascending=False).head(12).index
    )
    heat_df = frame[
        frame["commodity"].isin(top_commodities) & frame["COUNTY"].isin(top_counties)
    ].copy()
    heat_pivot = (
        heat_df.groupby(["commodity", "COUNTY"])["pred_anomaly"].mean().reset_index().pivot(
            index="commodity",
            columns="COUNTY",
            values="pred_anomaly",
        )
    ).fillna(0)

    figure = px.imshow(
        heat_pivot,
        aspect="auto",
        color_continuous_scale=["#E8F5E9", "#F9A825", "#C62828"],
        title="Commodity vs county anomaly frequency",
    )
    figure.update_layout(
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        coloraxis_colorbar_title="Rate",
        font={"color": "#2C3318"},
    )
    return figure


def make_score_distribution(frame: pd.DataFrame) -> go.Figure | None:
    if "risk_score" not in frame.columns or not frame["risk_score"].notna().any():
        return None

    figure = px.histogram(
        frame,
        x="risk_score",
        color="severity",
        category_orders={"severity": SEVERITY_ORDER},
        color_discrete_map=SEVERITY_COLORS,
        nbins=30,
        title="Anomaly risk score distribution",
    )
    figure.update_layout(
        xaxis_title="Risk score",
        yaxis_title="Count",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        font={"color": "#2C3318"},
        xaxis={"gridcolor": CHART_GRID},
        yaxis={"gridcolor": CHART_GRID},
    )
    return figure


def build_early_warning_summary(frame: pd.DataFrame) -> dict[str, object]:
    """Summary for policy-facing early warning panel."""
    anomalies = frame[frame["pred_anomaly"] == 1] if "pred_anomaly" in frame.columns else pd.DataFrame()
    if anomalies.empty:
        return {
            "high_severity_count": 0,
            "affected_commodities": [],
            "most_affected_county": "N/A",
            "latest_alert_date": None,
        }
    high = anomalies[anomalies["severity"].astype(str) == "High"]
    commodities = (
        anomalies.groupby("commodity")["pred_anomaly"].sum().sort_values(ascending=False).head(10)
    )
    counties = (
        anomalies.groupby("COUNTY")["pred_anomaly"].sum().sort_values(ascending=False)
    )
    latest = pd.to_datetime(anomalies["date"]).max()
    return {
        "high_severity_count": int(high["pred_anomaly"].sum()),
        "affected_commodities": commodities.index.tolist(),
        "most_affected_county": counties.index[0] if not counties.empty else "N/A",
        "latest_alert_date": latest,
    }


def make_severity_bar_chart(
    frame: pd.DataFrame,
    date_range_str: str = "",
    threshold_str: str = "",
) -> go.Figure:
    """Bar chart of records by risk severity (Low/Medium/High from risk score tiers).

    Uses the full filtered dataset, not only model-flagged rows. Flagged anomalies
    often sit above the classification threshold (~0.985), so they would all map
    to High if we counted only pred_anomaly==1.
    """
    if frame.empty or "severity" not in frame.columns:
        severity_counts = pd.Series({"Low": 0, "Medium": 0, "High": 0})
        total = 0
    else:
        severity_counts = (
            frame["severity"].astype(str).value_counts().reindex(SEVERITY_ORDER, fill_value=0)
        )
        total = int(severity_counts.sum())

    order = SEVERITY_ORDER

    counts = [int(severity_counts.get(s, 0)) for s in order]
    pcts = [(counts[i] / total * 100) if total else 0 for i in range(len(order))]
    labels_text = [f"{c:,}" if c else "0" for c in counts]
    pct_text = [f"({p:.1f}%)" if total else "(0%)" for p in pcts]
    combined_labels = [f"{labels_text[i]} {pct_text[i]}" for i in range(len(order))]
    colors = [SEVERITY_COLORS[s] for s in order]

    figure = go.Figure(
        data=[
            go.Bar(
                x=order,
                y=counts,
                text=combined_labels,
                textposition="outside",
                textfont={"size": 13, "color": "#2C3318"},
                marker_color=colors,
                width=0.5,
            )
        ]
    )
    title = "Market records by risk severity (Kenya)"
    if date_range_str:
        title += f" — {date_range_str}"
    margin_b = 70 if threshold_str else 48
    figure.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Severity tier",
        yaxis_title="Number of records",
        margin=dict(l=20, r=20, t=60, b=margin_b),
        font={"color": "#2C3318", "family": "DM Sans, sans-serif"},
        xaxis={
            "gridcolor": "rgba(0,0,0,0.06)",
            "tickfont": {"size": 12},
        },
        yaxis={
            "gridcolor": "rgba(0,0,0,0.06)",
            "title_font": {"size": 12},
        },
        showlegend=False,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
    )
    tier_note = (
        "Tiers: Low &lt;0.40, Medium 0.40–0.75, High ≥0.75 (risk score)."
    )
    if threshold_str:
        tier_note += f" Model flags when score {threshold_str}."
    figure.add_annotation(
        text=tier_note,
        xref="paper", yref="paper", x=0.5, y=-0.14,
        showarrow=False, font=dict(size=10, color="#4A5D44"),
    )
    return figure


def make_severity_donut(
    frame: pd.DataFrame,
    date_range_str: str = "",
) -> go.Figure:
    """Donut chart: share of all records in each risk severity tier (same logic as bar chart)."""
    if frame.empty or "severity" not in frame.columns:
        severity_counts = pd.Series({"Low": 0, "Medium": 0, "High": 0})
    else:
        severity_counts = (
            frame["severity"].astype(str).value_counts().reindex(SEVERITY_ORDER, fill_value=0)
        )
    order = SEVERITY_ORDER
    values = [int(severity_counts.get(s, 0)) for s in order]
    colors = [SEVERITY_COLORS[s] for s in order]
    total = sum(values)
    labels_with_pct = [f"{s} ({v:,})" if total else s for s, v in zip(order, values)]

    figure = go.Figure(
        data=[
            go.Pie(
                labels=labels_with_pct,
                values=values,
                hole=0.55,
                marker_colors=colors,
                textinfo="label+percent",
                textposition="outside",
                hovertemplate="%{label}<br>Count: %{value:,}<br>%{percent}<extra></extra>",
            )
        ]
    )
    title = "Risk severity share (all records)"
    if date_range_str:
        title += f" ({date_range_str})"
    figure.update_layout(
        title=dict(text=title, font=dict(size=14)),
        margin=dict(l=20, r=20, t=50, b=20),
        font={"color": "#2C3318"},
        showlegend=False,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        annotations=[
            dict(
                text=f"Total<br>{total:,}" if total else "0",
                x=0.5, y=0.5, font=dict(size=14), showarrow=False,
            )
        ],
    )
    return figure


def make_alerts_over_time_line(
    frame: pd.DataFrame,
    date_range_str: str = "",
) -> go.Figure:
    """Monthly record counts by risk severity (full dataset; three lines Low/Medium/High)."""
    if frame.empty or "severity" not in frame.columns or "date" not in frame.columns:
        time_df = pd.DataFrame({"date": [], "count": [], "severity": []})
    else:
        tmp = frame.copy()
        tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
        tmp = tmp.dropna(subset=["date"])
        time_df = (
            tmp.groupby(["date", "severity"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )
    if time_df.empty:
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=[], y=[], mode="lines", name="Low"))
        figure.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of records",
            margin=dict(l=20, r=20, t=50, b=20),
            font={"color": "#2C3318"},
        )
    else:
        figure = px.line(
            time_df,
            x="date",
            y="count",
            color="severity",
            color_discrete_map=SEVERITY_COLORS,
            category_orders={"severity": SEVERITY_ORDER},
        )
    title = "Records by severity over time (monthly)"
    if date_range_str:
        title += f" — {date_range_str}"
    figure.update_layout(
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="Date",
        yaxis_title="Number of records",
        margin=dict(l=20, r=20, t=50, b=20),
        font={"color": "#2C3318"},
        xaxis={"gridcolor": "rgba(0,0,0,0.06)"},
        yaxis={"gridcolor": "rgba(0,0,0,0.06)"},
        legend_title="Severity",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
        hovermode="x unified",
    )
    return figure


def make_county_anomaly_heatmap(frame: pd.DataFrame) -> go.Figure:
    """Price anomaly heatmap by county (top counties × top commodities, anomaly rate)."""
    anomalies = frame[frame["pred_anomaly"] == 1] if "pred_anomaly" in frame.columns else frame.head(0)
    if frame.empty:
        pivot = pd.DataFrame()
    else:
        top_counties = (
            frame.groupby("COUNTY")["pred_anomaly"].sum().sort_values(ascending=False).head(14).index
        )
        top_commodities = (
            frame.groupby("commodity")["pred_anomaly"].sum().sort_values(ascending=False).head(12).index
        )
        sub = frame[
            frame["COUNTY"].isin(top_counties) & frame["commodity"].isin(top_commodities)
        ]
        pivot = (
            sub.groupby(["COUNTY", "commodity"])["pred_anomaly"].mean().reset_index().pivot(
                index="COUNTY", columns="commodity", values="pred_anomaly"
            )
        ).fillna(0)
    if pivot.empty:
        figure = go.Figure()
        figure.update_layout(title="Price anomaly heatmap by county")
        return figure
    figure = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=["#E8F5E9", "#F9A825", "#C62828"],
        title="Price anomaly heatmap by county",
        labels=dict(x="Commodity", y="County", color="Anomaly rate"),
    )
    figure.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        font={"color": "#2C3318"},
        xaxis={"tickangle": -45},
    )
    return figure


def make_commodity_anomaly_trend(frame: pd.DataFrame) -> go.Figure:
    """Commodity anomaly trend: anomaly count over time per commodity (top commodities)."""
    anomalies = frame[frame["pred_anomaly"] == 1] if "pred_anomaly" in frame.columns else pd.DataFrame()
    if anomalies.empty or "commodity" not in anomalies.columns:
        figure = go.Figure()
        figure.update_layout(
            title="Commodity anomaly trend",
            xaxis_title="Date",
            yaxis_title="Number of Alerts",
        )
        return figure
    top_commodities = (
        anomalies.groupby("commodity")["pred_anomaly"].sum().sort_values(ascending=False).head(8).index
    )
    sub = anomalies[anomalies["commodity"].isin(top_commodities)].copy()
    sub["date"] = pd.to_datetime(sub["date"]).dt.to_period("M").dt.to_timestamp()
    trend = (
        sub.groupby(["date", "commodity"])["pred_anomaly"].sum().reset_index().rename(
            columns={"pred_anomaly": "alerts"}
        )
    )
    figure = px.line(
        trend,
        x="date",
        y="alerts",
        color="commodity",
        title="Commodity anomaly trend (top commodities)",
    )
    figure.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        font={"color": "#2C3318"},
        xaxis_title="Date",
        yaxis_title="Number of Alerts",
        xaxis={"gridcolor": "rgba(0,0,0,0.06)"},
        yaxis={"gridcolor": "rgba(0,0,0,0.06)"},
        legend_title="Commodity",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
        hovermode="x unified",
    )
    return figure


def make_top_affected_commodities_bar(frame: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Top affected commodities (by number of detected alerts)."""
    if frame.empty or "pred_anomaly" not in frame.columns or "commodity" not in frame.columns:
        figure = go.Figure()
        figure.update_layout(
            title="Top affected commodities",
            xaxis_title="Number of Alerts",
            yaxis_title="Commodity",
            font={"color": "#2C3318"},
        )
        return figure

    anomalies = frame[frame["pred_anomaly"] == 1].copy()
    if anomalies.empty:
        figure = go.Figure()
        figure.update_layout(
            title="Top affected commodities",
            xaxis_title="Number of Alerts",
            yaxis_title="Commodity",
            font={"color": "#2C3318"},
        )
        return figure

    counts = (
        anomalies.groupby("commodity")["pred_anomaly"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .sort_values(ascending=True)
    )
    bar_df = counts.reset_index().rename(columns={"pred_anomaly": "alerts"})
    figure = px.bar(
        bar_df,
        x="alerts",
        y="commodity",
        orientation="h",
        title="Top affected commodities",
        text="alerts",
        color="alerts",
        color_continuous_scale=["#E8F5E9", "#F9A825", "#C62828"],
    )
    figure.update_traces(texttemplate="%{text:,}", textposition="outside")
    figure.update_layout(
        xaxis_title="Number of Alerts",
        yaxis_title="Commodity",
        margin=dict(l=20, r=20, t=50, b=20),
        font={"color": "#2C3318"},
        xaxis={"gridcolor": "rgba(0,0,0,0.06)"},
        yaxis={"gridcolor": "rgba(0,0,0,0.00)"},
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
        coloraxis_showscale=False,
    )
    return figure


def make_price_distribution_boxplot(frame: pd.DataFrame) -> go.Figure:
    """Price distribution by commodity (box plot)."""
    if frame.empty or "commodity" not in frame.columns or "price_real" not in frame.columns:
        figure = go.Figure()
        figure.update_layout(
            title="Price distribution by commodity",
            xaxis_title="Commodity",
            yaxis_title="Real price (per kg)",
            font={"color": "#2C3318"},
        )
        return figure

    plot_df = frame.copy()
    commodity_counts = plot_df["commodity"].value_counts()
    top_commodities = commodity_counts.head(10).index.tolist()
    plot_df = plot_df[plot_df["commodity"].isin(top_commodities)].copy()
    plot_df["is_anomaly"] = (plot_df.get("pred_anomaly", 0) == 1).astype(int)

    figure = px.box(
        plot_df,
        x="commodity",
        y="price_real",
        points="outliers",
        color="is_anomaly",
        color_discrete_map={0: "#3D6B35", 1: "#C62828"},
        title="Price distribution by commodity (top commodities)",
    )
    figure.update_layout(
        xaxis_title="Commodity",
        yaxis_title="Real price (per kg)",
        margin=dict(l=20, r=20, t=50, b=40),
        font={"color": "#2C3318"},
        xaxis={"tickangle": -30, "gridcolor": "rgba(0,0,0,0.00)"},
        yaxis={"gridcolor": "rgba(0,0,0,0.06)"},
        legend_title="Anomaly",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
    )
    figure.for_each_trace(
        lambda trace: trace.update(name="Anomaly" if trace.name == "1" else "Normal")
    )
    return figure


def make_feature_correlation_heatmap(frame: pd.DataFrame, max_features: int = 14) -> go.Figure:
    """Correlation heatmap for numeric features used in the model pipeline."""
    if frame.empty:
        figure = go.Figure()
        figure.update_layout(title="Feature correlation")
        return figure

    numeric = frame.select_dtypes(include=[np.number]).copy()
    drop_cols = [c for c in ["pred_anomaly"] if c in numeric.columns]
    numeric = numeric.drop(columns=drop_cols, errors="ignore")
    if numeric.shape[1] == 0:
        figure = go.Figure()
        figure.update_layout(title="Feature correlation")
        return figure

    variances = numeric.var().sort_values(ascending=False)
    keep = variances.head(min(max_features, len(variances))).index.tolist()
    corr = numeric[keep].corr().fillna(0)

    figure = px.imshow(
        corr,
        color_continuous_scale=["#E8F5E9", "#FFFFFF", "#C62828"],
        zmin=-1,
        zmax=1,
        title="Feature correlation",
    )
    figure.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        font={"color": "#2C3318"},
        coloraxis_colorbar_title="ρ",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    return figure


def make_anomaly_timeline(frame: pd.DataFrame) -> go.Figure:
    """Timeline-style view of anomaly frequency (monthly heat strip)."""
    if frame.empty or "date" not in frame.columns or "pred_anomaly" not in frame.columns:
        figure = go.Figure()
        figure.update_layout(title="Anomaly timeline")
        return figure

    df = frame.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("date", as_index=False)["pred_anomaly"].sum().rename(columns={"pred_anomaly": "alerts"})
    if monthly.empty:
        figure = go.Figure()
        figure.update_layout(title="Anomaly timeline")
        return figure

    monthly["y"] = "Alerts"
    figure = px.imshow(
        monthly.pivot(index="y", columns="date", values="alerts").fillna(0),
        aspect="auto",
        color_continuous_scale=["#E8F5E9", "#F9A825", "#C62828"],
        title="Anomaly timeline (monthly alert density)",
        labels=dict(x="Month", y="", color="Alerts"),
    )
    figure.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        font={"color": "#2C3318"},
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    return figure


def make_feature_importance_chart(model: object | None, feature_names: list[str]) -> go.Figure | None:
    if model is None:
        return None

    importances = None
    if hasattr(model, "feature_importances_"):
        importances = np.asarray(model.feature_importances_).reshape(-1)
    elif hasattr(model, "coef_"):
        importances = np.abs(np.asarray(model.coef_)).reshape(-1)

    if importances is None or len(importances) != len(feature_names):
        return None

    imp_df = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(10)
    )
    figure = px.bar(
        imp_df.sort_values("importance"),
        x="importance",
        y="feature",
        orientation="h",
        title="Top feature importance drivers",
        color="importance",
        color_continuous_scale=[CHART_GOLD, CHART_ANOMALY],
    )
    figure.update_layout(
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        showlegend=False,
        font={"color": "#2C3318"},
        xaxis={"gridcolor": CHART_GRID},
        yaxis={"gridcolor": CHART_GRID},
    )
    return figure


def make_local_interpretation_chart(
    record: pd.Series | None,
    model: object | None,
    feature_names: list[str],
) -> go.Figure | None:
    if record is None or model is None:
        return None

    importances = None
    if hasattr(model, "feature_importances_"):
        importances = np.asarray(model.feature_importances_).reshape(-1)
    elif hasattr(model, "coef_"):
        importances = np.abs(np.asarray(model.coef_)).reshape(-1)

    if importances is None or len(importances) != len(feature_names):
        return None

    values = np.asarray([float(record.get(feature, 0.0)) for feature in feature_names])
    contribution = np.abs(values) * importances
    total = contribution.sum()
    if total <= 0:
        return None

    local_df = (
        pd.DataFrame(
            {
                "feature": feature_names,
                "value": values,
                "contribution": contribution / total,
            }
        )
        .sort_values("contribution", ascending=False)
        .head(8)
    )

    figure = px.bar(
        local_df.sort_values("contribution"),
        x="contribution",
        y="feature",
        orientation="h",
        text=local_df.sort_values("contribution")["value"].round(3),
        title="Importance-weighted local drivers",
        color="contribution",
        color_continuous_scale=[CHART_GOLD, CHART_ANOMALY],
    )
    figure.update_traces(textposition="outside")
    figure.update_layout(
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        showlegend=False,
        xaxis_title="Relative contribution proxy",
        yaxis_title="Feature",
        font={"color": "#2C3318"},
        xaxis={"gridcolor": CHART_GRID},
        yaxis={"gridcolor": CHART_GRID},
    )
    return figure

