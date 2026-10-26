"""
Builds a small star schema for a Power BI people dashboard from the public
Human Resources Data Set (Dr. Rich Huebner, fictional, 311 employees, hires 2006-2018).

Output (./model, not committed to git):
  Employee.csv            one row per employee, no names or sensitive attributes
  Date.csv                month-end calendar
  HeadcountSnapshot.csv   one row per employee per month-end while employed
  Hires.csv               one row per hire, keyed to the hire month-end
  Terminations.csv        one row per leaver, keyed to the leaving month-end
  expected_values.csv     numbers your DAX measures should reproduce (for testing)

Privacy steps (the same ones you would agree with a works council):
  - names, date of birth, zip, race, citizenship, marital status are dropped
  - EmpID replaced by a random key; manager name dropped, manager kept as a key
  - age kept only as a band

Run:  python prepare_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE = "https://raw.githubusercontent.com/bisquittz/Human-Resources-Dataset-Analysis/main/HRDataset_v14.csv"
OUT = Path(__file__).parent / "model"
OUT.mkdir(exist_ok=True)
START, END = pd.Timestamp("2012-01-31"), pd.Timestamp("2018-12-31")
rng = np.random.default_rng(7)

raw = pd.read_csv(SOURCE, encoding="utf-8-sig")
for c in ["Position", "Department", "Sex", "TermReason", "EmploymentStatus", "RecruitmentSource", "PerformanceScore"]:
    raw[c] = raw[c].astype(str).str.strip()

hire = pd.to_datetime(raw["DateofHire"])
term = pd.to_datetime(raw["DateofTermination"])
dob = pd.to_datetime(raw["DOB"], format="%m/%d/%y")
dob = dob.where(dob.dt.year <= 2000, dob - pd.DateOffset(years=100))  # 2-digit years
age = ((END - dob).dt.days / 365.25).astype(int)

keys = rng.permutation(np.arange(1001, 1001 + len(raw)))
mgr_keys = {m: f"M{i:02d}" for i, m in enumerate(sorted(raw["ManagerID"].fillna(0).unique()), 1)}

emp = pd.DataFrame({
    "EmpKey": keys,
    "Department": raw["Department"],
    "Position": raw["Position"],
    "Sex": raw["Sex"],
    "AgeBand": pd.cut(age, [0, 29, 39, 49, 59, 120], labels=["<30", "30-39", "40-49", "50-59", "60+"]).astype(str),
    "ManagerKey": raw["ManagerID"].fillna(0).map(mgr_keys),
    "RecruitmentSource": raw["RecruitmentSource"],
    "PerformanceScore": raw["PerformanceScore"],
    "HireDate": hire.dt.date,
    "TermDate": term.dt.date,
    "TermType": np.select([raw["EmploymentStatus"] == "Voluntarily Terminated",
                           raw["EmploymentStatus"] == "Terminated for Cause"],
                          ["Voluntary", "Involuntary"], ""),
    "TermReason": raw["TermReason"].where(term.notna(), ""),
    "Salary": raw["Salary"],
    "EngagementSurvey": raw["EngagementSurvey"],
    "EmpSatisfaction": raw["EmpSatisfaction"],
    "Absences": raw["Absences"],
})
emp.to_csv(OUT / "Employee.csv", index=False)

months = pd.date_range(START, END, freq="ME")
date = pd.DataFrame({"MonthEnd": months.date, "Year": months.year, "MonthNo": months.month,
                     "Month": months.strftime("%b"), "YearMonth": months.strftime("%Y-%m")})
date.to_csv(OUT / "Date.csv", index=False)

snap = []
for m in months:
    active = (hire <= m) & (term.isna() | (term > m))
    snap.append(pd.DataFrame({"MonthEnd": m.date(), "EmpKey": keys[active.values]}))
snap = pd.concat(snap)
snap.to_csv(OUT / "HeadcountSnapshot.csv", index=False)

me = lambda s: (s + pd.offsets.MonthEnd(0)).dt.date
hires = pd.DataFrame({"HireMonthEnd": me(hire), "EmpKey": keys})
hires = hires[(pd.to_datetime(hires.HireMonthEnd) >= START) & (pd.to_datetime(hires.HireMonthEnd) <= END)]
hires.to_csv(OUT / "Hires.csv", index=False)
terms = pd.DataFrame({"TermMonthEnd": me(term), "EmpKey": keys, "TermType": emp["TermType"],
                      "TermReason": emp["TermReason"]})[term.notna().values]
terms = terms[(pd.to_datetime(terms.TermMonthEnd) >= START) & (pd.to_datetime(terms.TermMonthEnd) <= END)]
terms.to_csv(OUT / "Terminations.csv", index=False)

# ---------------------------------------------------------------- expected values at Dec 2018
m = END
e = emp.set_index("EmpKey")


def metrics(dept=None):
    s = snap if dept is None else snap[snap.EmpKey.map(e["Department"]) == dept]
    t = terms if dept is None else terms[terms.EmpKey.map(e["Department"]) == dept]
    win = [mm.date() for mm in months if m - pd.DateOffset(months=12) < mm <= m]
    hc_m = s[s.MonthEnd == m.date()]
    hc = hc_m.EmpKey.nunique()
    avg_hc = s[s.MonthEnd.isin(win)].groupby("MonthEnd").EmpKey.nunique().reindex(win, fill_value=0).mean()
    leavers = t[t.TermMonthEnd.isin(win)]
    cost = e.loc[hc_m.EmpKey, "Salary"].sum()
    tenure = ((m - pd.to_datetime(e.loc[hc_m.EmpKey, "HireDate"])).dt.days / 365.25).mean()
    return {
        "Department": dept or "All",
        "Headcount": hc,
        "Avg Headcount 12M": round(avg_hc, 2),
        "Leavers 12M": len(leavers),
        "Voluntary Leavers 12M": int((leavers.TermType == "Voluntary").sum()),
        "Attrition Rate 12M": round(len(leavers) / avg_hc, 4) if avg_hc else None,
        "Annual Personnel Cost": round(cost, 0),
        "Avg Salary": round(cost / hc, 0) if hc else None,
        "Avg Tenure (years)": round(tenure, 2),
        "Avg Engagement": round(e.loc[hc_m.EmpKey, "EngagementSurvey"].mean(), 2),
    }


rows = [metrics()] + [metrics(d) for d in sorted(emp.Department.unique())]
exp = pd.DataFrame(rows)
# Scenario defaults used in the guide: +5% headcount, attrition unchanged, +3% pay
g, a, p = 0.05, 0.0, 0.03
exp["Plan Headcount"] = (exp["Headcount"] * (1 + g)).round(0)
exp["Plan Leavers"] = (exp["Headcount"] * exp["Attrition Rate 12M"].fillna(0) * (1 + a)).round(0)
exp["Hires Needed"] = exp["Plan Headcount"] - exp["Headcount"] + exp["Plan Leavers"]
avg_sal_exact = (exp["Annual Personnel Cost"] / exp["Headcount"]).fillna(0)
exp["Plan Personnel Cost"] = (exp["Plan Headcount"] * avg_sal_exact * (1 + p)).round(0)
exp.to_csv(OUT / "expected_values.csv", index=False)
print(f"Employee {len(emp)}, months {len(date)}, snapshot rows {len(snap)}, hires {len(hires)}, leavers {len(terms)}")
print(exp.to_string(index=False))
