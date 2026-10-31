"""
Synthetic data generator: NHS-style patient experience survey (Friends and Family Test)
---------------------------------------------------------------------------------------
Creates 2,400 SIMULATED survey responses for 2025 across four services and saves them to
data/patient_survey.csv. No real patient or hospital data is used.

Survey structure (modelled on the NHS Friends and Family Test):
  overall_experience : Very good / Good / Neither good nor poor / Poor / Very poor / Don't know
  % positive         : (Very good + Good) / all responses, including Don't know

How the numbers were chosen
  - Target positive scores per service are set close to published monthly results of an
    NHS trust (see README): inpatients about 95%, outpatients about 93%, maternity about
    90%, emergency department about 80% (ED results vary widely by month).
  - How waiting time, communication, kindness and cleanliness affect the overall rating
    is an ASSUMPTION based on common sense, not a published effect size.
  - Emergency waits are made longer in winter months (assumption), so the dashboard has
    a trend worth investigating.
Change the constants below to test other assumptions.
"""

import os
import numpy as np
import pandas as pd

SEED = 2025
N_RESPONSES = 2400

SERVICES = ["Emergency Department", "Outpatients", "Inpatients", "Maternity"]
SERVICE_MIX = [0.35, 0.30, 0.25, 0.10]
TARGET_POSITIVE = {"Emergency Department": 0.80, "Outpatients": 0.93,
                   "Inpatients": 0.95, "Maternity": 0.90}
MEDIAN_WAIT = {"Emergency Department": 150, "Outpatients": 20,
               "Inpatients": 60, "Maternity": 30}        # minutes
WAIT_SPREAD = {"Emergency Department": 0.50, "Outpatients": 0.80,
               "Inpatients": 0.60, "Maternity": 0.60}
WINTER_ED_WAIT_MULTIPLIER = 1.30                          # Dec, Jan, Feb

# Effect of each driver on the latent experience score (ASSUMPTIONS)
B_WAIT = -0.60            # per unit of log(wait / typical wait)
B_COMM, B_KIND, B_CLEAN = 0.55, 0.40, 0.25   # per rating point above 4
CUT_NEGATIVE, CUT_NEUTRAL, CUT_POSITIVE, CUT_VERY_GOOD = -1.9, -1.2, 0.0, 1.7
P_DONT_KNOW = 0.02

rng = np.random.default_rng(SEED)
os.makedirs("data", exist_ok=True)
n = N_RESPONSES

service = rng.choice(SERVICES, n, p=SERVICE_MIX)
date = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
month = date.month.values

age_mean = {"Emergency Department": 46, "Outpatients": 52, "Inpatients": 61, "Maternity": 29}
age = np.array([rng.normal(age_mean[s], 15 if s != "Maternity" else 5) for s in service])
age = age.round().clip(16, 95).astype(int)
sex = np.where(service == "Maternity", "Female", np.where(rng.random(n) < 0.52, "Female", "Male"))

# ---------- Waiting time (minutes) ----------
median = np.array([MEDIAN_WAIT[s] for s in service], dtype=float)
winter = np.isin(month, [12, 1, 2]) & (service == "Emergency Department")
median = median * np.where(winter, WINTER_ED_WAIT_MULTIPLIER, 1.0)
spread = np.array([WAIT_SPREAD[s] for s in service])
wait = (median * np.exp(rng.normal(0, spread))).round().clip(1, 600).astype(int)
typical = np.array([MEDIAN_WAIT[s] for s in service], dtype=float)
rel_wait = np.log(wait / typical)

# ---------- Staff and environment ratings (1 to 5) ----------
def rating(base, sd=0.8):
    return np.clip(np.round(rng.normal(base, sd, n)), 1, 5).astype(int)

# Long waits slightly lower communication ratings (assumption)
communication = np.clip(np.round(rng.normal(4.3, 0.8, n) - 0.25 * np.clip(rel_wait, 0, 2)), 1, 5).astype(int)
kindness = rating(4.4)
cleanliness = rating(4.3)

# ---------- Latent experience score and FFT rating ----------
latent_core = (B_WAIT * rel_wait + B_COMM * (communication - 4)
               + B_KIND * (kindness - 4) + B_CLEAN * (cleanliness - 4)
               + rng.logistic(0, 1, n))

# Shift each service so its positive score matches the target
shift = np.zeros(n)
for s in SERVICES:
    idx = service == s
    cut = np.quantile(latent_core[idx], 1 - TARGET_POSITIVE[s] / (1 - P_DONT_KNOW))
    shift[idx] = -cut + CUT_POSITIVE
latent = latent_core + shift

labels = np.select(
    [latent >= CUT_VERY_GOOD, latent >= CUT_POSITIVE, latent >= CUT_NEUTRAL,
     latent >= CUT_NEGATIVE],
    ["Very good", "Good", "Neither good nor poor", "Poor"], default="Very poor")
labels = np.where(rng.random(n) < P_DONT_KNOW, "Don't know", labels)

df = pd.DataFrame({
    "response_id": [f"R{10000 + i}" for i in range(n)],
    "response_date": date.strftime("%Y-%m-%d"),
    "service": service,
    "age": age,
    "sex": sex,
    "wait_minutes": wait,
    "communication_rating": communication,
    "kindness_rating": kindness,
    "cleanliness_rating": cleanliness,
    "overall_experience": labels,
}).sort_values("response_date").reset_index(drop=True)
df["response_id"] = [f"R{10000 + i}" for i in range(n)]
df.to_csv("data/patient_survey.csv", index=False)

pos = df["overall_experience"].isin(["Very good", "Good"])
print(f"Saved {len(df)} simulated survey responses to data/patient_survey.csv")
print("Positive score by service (%):")
print((pos.groupby(df["service"]).mean() * 100).round(1).to_string())
