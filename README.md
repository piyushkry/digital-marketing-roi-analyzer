# Campaign Intelligence

**Digital Marketing Campaign ROI & Funnel Analyzer** — Turn Marketing Data Into Profitable Decisions.

Local Streamlit dashboard for campaign performance, channel comparison, funnel drop-offs, monthly trends, rule-based budget scenarios, recommendations, and exports. It uses no paid APIs. Monetary values are displayed in INR. ROI is calculated from revenue because the dataset does not include product costs or profit; it is not profit-based ROI.

## Structure

```text
digital_marketing_roi_analyzer/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/config.toml
├── data/sample_campaign_data.csv
├── modules/{__init__.py,data_processing.py,metrics.py,visualizations.py,recommendations.py,report_generator.py}
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

## Verify modules

From the project directory after installing requirements:

```powershell
python -m compileall app.py modules
python -c "from modules.data_processing import load_sample_data; from modules.metrics import summarize,channel_performance,monthly_performance,funnel_metrics; from modules.recommendations import generate_recommendations,budget_allocation; from modules.report_generator import create_pdf_report; d=load_sample_data(); p=channel_performance(d); f,drop=funnel_metrics(d); print(len(d),summarize(d),len(monthly_performance(d)),drop); assert len(d)>=200 and len(p)==4"
streamlit run app.py
```

In the app, check filters, CSV and Excel uploads, both CSV downloads, and the PDF download. The sample report is included under `reports/` for demonstration. Uploads are processed in the local running process. The CSV and XLSX upload readers, validation, formula calculations, all chart constructors, CSV serializations, and PDF generation can also be exercised with the importable functions in `modules/`.
