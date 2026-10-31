"""
Patient Experience Dashboard (Streamlit)
Simulated NHS Friends and Family Test style survey data. Not real patient data.
Run locally:  streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Patient Experience Dashboard", page_icon="🏥", layout="wide")

SERVICES = ["Emergency Department", "Outpatients", "Inpatients", "Maternity"]
RATING_ORDER = ["Very good", "Good", "Neither good nor poor", "Poor", "Very poor", "Don't know"]
RATING_COLORS = {"Very good": "#1b7f6b", "Good": "#7cc4b3", "Neither good nor poor": "#d9d9d9",
                 "Poor": "#e8a598", "Very poor": "#c0392b", "Don't know": "#f3f3f3"}


@st.cache_data
def load_data():
    df = pd.read_csv("data/patient_survey.csv", parse_dates=["response_date"])
    df["positive"] = df["overall_experience"].isin(["Very good", "Good"])
    df["negative"] = df["overall_experience"].isin(["Poor", "Very poor"])
    df["month"] = df["response_date"].dt.to_period("M").dt.to_timestamp()
    bins = [0, 30, 60, 120, 240, 1000]
    labels = ["Under 30 min", "30-60 min", "1-2 hours", "2-4 hours", "Over 4 hours"]
    df["wait_band"] = pd.cut(df["wait_minutes"], bins=bins, labels=labels)
    return df


df = load_data()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
services = st.sidebar.multiselect("Service", SERVICES, default=SERVICES)
months = sorted(df["month"].unique())
start, end = st.sidebar.select_slider(
    "Months", options=months, value=(months[0], months[-1]),
    format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"))
view = df[df["service"].isin(services) & (df["month"] >= start) & (df["month"] <= end)]

st.title("🏥 Patient Experience Dashboard")
st.warning("This dashboard uses **simulated data** built to resemble NHS Friends and Family "
           "Test results. It contains no real patient or hospital data.")

if view.empty:
    st.info("No responses match the selected filters.")
    st.stop()

# ---------- KPIs ----------
n = len(view)
pos = view["positive"].mean() * 100
neg = view["negative"].mean() * 100
c1, c2, c3, c4 = st.columns(4)
c1.metric("Responses", f"{n:,}")
c2.metric("Percent positive", f"{pos:.1f}%")
c3.metric("Percent negative", f"{neg:.1f}%")
c4.metric("Median wait (min)", int(view["wait_minutes"].median()))
st.caption("Percent positive = (Very good + Good) divided by all responses, including "
           "'Don't know', as NHS trusts report the Friends and Family Test.")

tab1, tab2, tab3 = st.tabs(["Overview", "Waiting time", "What drives experience"])

# ---------- Overview ----------
with tab1:
    left, right = st.columns(2)
    monthly = (view.groupby(["service", "month"])
                   .agg(responses=("positive", "size"), positive=("positive", "mean"))
                   .reset_index())
    monthly["Percent positive"] = (monthly["positive"] * 100).round(1)
    fig = px.line(monthly, x="month", y="Percent positive", color="service", markers=True,
                  title="Percent positive by month")
    fig.update_layout(xaxis_title=None, legend_title=None, legend_orientation="h",
                      legend_y=-0.25)
    left.plotly_chart(fig, width="stretch")

    dist = (view.groupby(["service", "overall_experience"]).size()
                .groupby(level=0).transform(lambda s: s / s.sum() * 100)
                .reset_index(name="Percent"))
    fig = px.bar(dist, x="Percent", y="service", color="overall_experience", orientation="h",
                 category_orders={"overall_experience": RATING_ORDER, "service": SERVICES},
                 color_discrete_map=RATING_COLORS, title="Rating distribution by service")
    fig.update_layout(yaxis_title=None, legend_title=None, legend_orientation="h",
                      legend_y=-0.3)
    right.plotly_chart(fig, width="stretch")

# ---------- Waiting time ----------
with tab2:
    band = (view.groupby("wait_band", observed=True)
                .agg(responses=("positive", "size"), positive=("positive", "mean"))
                .reset_index())
    band["Percent positive"] = (band["positive"] * 100).round(1)
    fig = px.bar(band, x="wait_band", y="Percent positive", text="Percent positive",
                 hover_data=["responses"], title="Percent positive by waiting time")
    fig.update_traces(marker_color="#2a9d8f", texttemplate="%{text:.0f}%")
    fig.update_layout(xaxis_title=None, yaxis_range=[50, 100])
    st.plotly_chart(fig, width="stretch")
    st.caption("Small groups have wide uncertainty. Check the response counts when hovering.")

# ---------- Drivers ----------
with tab3:
    ratings = {"communication_rating": "Communication", "kindness_rating": "Kindness",
               "cleanliness_rating": "Cleanliness"}
    comp = (view.assign(Group=np.where(view["positive"], "Positive experience", "Not positive"))
                .groupby("Group")[list(ratings)].mean().rename(columns=ratings)
                .reset_index().melt(id_vars="Group", var_name="Rating", value_name="Average (1-5)"))
    fig = px.bar(comp, x="Rating", y="Average (1-5)", color="Group", barmode="group",
                 color_discrete_map={"Positive experience": "#2a9d8f", "Not positive": "#c0392b"},
                 title="Average staff and environment ratings")
    fig.update_layout(yaxis_range=[1, 5], legend_title=None)
    st.plotly_chart(fig, width="stretch")
    st.caption("Positive-experience patients rated communication and kindness higher. "
               "The full odds-ratio analysis is in the repository (analysis.py).")

with st.expander("About this project"):
    st.write("Simulated survey of 2,400 responses in 2025 across four services. "
             "Source code, assumptions and references are in the GitHub repository.")
