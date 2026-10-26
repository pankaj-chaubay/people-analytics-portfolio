# Power BI people dashboard and workforce plan

**Question:** how many people do we have, who is leaving, what do they cost, and what does next year's plan need in hires and budget?

**Data:** Human Resources Data Set by Dr. Rich Huebner. Fictional, 311 employees, hires from 2006 to 2018. Prepared into a star schema by [prepare_data.py](prepare_data.py).

## What is in it

- **Data model:** Employee, Date (month-end), HeadcountSnapshot, Hires, Terminations
- **Measures:** headcount, rolling 12-month attrition (total and voluntary), personnel cost, average tenure, engagement and absence. See [measures.dax](measures.dax).
- **Workforce plan:** what-if sliders for headcount growth, change in attrition and pay increase. These show the hires needed and next year's personnel cost by department.
- **Privacy:** names, date of birth, zip, race, citizenship and marital status are dropped before loading. Age is kept as a band only.

## Baseline (Dec 2018, from `model/expected_values.csv`)

| | Value |
|---|---|
| Headcount | 207 |
| Attrition, last 12 months | 6.1% (13 leavers, 9 voluntary) |
| Annual personnel cost | 14.6 M (latest salaries) |
| Plan at +5% growth, same attrition, +3% pay | 217 heads, 23 hires needed, personnel cost 15.8 M |

## Screenshots

_Add after building the report: see [BUILD_GUIDE.md](BUILD_GUIDE.md), step 7._

## Build it yourself

Follow [BUILD_GUIDE.md](BUILD_GUIDE.md). `expected_values.csv` holds the numbers each measure should return, so you can test the DAX.

Limits: the source has only the latest salary, so cost history uses today's pay. Engagement is one survey score per person.
