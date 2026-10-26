# People analytics portfolio

Three small projects on public, fictional HR data. They show the work I do in people analytics: attrition analysis, pay equity, and a workforce dashboard with a planning scenario. Each folder has its own README with the method and results.

| Project | What it answers | Tools |
|---|---|---|
| [01 Attrition risk model](01-attrition-risk-model) | Who is most likely to leave, and which drivers matter? | Python, scikit-learn, statsmodels |
| [02 Pay equity analysis](02-pay-equity-analysis) | Is there a gender pay gap, overall and per job category, as the EU Pay Transparency Directive asks? | Python, statsmodels |
| [03 Power BI people dashboard](03-powerbi-people-dashboard) | Headcount, attrition, personnel cost and a 12-month workforce plan with what-if sliders | Power BI, DAX, Python (data prep) |

## How to run

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python 01-attrition-risk-model/attrition_model.py
python 02-pay-equity-analysis/pay_equity.py
python 03-powerbi-people-dashboard/prepare_data.py
```

The scripts download the data from the public source each time. No data files are stored here.

## Data and privacy

Both datasets are fictional and published for learning:

- IBM HR Analytics Employee Attrition (1,470 employees), from IBM's public GitHub repository
- Human Resources Data Set by Dr. Rich Huebner (311 employees), via a public GitHub mirror

I still handle them as if they were real personnel data. Names and sensitive attributes are dropped, protected attributes are kept out of the attrition model, and small groups are suppressed in the pay analysis so no individual salary can be worked out. In a German company these are the points I would agree with the data protection officer and the works council before any analysis starts.

## Related repositories

- [hr-kpi-sql-library](https://github.com/pankaj-chaubay/hr-kpi-sql-library): the same KPIs in SQL, with a KPI dictionary and a cross-check against this dashboard
- [hr-data-quality-checks](https://github.com/pankaj-chaubay/hr-data-quality-checks): SQL rules that find and fix problems in personnel records
- [jd-standardiser-local-llm](https://github.com/pankaj-chaubay/jd-standardiser-local-llm): job descriptions into one template with a local LLM, GDPR-aware

## About me

Pankaj Chaubay, Munich. HR reporting, workforce analytics and HR data quality since 2011. [LinkedIn](https://www.linkedin.com/in/pankaj-chaubay/)
