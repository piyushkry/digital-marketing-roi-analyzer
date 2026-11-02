# Campaign Intelligence

**Digital Marketing Campaign ROI & Funnel Analyzer** — Turn Marketing Data Into Profitable Decisions.

Local Streamlit dashboard for campaign performance, channel comparison, funnel drop-offs, monthly trends, rule-based budget scenarios, recommendations, and exports. It also includes campaign comparison, period-over-period analysis, campaign rankings, performance alerts, and configurable marketing goals. It uses no paid APIs. Monetary values are displayed in INR. ROI is calculated from revenue because the dataset does not include product costs or profit; it is not profit-based ROI.

## Structure

```text
digital_marketing_roi_analyzer/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/config.toml
├── data/sample_campaign_data.csv
├── modules/{__init__.py,data_processing.py,metrics.py,advanced_analytics.py,visualizations.py,recommendations.py,report_generator.py}
├── tests/test_advanced_analytics.py
└── reports/sample_analytics_report.pdf
```

## Install and run (Windows PowerShell)

Install Python 3.10 or newer. Then:

```powershell
cd digital_marketing_roi_analyzer
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the terminal, or invoke `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe -m streamlit run app.py`.

The included deterministic sample has 240 campaign records spanning 12 months and all four channels. CSV, XLSX, and XLS uploads are supported. Required columns: `Date, Campaign_ID, Campaign_Name, Channel, Impressions, Clicks, Leads, Conversions, Ad_Spend, Revenue`. Channels: Google Ads, Meta Ads, Email Marketing, Influencer Marketing (common short names are normalized). Values must be nonnegative and funnel stage counts must not increase down-funnel. Invalid uploads display a helpful sidebar error and sample data remains available. Date and channel filters apply to every dashboard view; selecting no channel returns no records.

## Measures

CTR = Clicks / Impressions × 100; CPC = Spend / Clicks; CPL = Spend / Leads; CPA = Spend / Conversions; conversion rate = Conversions / Clicks × 100; revenue-based ROI = (Revenue − Spend) / Spend × 100; ROAS = Revenue / Spend. Rates are calculated from aggregated totals. Zero denominators yield N/A. Budget scenarios and recommendations are transparent rules based on the filtered historical records, not forecasts or guarantees. Since cost of goods and profit are absent, revenue-based ROI must not be interpreted as profit ROI.

## Added analytical pages

- **Campaign Comparison:** compare selected campaign totals and recomputed CTR, CPC, CPA, ROI, and ROAS. The chart metric is selectable; the table retains all requested measures.
- **Period-over-Period:** compares the selected date range with the immediately preceding equal-length calendar window, using the same channel selection. Missing periods and zero prior denominators are displayed as unavailable. ROI movement is expressed in percentage points.
- **Campaign Rankings:** rank the filtered campaigns by ROI, revenue, CPA, conversion rate, or conversions; refine by channel and result count. The table is sortable.
- **Performance Alerts:** rule-based checks for negative ROI, high CPA, high spend without conversions, revenue declines, and significant conversion changes. Initial CPA and spend thresholds are the filtered median positive CPA and 75th-percentile positive spend; both are adjustable in the page.
- **Marketing Goals & Targets:** enter monthly revenue and conversion targets, maximum CPA, and minimum revenue-based ROI. Monthly targets are prorated to the selected calendar days; a zero target is treated as unset.

Period comparisons use records in the uploaded or sample data; no values are imputed for absent periods. The app does not forecast campaign outcomes.

## Verify modules

From the project directory after installing requirements:

```powershell
python -m compileall app.py modules
python -m unittest discover -s tests -v
python -c "from modules.data_processing import load_sample_data; from modules.metrics import summarize,channel_performance,monthly_performance,funnel_metrics; from modules.recommendations import generate_recommendations,budget_allocation; from modules.report_generator import create_pdf_report; d=load_sample_data(); p=channel_performance(d); f,drop=funnel_metrics(d); print(len(d),summarize(d),len(monthly_performance(d)),drop); assert len(d)>=200 and len(p)==4"
streamlit run app.py
```

The automated `unittest` suite covers campaign ratios and zero denominators, ranking order, equal-length periods and missing baselines, alert rules and thresholds, and monthly target proration. The Streamlit pages can be smoke-tested with `streamlit.testing.v1.AppTest` or in the browser. In the app, also check filters, CSV and Excel uploads, both CSV downloads, and the PDF download. The sample report is included under `reports/` for demonstration. Uploads are processed in the local running process.
