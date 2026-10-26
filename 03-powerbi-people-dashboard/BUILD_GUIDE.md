# Build guide: Power BI people dashboard

About 3-4 hours in Power BI Desktop (free, Windows). Work through the steps in order. At the end, check your numbers against `model/expected_values.csv`.

## 1. Prepare the data

```
pip install -r ../requirements.txt
python prepare_data.py
```

This writes six CSV files to `model/`.

## 2. Load the tables

Home > Get data > Text/CSV. Load `Employee`, `Date`, `HeadcountSnapshot`, `Hires` and `Terminations` (not `expected_values`).

In Power Query, check the column types:

| Table | Column | Type |
|---|---|---|
| Date | MonthEnd | Date |
| Employee | HireDate, TermDate | Date |
| Employee | Salary, Absences | Whole number |
| Employee | EngagementSurvey | Decimal number |
| HeadcountSnapshot | MonthEnd | Date |
| Hires | HireMonthEnd | Date |
| Terminations | TermMonthEnd | Date |

## 3. Relationships (Model view)

| From (one side) | To (many side) |
|---|---|
| Date[MonthEnd] | HeadcountSnapshot[MonthEnd] |
| Date[MonthEnd] | Hires[HireMonthEnd] |
| Date[MonthEnd] | Terminations[TermMonthEnd] |
| Employee[EmpKey] | HeadcountSnapshot[EmpKey] |
| Employee[EmpKey] | Hires[EmpKey] |
| Employee[EmpKey] | Terminations[EmpKey] |

All single direction, from the one side to the many side. Right-click `Date` > Mark as date table > `MonthEnd`. Sort `Date[Month]` by `Date[MonthNo]`.

## 4. Measures

1. Home > Enter data. Name the table `_Measures`, then load it.
2. Modeling > New parameter > Numeric range. Create the three parameters from the comment block in `measures.dax` (Growth, Attrition Change, Pay Increase). Keep "Add slicer to this page" ticked.
3. Copy each measure from `measures.dax` into `_Measures` (New measure, paste one at a time).
4. Formats: rates as percentage with 1 decimal place, cost as currency with no decimals, tenure with 1 decimal place.

## 5. Pages

**1. Overview**
- Cards: Headcount, Attrition Rate 12M, Voluntary Attrition Rate 12M, Avg Tenure (years), Annual Personnel Cost
- Line chart: Headcount by Date[YearMonth]
- Clustered bar: Headcount by Employee[Department]
- Slicer: Date[Year] (single select), Employee[Department]

**2. Attrition**
- Line chart: Attrition Rate 12M and Voluntary Attrition Rate 12M by Date[YearMonth]
- Bar: Leavers by Terminations[TermReason] (top 10)
- Matrix: Department x Year with Leavers and Attrition Rate 12M
- Bar: Attrition Rate 12M by Employee[RecruitmentSource]

**3. Workforce plan**
- The three parameter slicers
- Cards: Headcount, Plan Headcount, Plan Leavers, Hires Needed, Plan Personnel Cost, Cost Change %
- Table by Department: Headcount, Attrition Rate 12M, Plan Headcount, Hires Needed, Plan Personnel Cost

**4. Engagement and absence**
- Scatter: Avg Engagement (x) vs Attrition Rate 12M (y), details = Department
- Bar: Avg Absences by Department
- Note on the page: "Engagement score is the latest survey result per employee."

## 6. Check your numbers

Set the year slicer to 2018 (the last month is Dec 2018) and the scenario to +5% growth, attrition change 0, pay increase 3%. Each card should match the `All` row of `model/expected_values.csv`. Filter one department and check its row too. If a number does not match, it is almost always a relationship direction or a date column typed as text.

## 7. Publish

- File > Export > PDF for the README screenshots, or take a screenshot of each page and save it to `screenshots/`.
- Save the .pbix in this folder. Power BI files can hold data, so check you are fine sharing the fictional data before you push it to GitHub.
- Add the screenshots to this folder's README under "Screenshots".
