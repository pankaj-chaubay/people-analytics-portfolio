"""
Gender pay gap analysis in the format the EU Pay Transparency Directive asks for.

The directive is Directive (EU) 2023/970. Employers report the gender pay gap overall and
per category of workers. Where a gap of 5% or more in a category is not explained by
objective, gender-neutral factors, a joint pay assessment with employee representatives
is required.

Two public, fictional datasets are used:
  A. IBM HR Analytics Employee Attrition (1,470 employees, monthly income, job level, role)
  B. Human Resources Data Set by Dr. Rich Huebner (311 employees, salary, position)

For each dataset:
1. Unadjusted gap: difference in mean and median pay, women vs men.
2. Gap per category of workers (A: job level, B: position).
3. Adjusted gap: log-pay regression with gender-neutral controls.
4. Categories at or above the 5% threshold are flagged. Categories with fewer than
   MIN_GROUP women or men are suppressed, so no individual salary can be worked out.

Run:  python pay_equity.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

SOURCE_A = "https://raw.githubusercontent.com/IBM/employee-attrition-aif360/master/data/emp_attrition.csv"
SOURCE_B = "https://raw.githubusercontent.com/bisquittz/Human-Resources-Dataset-Analysis/main/HRDataset_v14.csv"
HERE = Path(__file__).parent
CHARTS = HERE / "charts"
CHARTS.mkdir(exist_ok=True)
NAVY, ORANGE, GREY = "#1F3864", "#D9822B", "#8C8C8C"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
THRESHOLD = 5.0   # % gap that triggers a joint pay assessment if unexplained
MIN_GROUP = 3     # suppress categories with fewer women or men than this (anonymity)


def gap(g):
    """Gap in % of men's pay. Positive = women paid less."""
    m, w = g[g.gender == "M"]["pay"], g[g.gender == "F"]["pay"]
    out = {"men": len(m), "women": len(w), "mean_gap_%": np.nan, "median_gap_%": np.nan}
    if len(m) >= MIN_GROUP and len(w) >= MIN_GROUP:
        out["mean_gap_%"] = round((m.mean() - w.mean()) / m.mean() * 100, 1)
        out["median_gap_%"] = round((m.median() - w.median()) / m.median() * 100, 1)
    return pd.Series(out)


def adjusted(df, formula):
    model = smf.ols(formula, data=df).fit(cov_type="HC1")
    b = model.params["female"]
    lo, hi = model.conf_int().loc["female"]
    pct = lambda v: (np.exp(v) - 1) * 100
    return {"adj_%": pct(b), "lo_%": pct(lo), "hi_%": pct(hi), "p": model.pvalues["female"], "r2": model.rsquared}


def analyse(df, category, formula):
    df = df.copy()
    df["log_pay"] = np.log(df["pay"])
    df["female"] = (df["gender"] == "F").astype(int)
    overall = gap(df)
    cat = df.groupby(category).apply(gap, include_groups=False)
    cat["status"] = np.where(cat["mean_gap_%"].isna(), "suppressed (small group)",
                    np.where((cat["mean_gap_%"].abs() >= THRESHOLD) | (cat["median_gap_%"].abs() >= THRESHOLD),
                             "5%+ gap: check", "below 5%"))
    return overall, cat, adjusted(df, formula)


# ---------------------------------------------------------------- dataset A
a = pd.read_csv(SOURCE_A, encoding="utf-8-sig")
a = a.assign(pay=a["MonthlyIncome"], gender=a["Gender"].str[0])
ov_a, cat_a, adj_a = analyse(
    a, "JobLevel",
    "log_pay ~ female + C(JobLevel) + C(JobRole) + TotalWorkingYears + YearsAtCompany"
    " + C(Education) + C(PerformanceRating)")

# ---------------------------------------------------------------- dataset B
b = pd.read_csv(SOURCE_B, encoding="utf-8-sig")
b["Position"] = b["Position"].str.strip()           # 'Data Analyst ' and 'Data Analyst' are one job
b = b.assign(pay=b["Salary"], gender=b["Sex"].str.strip())
b["tenure_years"] = (pd.Timestamp("2019-01-01") - pd.to_datetime(b["DateofHire"])).dt.days / 365.25
ov_b, cat_b, adj_b = analyse(
    b, "Position", "log_pay ~ female + C(Position) + tenure_years + C(PerformanceScore)")
cat_b = cat_b.sort_values("men", ascending=False)

# ---------------------------------------------------------------- chart (dataset B, reportable positions)
rep = cat_b.dropna(subset=["mean_gap_%"]).sort_values("mean_gap_%")
fig, ax = plt.subplots(figsize=(7, 3.6))
colors = [ORANGE if s == "5%+ gap: check" else NAVY for s in rep["status"]]
ax.barh(rep.index, rep["mean_gap_%"], color=colors)
for t in (THRESHOLD, -THRESHOLD):
    ax.axvline(t, color=ORANGE, ls="--", lw=1)
ax.axvline(0, color="black", lw=0.6)
for i, (v, n_w, n_m) in enumerate(zip(rep["mean_gap_%"], rep["women"], rep["men"])):
    ax.text(v + (0.4 if v >= 0 else -0.4), i, f"{v:+.1f}%  (W {int(n_w)} / M {int(n_m)})",
            va="center", ha="left" if v >= 0 else "right", fontsize=8)
ax.set_xlabel("Mean gap, % of men's pay (+ = women paid less)")
ax.set_title("Mean gap per position, reportable groups only (dataset B)\nOrange = mean or median gap of 5% or more", loc="left", fontsize=10)
ax.set_xlim(rep["mean_gap_%"].min() - 8, rep["mean_gap_%"].max() + 14)
fig.tight_layout()
fig.savefig(CHARTS / "01_gap_by_position.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- results
def block(name, ov, cat, adj, cat_label):
    s = [f"## {name}\n",
         f"- Unadjusted gap: mean {ov['mean_gap_%']}%, median {ov['median_gap_%']}% "
         f"({int(ov['women'])} women, {int(ov['men'])} men). Negative = women paid more.",
         f"- Adjusted gap: women earn {adj['adj_%']:+.1f}% vs comparable men "
         f"(95% CI {adj['lo_%']:+.1f}% to {adj['hi_%']:+.1f}%, p = {adj['p']:.2f}, R-squared {adj['r2']:.2f}).",
         f"- {cat_label} at or above 5%: "
         f"{', '.join(map(str, cat[cat.status == '5%+ gap: check'].index)) or 'none'}.",
         f"- {cat_label} suppressed (fewer than {MIN_GROUP} women or men): {(cat.status.str.startswith('suppressed')).sum()} "
         f"of {len(cat)}.\n",
         cat.to_markdown(), "\n"]
    return "\n".join(s)

with open(HERE / "results.md", "w") as f:
    f.write("# Results (generated by pay_equity.py)\n\n")
    f.write(block("Dataset A: IBM HR (category = job level)", ov_a, cat_a, adj_a, "Job levels"))
    f.write(block("Dataset B: Huebner HR (category = position)", ov_b, cat_b, adj_b, "Positions"))

print(open(HERE / "results.md").read()[:2500])
