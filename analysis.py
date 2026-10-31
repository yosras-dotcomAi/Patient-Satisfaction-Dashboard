"""
Analysis of simulated patient experience survey data (NHS Friends and Family Test style)
----------------------------------------------------------------------------------------
Input : data/patient_survey.csv  (SIMULATED data)
Output: results/*.csv and images/*.png

FFT percent positive = (Very good + Good) / all responses, including "Don't know",
which is how NHS trusts report it.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats

os.makedirs("results", exist_ok=True)
os.makedirs("images", exist_ok=True)

df = pd.read_csv("data/patient_survey.csv", parse_dates=["response_date"])
df["positive"] = df["overall_experience"].isin(["Very good", "Good"]).astype(int)
df["negative"] = df["overall_experience"].isin(["Poor", "Very poor"]).astype(int)
df["month"] = df["response_date"].dt.to_period("M").astype(str)

SERVICE_ORDER = ["Emergency Department", "Outpatients", "Inpatients", "Maternity"]
TEAL, GREY, RED = "#2a9d8f", "#9aa0a6", "#c0392b"


def pct_row(group, k, n):
    """Percent with an exact (Clopper-Pearson) 95% confidence interval."""
    ci = stats.binomtest(int(k), int(n)).proportion_ci(method="exact")
    return {"Group": group, "Responses": int(n), "Positive": int(k),
            "Percent_positive": round(100 * k / n, 1),
            "CI_low": round(100 * ci.low, 1), "CI_high": round(100 * ci.high, 1)}


# ---------- 1. FFT positive score by service ----------
rows = [pct_row("All services", df["positive"].sum(), len(df))]
for s in SERVICE_ORDER:
    sub = df[df["service"] == s]
    rows.append(pct_row(s, sub["positive"].sum(), len(sub)))
by_service = pd.DataFrame(rows)
by_service["Percent_negative"] = [
    round(100 * (df if g == "All services" else df[df["service"] == g])["negative"].mean(), 1)
    for g in by_service["Group"]]
by_service.to_csv("results/positive_by_service.csv", index=False)
print("FFT PERCENT POSITIVE BY SERVICE (exact 95% CI)")
print(by_service.to_string(index=False))

# ---------- 2. Monthly trend by service ----------
monthly = (df.groupby(["service", "month"])
             .agg(responses=("positive", "size"), positive=("positive", "sum"))
             .reset_index())
monthly["percent_positive"] = (100 * monthly["positive"] / monthly["responses"]).round(1)
monthly.to_csv("results/monthly_positive.csv", index=False)

# ---------- 3. Waiting time bands ----------
bins = [0, 30, 60, 120, 240, 1000]
labels = ["Under 30 min", "30-60 min", "1-2 hours", "2-4 hours", "Over 4 hours"]
df["wait_band"] = pd.cut(df["wait_minutes"], bins=bins, labels=labels)
wait_rows = []
for band, sub in df.groupby("wait_band", observed=True):
    r = pct_row(str(band), sub["positive"].sum(), len(sub))
    wait_rows.append(r)
wait_table = pd.DataFrame(wait_rows)
wait_table.to_csv("results/positive_by_wait_band.csv", index=False)
print("\nPERCENT POSITIVE BY WAITING TIME")
print(wait_table[["Group", "Responses", "Percent_positive", "CI_low", "CI_high"]].to_string(index=False))

# ---------- 4. What drives a positive experience? (logistic regression) ----------
model_df = df[df["overall_experience"] != "Don't know"].copy()
X = pd.DataFrame({
    "Wait: +30 minutes": model_df["wait_minutes"] / 30,
    "Communication: +1 rating point": model_df["communication_rating"],
    "Kindness: +1 rating point": model_df["kindness_rating"],
    "Cleanliness: +1 rating point": model_df["cleanliness_rating"],
    "Age: +10 years": model_df["age"] / 10,
})
service_dummies = pd.get_dummies(model_df["service"], drop_first=False)
service_dummies = service_dummies.drop(columns="Outpatients").astype(float)
X = pd.concat([X, service_dummies.add_prefix("Service: ")], axis=1)
X = sm.add_constant(X)
fit = sm.Logit(model_df["positive"], X).fit(disp=False)
ci = fit.conf_int()
drivers = pd.DataFrame({
    "Factor": fit.params.index,
    "Odds_ratio": np.exp(fit.params).round(2).values,
    "CI_low": np.exp(ci[0]).round(2).values,
    "CI_high": np.exp(ci[1]).round(2).values,
    "p_value": fit.pvalues.round(4).values,
})
drivers = drivers[drivers["Factor"] != "const"]
drivers.to_csv("results/drivers_logistic.csv", index=False)
print("\nODDS OF A POSITIVE EXPERIENCE (logistic regression, reference service: Outpatients)")
print(drivers.to_string(index=False))

# ---------- 5. Charts ----------
# 5a. Positive score by service
fig, ax = plt.subplots(figsize=(7.5, 4.5))
sub = by_service[by_service["Group"] != "All services"].set_index("Group").loc[SERVICE_ORDER].reset_index()
x = np.arange(len(sub))
ax.bar(x, sub["Percent_positive"], color=TEAL,
       yerr=[sub["Percent_positive"] - sub["CI_low"], sub["CI_high"] - sub["Percent_positive"]],
       capsize=5)
for i, r in sub.iterrows():
    ax.text(i, r["CI_low"] - 4.5, f"{r['Percent_positive']:.0f}%", ha="center",
            color="white", fontsize=10, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(sub["Group"])
ax.set_ylim(50, 100)
ax.set_ylabel("Percent positive (Very good or Good)")
ax.set_title("Friends and Family Test: percent positive by service\n(simulated data, exact 95% CI)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("images/positive_by_service.png", dpi=130)
plt.close()

# 5b. Monthly trend
fig, ax = plt.subplots(figsize=(8.5, 4.8))
colors = {"Emergency Department": RED, "Outpatients": TEAL, "Inpatients": "#264653", "Maternity": "#e9c46a"}
for s in SERVICE_ORDER:
    m = monthly[monthly["service"] == s]
    ax.plot(m["month"], m["percent_positive"], marker="o", label=s, color=colors[s])
ax.set_ylabel("Percent positive")
ax.set_title("Monthly percent positive by service (simulated data)")
ax.tick_params(axis="x", rotation=60)
ax.legend(frameon=False, fontsize=9, ncol=2)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("images/monthly_trend.png", dpi=130)
plt.close()

# 5c. Waiting time
fig, ax = plt.subplots(figsize=(7.5, 4.5))
x = np.arange(len(wait_table))
ax.bar(x, wait_table["Percent_positive"], color=TEAL,
       yerr=[wait_table["Percent_positive"] - wait_table["CI_low"],
             wait_table["CI_high"] - wait_table["Percent_positive"]], capsize=5)
for i, r in wait_table.iterrows():
    ax.text(i, 52, f"n={r['Responses']}", ha="center", color="white", fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(wait_table["Group"])
ax.set_ylim(50, 100)
ax.set_ylabel("Percent positive")
ax.set_title("Percent positive by waiting time (all services, simulated data)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("images/positive_by_wait.png", dpi=130)
plt.close()

# 5d. Drivers
fig, ax = plt.subplots(figsize=(8, 4.8))
d = drivers[~drivers["Factor"].str.startswith("Service")].iloc[::-1].reset_index(drop=True)
y = np.arange(len(d))
ax.errorbar(d["Odds_ratio"], y, xerr=[d["Odds_ratio"] - d["CI_low"], d["CI_high"] - d["Odds_ratio"]],
            fmt="o", color=TEAL, ecolor=GREY, capsize=3)
ax.axvline(1, color=RED, linestyle="--", linewidth=1)
ax.set_xscale("log")
ax.set_xticks([0.8, 1, 1.25, 1.5, 2])
ax.set_xticklabels(["0.8", "1", "1.25", "1.5", "2"])
ax.minorticks_off()
ax.set_yticks(y)
ax.set_yticklabels(d["Factor"])
ax.set_xlabel("Odds ratio for a positive experience (log scale, 95% CI)")
ax.set_title("What is linked to a positive experience? (simulated data)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("images/drivers.png", dpi=130)
plt.close()

print("\nDone: results/ and images/ saved.")
