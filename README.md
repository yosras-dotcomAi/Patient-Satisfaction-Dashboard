# Patient-Satisfaction-Dashboard
Goal: Visualize patient survey data (e.g., satisfaction with nurses, doctors, wait times, cleanliness, overall experience).
Patient-Satisfaction-Dashboard/
│── data/
│   └── patient_satisfaction.csv
│── app.py                 # Streamlit dashboard code
│── requirements.txt       # libraries (streamlit, pandas, matplotlib, plotly)
│── README.md              # project explanation + screenshots
│── screenshots/           # images of dashboard

import pandas as pd
import numpy as np

np.random.seed(42)

n = 500

departments = ["Emergency", "ICU", "OPD", "Surgery", "Radiology"]
gender = ["Male", "Female"]

data = {
    "Patient_ID": range(1, n+1),
    "Department": np.random.choice(departments, n),
    "Gender": np.random.choice(gender, n),
    "Age": np.random.randint(18, 80, n),
    "Wait_Time": np.random.randint(5, 180, n),  # in minutes
    "Staff_Friendliness": np.random.randint(1, 6, n),
    "Cleanliness": np.random.randint(1, 6, n),
    "Communication": np.random.randint(1, 6, n),
    "Overall_Satisfaction": np.random.randint(1, 11, n),
}

df = pd.DataFrame(data)
df.to_csv("patient_satisfaction.csv", index=False)

print("✅ patient_satisfaction.csv created with", n, "rows")
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------
# Load Data
# ---------------------------
@st.cache_data
def load_data():
    return pd.read_csv("data/patient_satisfaction.csv")

df = load_data()

# ---------------------------
# Sidebar Filters
# ---------------------------
st.sidebar.header("Filters")
department_filter = st.sidebar.multiselect("Select Department:", options=df["Department"].unique(), default=df["Department"].unique())
gender_filter = st.sidebar.multiselect("Select Gender:", options=df["Gender"].unique(), default=df["Gender"].unique())

df_filtered = df[(df["Department"].isin(department_filter)) & (df["Gender"].isin(gender_filter))]

# ---------------------------
# Main Dashboard
# ---------------------------
st.title("🏥 Patient Satisfaction Dashboard")

# KPIs
avg_wait = int(df_filtered["Wait_Time"].mean())
avg_satisfaction = round(df_filtered["Overall_Satisfaction"].mean(), 1)
happy_patients = round((df_filtered["Overall_Satisfaction"] >= 8).mean() * 100, 1)

col1, col2, col3 = st.columns(3)
col1.metric("⏳ Avg Wait Time (min)", avg_wait)
col2.metric("😊 Avg Satisfaction (1-10)", avg_satisfaction)
col3.metric("👍 % Happy Patients", f"{happy_patients}%")

st.markdown("---")

# ---------------------------
# Charts
# ---------------------------

# Satisfaction by Department
st.subheader("📊 Average Satisfaction by Department")
dept_chart = df_filtered.groupby("Department")["Overall_Satisfaction"].mean().reset_index()
fig_dept = px.bar(dept_chart, x="Department", y="Overall_Satisfaction", color="Department", text_auto=True)
st.plotly_chart(fig_dept, use_container_width=True)

# Cleanliness Distribution
st.subheader("🧼 Cleanliness Ratings Distribution")
fig_clean = px.histogram(df_filtered, x="Cleanliness", nbins=5, color="Department", barmode="group")
st.plotly_chart(fig_clean, use_container_width=True)

# Satisfaction vs Wait Time
st.subheader("⏱️ Wait Time vs. Satisfaction")
fig_scatter = px.scatter(df_filtered, x="Wait_Time", y="Overall_Satisfaction", color="Department", size="Communication", hover_data=["Age"])
st.plotly_chart(fig_scatter, use_container_width=True)

# Gender Comparison
st.subheader("👩‍⚕️ Satisfaction by Gender")
gender_chart = df_filtered.groupby("Gender")["Overall_Satisfaction"].mean().reset_index()
fig_gender = px.bar(gender_chart, x="Gender", y="Overall_Satisfaction", color="Gender", text_auto=True)
st.plotly_chart(fig_gender, use_container_width=True)

st.markdown("📌 *This dashboard is based on simulated survey data.*")
streamlit
pandas
plotly
# 🏥 Patient Satisfaction Dashboard

An interactive dashboard to analyze patient satisfaction survey data.  
Built with **Python, Streamlit, Pandas, and Plotly**.

## 📊 Features
- KPIs: Avg wait time, Avg satisfaction, % happy patients
- Charts:
  - Satisfaction by Department
  - Cleanliness distribution
  - Wait time vs. satisfaction
  - Gender comparison
- Interactive filters (department, gender)

