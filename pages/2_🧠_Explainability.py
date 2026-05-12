from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.app_state import APP_END_DATE, APP_START_DATE, get_app_context
from src.explainability import compute_global_shap_summary, compute_local_shap_explanation
from src.streamlit_plotly import plotly_chart_interactive
from src.theme import apply_custom_theme, render_badge


st.set_page_config(page_title="Explainability Hub | Market Pulse AI", page_icon="🧠", layout="wide")
apply_custom_theme()

st.title("🧠 Intelligence Explainability")
st.markdown(
    """
    Explore the **SHAP (SHapley Additive exPlanations)** drivers behind the model's decisions. 
    This transparency layer helps you understand which features are pushing price records toward 'Anomaly' status.
    """
)

context = get_app_context()
bundle = context["bundle"]
dashboard_df = context["dashboard_df"]
artifact_status = context["artifact_status"]

hist_df = dashboard_df[
    dashboard_df["date"].between(pd.Timestamp(APP_START_DATE), pd.Timestamp(APP_END_DATE))
].copy()

if hist_df.empty:
    st.error("No historical records are available for SHAP interpretation.")
    st.stop()

with st.sidebar:
    st.header("Interpretability Filters")
    render_badge("Deployed Model", artifact_status["best_model"], tone="blue")
    render_badge("Threshold", artifact_status["threshold"])

    commodities = sorted(hist_df["commodity"].dropna().unique().tolist())
    counties = sorted(hist_df["COUNTY"].dropna().unique().tolist())

    selected_commodities = st.multiselect(
        "Commodity",
        options=commodities,
        default=commodities[: min(5, len(commodities))],
    )
    selected_counties = st.multiselect("County", options=counties, default=[])

filtered_df = hist_df.copy()
if selected_commodities:
    filtered_df = filtered_df[filtered_df["commodity"].isin(selected_commodities)]
if selected_counties:
    filtered_df = filtered_df[filtered_df["COUNTY"].isin(selected_counties)]

if filtered_df.empty:
    st.error("No historical records match the selected interpretability filters.")
    st.stop()

top_section = st.columns([1.25, 1.0])
with top_section[0]:
    st.subheader("Global SHAP Summary")
    if st.button("Generate global SHAP summary", use_container_width=True):
        global_summary, global_error = compute_global_shap_summary(
            filtered_df,
            bundle,
            sample_size=200,
            background_size=50,
        )
        if global_error:
            st.info(global_error)
        elif global_summary is not None:
            summary_fig = px.bar(
                global_summary.head(12).sort_values("mean_abs_shap"),
                x="mean_abs_shap",
                y="feature",
                orientation="h",
                title="Global Feature Importance (Mean |SHAP|)",
                color="mean_abs_shap",
                color_continuous_scale=["#10B981", "#EF4444"], # Emerald to Red
            )
            summary_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#F8FAFC",
                title_font_family="Outfit",
                xaxis=dict(showgrid=True, gridcolor="#334155"),
                yaxis=dict(showgrid=False),
                showlegend=False
            )
            plotly_chart_interactive(summary_fig)
    else:
        st.info("Click the button to generate a SHAP summary for the filtered historical sample.")

with top_section[1]:
    st.subheader("Model Context")
    st.markdown(
        f"""
**Model in use:** `{artifact_status['best_model']}`  
**Scoring mode:** `{artifact_status['mode']}`  
**Rows available for SHAP:** `{len(filtered_df):,}`
"""
    )
    st.markdown(
        """
SHAP values show how each feature pushes the model output toward a higher or lower anomaly prediction for the deployed model.
"""
    )

st.subheader("Local SHAP Interpretation")
candidate_records = filtered_df.sort_values("risk_score", ascending=False).head(50).copy()
candidate_records["label"] = candidate_records.apply(
    lambda row: (
        f"{row['date']:%Y-%m} | {row['COUNTY']} | {row['commodity']} | "
        f"score={row['risk_score']:.3f}"
    ),
    axis=1,
)
selected_label = st.selectbox("Select case to explain", options=candidate_records["label"].tolist())
selected_record = candidate_records.loc[candidate_records["label"] == selected_label].iloc[0]

local_cols = st.columns([1.2, 1.0])
with local_cols[0]:
    if st.button("Generate local SHAP explanation", use_container_width=True):
        local_explanation, local_error = compute_local_shap_explanation(selected_record, filtered_df, bundle)
        if local_error:
            st.info(local_error)
        elif local_explanation is not None:
            local_fig = px.bar(
                local_explanation.head(12).sort_values("shap_value"),
                x="shap_value",
                y="feature",
                orientation="h",
                title="Case-Level Driver Analysis (SHAP)",
                color="shap_value",
                color_continuous_scale=["#10B981", "#334155", "#EF4444"], # Emeral -> Neutral -> Red
            )
            local_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#F8FAFC",
                title_font_family="Outfit",
                xaxis=dict(showgrid=True, gridcolor="#334155"),
                yaxis=dict(showgrid=False),
                showlegend=False
            )
            plotly_chart_interactive(local_fig)
    else:
        st.info("Click the button to generate a SHAP explanation for the selected case.")

with local_cols[1]:
    st.markdown(
        f"""
**Selected case**
- County: `{selected_record['COUNTY']}`
- Commodity: `{selected_record['commodity']}`
- Date: `{selected_record['date']:%Y-%m-%d}`
- Observed price: `{selected_record['price_real']:.2f}`
- Risk score: `{selected_record['risk_score']:.3f}`
- Predicted anomaly: `{int(selected_record['pred_anomaly'])}`
"""
    )
    if "local_explanation" in locals() and local_explanation is not None:
        st.dataframe(
            local_explanation.head(12)[["feature", "feature_value", "shap_value", "abs_shap"]],
            use_container_width=True,
            hide_index=True,
        )

