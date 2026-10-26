"""
Attrition risk model on the IBM HR Analytics Employee Attrition dataset.

The dataset is fictional. It was created by IBM data scientists for teaching and
is widely used for people analytics practice. 1,470 employees, 35 columns.

What the script does
1. Loads the data straight from the public source (no data file is stored in this repo).
2. Describes attrition by a few HR drivers (overtime, job level, tenure, income).
3. Fits a logistic regression to explain which drivers matter (odds ratios).
4. Compares it with a gradient boosting model on predictive power (cross-validated ROC AUC).
5. Checks that the model treats women and men alike at the chosen threshold.
6. Writes charts to ./charts and a results summary to ./results.md.

Protected attributes (gender, marital status, age) are left out of the model features.
Gender is used only afterwards, to check the model for unequal treatment.

Run:  python attrition_model.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SOURCE = "https://raw.githubusercontent.com/IBM/employee-attrition-aif360/master/data/emp_attrition.csv"
HERE = Path(__file__).parent
CHARTS = HERE / "charts"
CHARTS.mkdir(exist_ok=True)
SEED = 42

NAVY, GREY, ORANGE = "#1F3864", "#8C8C8C", "#D9822B"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

# ---------------------------------------------------------------- load
df = pd.read_csv(SOURCE, encoding="utf-8-sig")
df["left"] = (df["Attrition"] == "Yes").astype(int)
n, rate = len(df), df["left"].mean()

# ---------------------------------------------------------------- describe
df["TenureBand"] = pd.cut(df["YearsAtCompany"], [-1, 1, 3, 5, 10, 50],
                          labels=["0-1", "2-3", "4-5", "6-10", "10+"])
df["IncomeBand"] = pd.qcut(df["MonthlyIncome"], 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])

def rate_by(col):
    t = df.groupby(col, observed=True)["left"].agg(["mean", "size"])
    t["mean"] = (t["mean"] * 100).round(1)
    return t.rename(columns={"mean": "attrition_%", "size": "employees"})

tables = {c: rate_by(c) for c in ["OverTime", "JobLevel", "TenureBand", "IncomeBand", "Department"]}

fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
for ax, col, title in zip(axes, ["OverTime", "TenureBand", "IncomeBand"],
                          ["Overtime", "Years at company", "Monthly income quartile"]):
    t = tables[col]
    ax.bar(t.index.astype(str), t["attrition_%"], color=NAVY)
    ax.axhline(rate * 100, color=ORANGE, lw=1, ls="--")
    ax.set_title(title)
    ax.set_ylabel("Attrition %")
    ax.tick_params(axis="x", rotation=20)
    for i, v in enumerate(t["attrition_%"]):
        ax.text(i, v + 0.6, f"{v:.0f}%", ha="center", fontsize=9)
axes[0].text(1.45, rate * 100 + 0.8, f"overall {rate*100:.1f}%", color=ORANGE, fontsize=8, ha="right")
fig.suptitle("Attrition rate by driver (IBM HR dataset, n = 1,470)", x=0.01, ha="left")
fig.tight_layout()
fig.savefig(CHARTS / "01_attrition_by_driver.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- features
protected = ["Gender", "MaritalStatus", "Age"]
drop = ["Attrition", "left", "EmployeeCount", "EmployeeNumber", "Over18", "StandardHours",
        "TenureBand", "IncomeBand", "DailyRate", "HourlyRate", "MonthlyRate"] + protected
X = df.drop(columns=drop)
y = df["left"]
cat_cols = X.select_dtypes(include=["object", "string"]).columns.tolist()
num_cols = [c for c in X.columns if c not in cat_cols]

pre = ColumnTransformer([
    ("num", StandardScaler(), num_cols),
    ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), cat_cols),
])
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

models = {
    "Logistic regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
    "Gradient boosting": GradientBoostingClassifier(random_state=SEED),
}
scores = {}
for name, m in models.items():
    pipe = Pipeline([("pre", pre), ("model", m)])
    p = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    scores[name] = {"auc": roc_auc_score(y, p), "proba": p}

best_name = max(scores, key=lambda k: scores[k]["auc"])
proba = scores[best_name]["proba"]

# Threshold: flag the top 20% highest-risk employees for a stay conversation.
thr = np.quantile(proba, 0.80)
flag = (proba >= thr).astype(int)
prec, rec = precision_score(y, flag), recall_score(y, flag)

# ---------------------------------------------------------------- drivers (statsmodels logit)
key = ["OverTime", "JobLevel", "YearsAtCompany", "TotalWorkingYears", "JobSatisfaction",
       "EnvironmentSatisfaction", "WorkLifeBalance", "StockOptionLevel", "DistanceFromHome",
       "NumCompaniesWorked", "BusinessTravel", "YearsSinceLastPromotion", "JobInvolvement"]
D = pd.get_dummies(df[key], drop_first=True, dtype=float)
D = sm.add_constant(D)
logit = sm.Logit(y, D).fit(disp=0)
orr = pd.DataFrame({
    "odds_ratio": np.exp(logit.params),
    "ci_low": np.exp(logit.conf_int()[0]),
    "ci_high": np.exp(logit.conf_int()[1]),
    "p_value": logit.pvalues,
}).drop("const").sort_values("odds_ratio", ascending=False)

sig = orr[orr["p_value"] < 0.05]
fig, ax = plt.subplots(figsize=(7, 4.2))
ypos = np.arange(len(sig))
ax.errorbar(sig["odds_ratio"], ypos, xerr=[sig["odds_ratio"] - sig["ci_low"], sig["ci_high"] - sig["odds_ratio"]],
            fmt="o", color=NAVY, ecolor=GREY, capsize=3)
ax.axvline(1, color=ORANGE, ls="--", lw=1)
ax.set_yticks(ypos, sig.index)
ax.set_xscale("log")
ax.set_xlabel("Odds ratio (log scale). Above 1 = higher attrition risk")
ax.set_title("Significant attrition drivers (logistic regression, p < 0.05)", loc="left")
fig.tight_layout()
fig.savefig(CHARTS / "02_odds_ratios.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- fairness check by gender
fair = pd.DataFrame({"gender": df["Gender"], "y": y, "flag": flag})
fair_tbl = fair.groupby("gender").apply(
    lambda g: pd.Series({
        "employees": len(g),
        "actual_attrition_%": round(g["y"].mean() * 100, 1),
        "flagged_%": round(g["flag"].mean() * 100, 1),
        "recall_%": round(recall_score(g["y"], g["flag"]) * 100, 1),
    }), include_groups=False)

# ---------------------------------------------------------------- what-if: overtime
# If overtime employees had the attrition rate of non-overtime employees (descriptive, not causal).
ot = tables["OverTime"]
leavers_now = df["left"].sum()
ot_n = (df["OverTime"] == "Yes").sum()
leavers_if = leavers_now - ot_n * (ot.loc["Yes", "attrition_%"] - ot.loc["No", "attrition_%"]) / 100

# ---------------------------------------------------------------- write results
with open(HERE / "results.md", "w") as f:
    f.write("# Results (generated by attrition_model.py)\n\n")
    f.write(f"- Employees: {n:,}. Overall attrition: {rate*100:.1f}%.\n")
    for k, v in scores.items():
        f.write(f"- {k}: cross-validated ROC AUC {v['auc']:.3f}\n")
    f.write(f"- Model used for the risk list: {best_name}.\n")
    f.write(f"- Flagging the top 20% risk scores catches {rec*100:.0f}% of actual leavers; "
            f"{prec*100:.0f}% of flagged employees actually left (base rate {rate*100:.0f}%).\n")
    f.write(f"- Overtime what-if (descriptive): about {leavers_now - leavers_if:.0f} fewer leavers "
            f"out of {leavers_now} if overtime staff left at the non-overtime rate.\n\n")
    for k, t in tables.items():
        f.write(f"## Attrition by {k}\n\n{t.to_markdown()}\n\n")
    f.write("## Odds ratios (logistic regression)\n\n" + orr.round(3).to_markdown() + "\n\n")
    f.write("## Fairness check by gender (top-20% flag)\n\n" + fair_tbl.to_markdown() + "\n")

print(open(HERE / "results.md").read()[:1500])
