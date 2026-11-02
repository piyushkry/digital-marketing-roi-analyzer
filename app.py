"""Streamlit business intelligence dashboard for campaign ROI and funnel analysis."""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.data_processing import CHANNELS, filter_data, load_sample_data, validate_data
from modules.metrics import campaign_performance, channel_performance, funnel_metrics, monthly_performance, summarize
from modules.recommendations import budget_allocation, generate_insights, generate_recommendations
from modules.advanced_analytics import (
    CAMPAIGN_METRICS, RANKING_METRICS, campaign_metrics, default_alert_thresholds,
    generate_performance_alerts, goal_attainment, period_frames, period_over_period,
    rank_campaigns,
)
from modules.report_generator import create_pdf_report
from modules.visualizations import (
    budget_chart, campaign_metric_chart, channel_bar, channel_contribution_chart,
    funnel_chart, monthly_chart, period_comparison_chart, ranking_chart,
    revenue_spend_chart,
)


st.set_page_config(
    page_title="Campaign Intelligence | Marketing BI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --navy:#142B4A; --navy-2:#1C3C64; --ink:#142B4A; --muted:#52647D;
            --blue:#2457A7; --accent:#3B82F6; --green:#10B981; --orange:#F59E0B;
            --red:#EF4444; --line:#E5EAF2; --canvas:#F5F7FB; }
    .stApp { background:var(--canvas); color:var(--ink); }
    /* Keep Streamlit's layout header transparent so its empty surface doesn't
       paint a pale badge over the top edge of the dashboard workspace. */
    [data-testid="stHeader"] { background:transparent !important; }
    [data-testid="stHeader"] [data-testid="stAppDeployButton"],
    [data-testid="stHeader"] [data-testid="stMainMenu"],
    #MainMenu { display:none !important; }
    [data-testid="stSidebar"] { background:var(--navy); border-right:1px solid #28466E; }
    [data-testid="stSidebarContent"] { padding-top:.55rem !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.65rem !important; }
    [data-testid="stMainBlockContainer"] { padding-top:.8rem !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color:#F2F6FC !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color:#D1DDEE !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] * { color:#17243B !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] input { background:transparent !important; color:#F2F6FC !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"] { background:#DBEAFE !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"] * { color:#17305A !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section { background:#1B365B; border-color:#54709A; }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section * { color:#EAF0FC !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
      color:#17305A !important; background:#FFFFFF !important; border:1px solid #C8D3E2 !important;
      border-radius:7px !important; font-weight:650 !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button * { color:#17305A !important; }
    .hero { padding:1.15rem 1.55rem; border-radius:16px; color:#FFFFFF;
            background:linear-gradient(115deg,#142B4A,#2457A7); margin:0 0 1rem 0;
            box-shadow:0 8px 24px rgba(20,43,74,.12); }
    .hero h1 { color:#FFFFFF !important; margin:0; font-size:1.8rem; letter-spacing:-.025em; }
    .hero p { color:#E3ECF8 !important; margin:.35rem 0 0; font-size:.94rem; }
    .section-intro { color:var(--muted); margin-top:-.35rem; margin-bottom:1rem; }
    div[data-testid="stMetric"] { background:#FFFFFF; border:1px solid var(--line); padding:15px 16px;
      border-radius:14px; box-shadow:0 3px 12px rgba(20,43,74,.045); min-height:102px; }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"],
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
      color:#425670 !important; -webkit-text-fill-color:#425670 !important;
      opacity:1 !important; font-size:.81rem; font-weight:650; }
    div[data-testid="stMetricValue"] { color:var(--ink) !important; font-weight:720; }
    div[data-testid="stMetricDelta"] { color:var(--muted) !important; }
    div[data-testid="stAlert"] { border-radius:12px; }
    .method-note { color:#34465F; background:#EAF0F8; border-left:4px solid #3B82F6;
      padding:.8rem 1rem; border-radius:0 10px 10px 0; font-size:.9rem; }
    .brand-lockup { display:flex; align-items:center; gap:.65rem; padding:.4rem 0 .1rem; }
    .brand-icon { width:38px; height:38px; flex:none; }
    .brand-name { color:#FFFFFF; font-weight:750; font-size:1.05rem; letter-spacing:-.02em; }
    .brand-tagline { color:#C5D4E8; font-size:.75rem; line-height:1.35; margin:.2rem 0 .2rem 3.05rem; }
    .insight-card { background:#FFFFFF; border:1px solid var(--line); border-radius:14px;
      padding:1rem 1.1rem; margin:0 0 .75rem; box-shadow:0 3px 12px rgba(20,43,74,.04); }
    .insight-card h4 { color:#142B4A; margin:0 0 .35rem; font-size:1rem; }
    .insight-card p { color:#40536D; margin:.3rem 0; font-size:.9rem; line-height:1.45; }
    .insight-evidence { color:#2457A7 !important; font-weight:650; }
    .priority { float:right; border-radius:999px; padding:.2rem .55rem; font-size:.72rem; font-weight:700; }
    .priority-high { background:#FEE2E2; color:#991B1B; }
    .priority-medium { background:#FEF3C7; color:#854D0E; }
    .priority-low { background:#DCFCE7; color:#166534; }
    [data-testid="stDownloadButton"] button, [data-testid="stButton"] button {
      background:#2457A7 !important; color:#FFFFFF !important; border:1px solid #2457A7 !important;
      border-radius:9px !important; font-weight:650 !important; }
    [data-testid="stDownloadButton"] button:hover, [data-testid="stButton"] button:hover {
      background:#1B468B !important; color:#FFFFFF !important; }
    [data-testid="collapsedControl"] button, [data-testid="stSidebarCollapsedControl"] button,
    button[data-testid="collapsedControl"], button[data-testid="stSidebarCollapsedControl"] {
      color:#142B4A !important; background:#FFFFFF !important; border:1px solid #CBD5E1 !important;
      box-shadow:0 2px 8px rgba(20,43,74,.14) !important; border-radius:9px !important; }
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {
      visibility:visible !important; opacity:1 !important; }
    button[data-testid="collapsedControl"], button[data-testid="stSidebarCollapsedControl"] {
      display:flex !important; position:fixed !important; top:.75rem !important; left:.75rem !important;
      z-index:999999 !important; width:2.35rem !important; height:2.35rem !important; }
    [data-testid="stExpandSidebarButton"] {
      display:flex !important; position:fixed !important; top:.75rem !important; left:.75rem !important;
      z-index:1000001 !important; width:2.45rem !important; height:2.45rem !important;
      color:#142B4A !important; background:#FFFFFF !important; border:1px solid #CBD5E1 !important;
      border-radius:9px !important; box-shadow:0 2px 8px rgba(20,43,74,.16) !important;
      visibility:visible !important; opacity:1 !important; }
    [data-testid="stExpandSidebarButton"] svg {
      fill:#142B4A !important; color:#142B4A !important; stroke:#142B4A !important; opacity:1 !important; }
    button[data-testid="collapsedControl"] svg, button[data-testid="stSidebarCollapsedControl"] svg {
      fill:#142B4A !important; color:#142B4A !important; opacity:1 !important; }
    button[aria-label="Expand sidebar"], button[aria-label="Collapse sidebar"] {
      display:flex !important; align-items:center !important; justify-content:center !important;
      visibility:visible !important; opacity:1 !important; background:#FFFFFF !important;
      color:#142B4A !important; border:1px solid #CBD5E1 !important; border-radius:9px !important;
      box-shadow:0 2px 8px rgba(20,43,74,.16) !important; }
    button[aria-label="Expand sidebar"] { position:fixed !important; top:.75rem !important; left:.75rem !important;
      z-index:1000000 !important; width:2.45rem !important; height:2.45rem !important; }
    button[aria-label="Expand sidebar"] svg, button[aria-label="Collapse sidebar"] svg {
      fill:#142B4A !important; color:#142B4A !important; stroke:#142B4A !important; opacity:1 !important; }
    [data-testid="stSidebarHeader"] button, [data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarCollapseButton"] {
      color:#F2F6FC !important; fill:#F2F6FC !important; background:#1C3C64 !important;
      border:1px solid #54709A !important; border-radius:8px !important;
      visibility:visible !important; opacity:1 !important; }
    [data-testid="stSidebarHeader"] button svg,
    [data-testid="stSidebarCollapseButton"] svg { fill:#F2F6FC !important; color:#F2F6FC !important; }
    [data-testid="stSidebarHeader"] button:hover,
    [data-testid="stSidebarCollapseButton"]:hover { background:#2457A7 !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"],
    [data-testid="stSidebar"] span[data-baseweb="tag"] {
      background:#2457A7 !important; border-color:#4D76B4 !important; color:#FFFFFF !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"] *,
    [data-testid="stSidebar"] span[data-baseweb="tag"] * {
      background-color:#2457A7 !important; color:#FFFFFF !important; }
    [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    @media (max-width: 900px) { .hero { padding:1rem 1.1rem; } .hero h1 {font-size:1.45rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_inr(value, decimals=0):
    """Format currency with the rupee symbol and Indian digit grouping."""
    if value is None or pd.isna(value):
        return "N/A"
    value = float(value)
    number = f"{abs(value):.{decimals}f}"
    whole, dot, fraction = number.partition(".")
    if len(whole) > 3:
        last_three, prefix = whole[-3:], whole[:-3]
        pairs = []
        while prefix:
            pairs.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        whole = ",".join(pairs + [last_three])
    return f"{'-' if value < 0 else ''}₹{whole}{dot}{fraction if dot else ''}"


def format_percent(value, decimals=1):
    return "N/A" if value is None or pd.isna(value) else f"{value:.{decimals}f}%"


def show_kpis(kpis):
    cards = [
        ("Revenue", format_inr(kpis["Revenue"]), "Observed revenue in the filtered period."),
        ("Marketing Spend", format_inr(kpis["Ad_Spend"]), "Observed campaign ad spend in INR."),
        ("ROI", format_percent(kpis["ROI"], 1), "Revenue-based ROI; it is not profit-based ROI."),
        ("ROAS", "N/A" if pd.isna(kpis["ROAS"]) else f"{kpis['ROAS']:.2f}x", "Revenue divided by ad spend."),
        ("Impressions", f"{kpis['Impressions']:,.0f}", "Campaign impressions in the filtered period."),
        ("Clicks", f"{kpis['Clicks']:,.0f}", "Campaign clicks in the filtered period."),
        ("Leads", f"{kpis['Leads']:,.0f}", "Leads recorded in the filtered period."),
        ("Conversions", f"{kpis['Conversions']:,.0f}", "Conversions recorded in the filtered period."),
    ]
    for start in range(0, len(cards), 4):
        row = cards[start : start + 4]
        columns = st.columns(4)
        for column, (label, value, help_text) in zip(columns, row):
            column.metric(label, value, help=help_text)


def format_table(frame):
    formats = {}
    currency_columns = [
        "Ad_Spend", "Revenue", "CPC", "CPL", "CPA", "Proposed Budget",
    ]
    percent_columns = ["CTR (%)", "Conversion Rate (%)", "ROI (%)", "Allocation (%)", "Current Allocation (%)"]
    for column in currency_columns:
        if column in frame.columns:
            formats[column] = lambda value: format_inr(value, 2)
    for column in percent_columns:
        if column in frame.columns:
            formats[column] = lambda value: format_percent(value, 1)
    if "ROAS" in frame.columns:
        formats["ROAS"] = lambda value: "N/A" if pd.isna(value) else f"{value:.2f}x"
    return frame.style.format(formats, na_rep="—")


def transition_for(stage):
    previous = {"Clicks": "Impressions", "Leads": "Clicks", "Conversions": "Leads"}
    return f"{previous[stage]} → {stage}" if stage in previous else stage


# Data source: a validated user upload replaces the bundled sample for this session.
logo_svg = '''<svg class="brand-icon" viewBox="0 0 44 44" role="img" aria-label="Campaign Intelligence analytics logo">
<rect x="1" y="1" width="42" height="42" rx="12" fill="#2457A7"/>
<path d="M10 33V23h5v10m6 0V16h5v17m6 0V11h5v22" fill="#FFFFFF" opacity=".95"/>
<path d="m10 19 8-5 7 2 9-7" fill="none" stroke="#79D7B2" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
st.sidebar.markdown(
    f'<div class="brand-lockup">{logo_svg}<div class="brand-name">Campaign<br>Intelligence</div></div>'
    '',
    unsafe_allow_html=True,
)
st.sidebar.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader(
    "Upload campaign data",
    type=["csv", "xlsx", "xls"],
    help="Required columns: " + ", ".join([
        "Date", "Campaign_ID", "Campaign_Name", "Channel", "Impressions",
        "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue",
    ]),
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.lower().endswith((".xlsx", ".xls")):
            raw_data = pd.read_excel(uploaded_file)
        else:
            raw_data = pd.read_csv(uploaded_file)
        base_data = validate_data(raw_data)
        st.sidebar.success(f"Connected · {len(base_data):,} valid records")
    except Exception as exc:
        st.sidebar.error(f"Upload error: {exc}")
        base_data = load_sample_data()
        st.sidebar.info("The bundled sample data is active until the upload is corrected.")
else:
    base_data = load_sample_data()
    st.sidebar.success(f"Sample connected · {len(base_data):,} records")

st.sidebar.markdown("### Filters")
min_date, max_date = base_data["Date"].min().date(), base_data["Date"].max().date()
date_range = st.sidebar.date_input(
    "Campaign date range",
    value=(min_date, max_date), min_value=min_date, max_value=max_date,
)
selected_channels = st.sidebar.multiselect("Marketing channels", CHANNELS, default=CHANNELS)
filtered_data = filter_data(base_data, date_range, selected_channels)

pages = [
    "▦  Executive Overview", "◉  Channel Performance", "▽  Funnel Analysis", "⌁  Monthly Trends",
    "◈  Budget Optimization", "✦  Business Insights", "⇩  Reports & Downloads",
    "⇄  Campaign Comparison", "↔  Period-over-Period", "⇧  Campaign Rankings",
    "⚠  Performance Alerts", "◎  Marketing Goals & Targets",
]
page = st.sidebar.radio("WORKSPACE", pages)
st.sidebar.caption(f"Showing {len(filtered_data):,} of {len(base_data):,} campaign records")

kpis = summarize(filtered_data)
performance = channel_performance(filtered_data)
funnel, largest_drop_stage = funnel_metrics(filtered_data)
monthly = monthly_performance(filtered_data)
recommendations = generate_recommendations(performance, funnel, filtered_data)
insights = generate_insights(performance, funnel, filtered_data)
campaigns = campaign_performance(filtered_data)
period = (
    f"{filtered_data['Date'].min().date()} to {filtered_data['Date'].max().date()}"
    if not filtered_data.empty else "No records in selected range"
)

st.markdown(
    f'<div class="hero"><h1>{page.split("  ", 1)[-1]}</h1><p>{period}</p></div>',
    unsafe_allow_html=True,
)
if filtered_data.empty:
    st.warning("No campaigns match these filters. Expand the date range or select one or more channels.")

if page.endswith("Executive Overview"):
    show_kpis(kpis)
    left, right = st.columns([1.15, 1])
    with left:
        st.plotly_chart(revenue_spend_chart(performance), width="stretch", theme=None)
    with right:
        st.plotly_chart(channel_bar(performance, "ROI (%)", "ROI by channel · revenue-based"), width="stretch", theme=None)
    st.plotly_chart(channel_contribution_chart(performance), width="stretch", theme=None)
    st.subheader("Campaign performance")
    st.caption("Campaign-level totals within the selected date range and channels. Select a table header to sort.")
    st.dataframe(format_table(campaigns), width="stretch", hide_index=True, height=360)

elif page.endswith("Channel Performance"):
    st.markdown('<p class="section-intro">Compare channel scale, efficiency, and revenue return. '
                'Rates are recalculated from filtered aggregate totals.</p>', unsafe_allow_html=True)
    st.dataframe(format_table(performance), width="stretch", hide_index=True)
    chart_specs = [
        ("ROI (%)", "ROI comparison", False), ("ROAS", "ROAS comparison", False),
        ("CTR (%)", "CTR comparison", False), ("CPA", "CPA comparison", True),
        ("CPC", "CPC comparison", True), ("Revenue", "Revenue comparison", True),
    ]
    for start in range(0, len(chart_specs), 2):
        left, right = st.columns(2)
        for column, (metric, title, currency) in zip((left, right), chart_specs[start:start + 2]):
            with column:
                st.plotly_chart(channel_bar(performance, metric, title, currency), width="stretch", theme=None)

elif page.endswith("Funnel Analysis"):
    st.markdown('<p class="section-intro">Track volume and conversion through each campaign stage.</p>', unsafe_allow_html=True)
    left, right = st.columns([1.08, 1])
    with left:
        st.plotly_chart(funnel_chart(funnel), width="stretch", theme=None)
    with right:
        drop_row = funnel.loc[funnel["Stage"] == largest_drop_stage]
        if not drop_row.empty:
            drop_percent = drop_row.iloc[0]["Drop-off from prior (%)"]
            st.metric(
                "Biggest customer drop-off", transition_for(largest_drop_stage),
                delta=f"{drop_percent:.1f}% drop-off" if pd.notna(drop_percent) else None,
                delta_color="off",
            )
        else:
            st.metric("Biggest customer drop-off", "Not available")
        st.dataframe(
            funnel.style.format({
                "Volume": "{:,.0f}",
                "Conversion from prior (%)": "{:.1f}%",
                "Drop-off from prior (%)": "{:.1f}%",
            }, na_rep="—"),
            width="stretch", hide_index=True,
        )
    st.caption("Conversion = current stage ÷ prior stage. Drop-off = 100% − conversion. A zero prior-stage volume is shown as unavailable.")

elif page.endswith("Monthly Trends"):
    st.markdown('<p class="section-intro">Monthly performance by channel, based on the selected date range and channels.</p>', unsafe_allow_html=True)
    chart_specs = [
        ("Revenue", "Monthly revenue", True), ("Ad_Spend", "Monthly ad spend", True),
        ("ROI (%)", "Monthly revenue-based ROI", False), ("Conversions", "Monthly conversions", False),
    ]
    for start in range(0, len(chart_specs), 2):
        left, right = st.columns(2)
        for column, (metric, title, currency) in zip((left, right), chart_specs[start:start + 2]):
            with column:
                st.plotly_chart(monthly_chart(monthly, metric, title, currency), width="stretch", theme=None)

elif page.endswith("Budget Optimization"):
    st.markdown('<p class="section-intro">A transparent historical allocation scenario. Enter an available budget to see how the selected channel results distribute it.</p>', unsafe_allow_html=True)
    budget = st.number_input("Available marketing budget (INR)", min_value=0.0, value=500000.0, step=10000.0)
    allocation = budget_allocation(performance, budget)
    allocated_total = allocation["Proposed Budget"].sum()
    if allocated_total > 0:
        top = allocation.loc[allocation["Proposed Budget"].idxmax()]
        st.info(f"Largest proposed allocation: {top.Channel} · {format_inr(top['Proposed Budget'])} ({top['Allocation (%)']:.1f}%).")
    else:
        st.warning("No channel has positive observed ROI and recorded spend in this view. Review tracking and unit economics before assigning budget.")
    st.plotly_chart(budget_chart(allocation), width="stretch", theme=None)
    st.subheader("Channel allocation detail")
    st.caption("Compare each channel’s observed spend with the proposed share of the entered budget.")
    st.dataframe(format_table(allocation), width="stretch", hide_index=True)
    st.markdown(
        '<div class="method-note"><b>Allocation rule:</b> only channels with recorded spend and '
        'positive revenue-based ROI qualify. Each qualifying channel receives a weight of '
        '(ROI percentage + 100), normalized to the available budget; when multiple channels qualify, '
        'a 50% cap limits concentration. If only one qualifies, it receives the full budget. '
        'This is a historical scenario, not a forecast.</div>',
        unsafe_allow_html=True,
    )

elif page.endswith("Business Insights"):
    st.markdown('<p class="section-intro">Evidence-led findings recalculated from the filtered campaign records.</p>', unsafe_allow_html=True)
    for item in insights:
        priority = item["priority"].lower()
        st.markdown(
            f'<div class="insight-card"><span class="priority priority-{priority}">{item["priority"]} priority</span>'
            f'<h4>{item["finding"]}</h4><p class="insight-evidence">{item["evidence"]}</p>'
            f'<p><b>Business implication:</b> {item["implication"]}</p>'
            f'<p><b>Recommended action:</b> {item["action"]}</p></div>',
            unsafe_allow_html=True,
        )
    st.caption("Insights describe historical filtered data and do not guarantee future performance.")

elif page.endswith("Reports & Downloads"):
    st.markdown('<p class="section-intro">Export the same filtered records and metrics used across the dashboard.</p>', unsafe_allow_html=True)
    st.download_button(
        "Download filtered campaign data (CSV)",
        data=filtered_data.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8"),
        file_name="filtered_campaign_data.csv", mime="text/csv", disabled=filtered_data.empty,
    )
    st.download_button(
        "Download channel performance analysis (CSV)",
        data=performance.to_csv(index=False).encode("utf-8"),
        file_name="channel_performance.csv", mime="text/csv",
    )
    pdf_report = create_pdf_report(kpis, performance, funnel, transition_for(largest_drop_stage), recommendations, period)
    st.download_button(
        "Generate and download PDF analytics report", data=pdf_report,
        file_name="digital_marketing_analytics_report.pdf", mime="application/pdf",
    )
    st.subheader("Filtered KPI and channel preview")
    show_kpis(kpis)
    st.dataframe(format_table(performance), width="stretch", hide_index=True)
    st.subheader("Recommendations in this report")
    for item in recommendations:
        st.markdown(f"- {item}")
    st.caption("The PDF includes the ROI definition and its revenue-based limitation.")

elif page.endswith("Campaign Comparison"):
    st.markdown('<p class="section-intro">Compare campaign totals and efficiency measures for the current date and channel filters.</p>', unsafe_allow_html=True)
    comparison_data = campaign_metrics(filtered_data)
    if comparison_data.empty:
        st.info("No campaigns match the current filters.")
    else:
        available_campaigns = comparison_data["Campaign Key"].tolist()
        default_campaigns = available_campaigns[:2] if len(available_campaigns) >= 2 else available_campaigns
        selected_campaigns = st.multiselect(
            "Select two or more campaigns", available_campaigns, default=default_campaigns,
            help="Campaigns are identified by name and ID; all measures use filtered campaign totals.",
        )
        metric_labels = {
            "Impressions": "Impressions", "Clicks": "Clicks", "Leads": "Leads",
            "Conversions": "Conversions", "Ad_Spend": "Ad spend (INR)",
            "Revenue": "Revenue (INR)", "CTR (%)": "CTR (%)", "CPC": "CPC (INR)",
            "CPA": "CPA (INR)", "ROI (%)": "ROI (%)", "ROAS": "ROAS (x)",
        }
        chosen_metric_label = st.selectbox("Chart metric", list(metric_labels.values()))
        chosen_metric = next(key for key, label in metric_labels.items() if label == chosen_metric_label)
        selected = comparison_data[comparison_data["Campaign Key"].isin(selected_campaigns)]
        if len(selected) < 2:
            st.info("Select at least two campaigns to render a comparison.")
        else:
            st.plotly_chart(
                campaign_metric_chart(
                    selected, chosen_metric, f"Campaign comparison · {chosen_metric_label}",
                    currency=chosen_metric in {"Ad_Spend", "Revenue", "CPC", "CPA"},
                ), width="stretch", theme=None,
            )
            st.subheader("Detailed campaign comparison")
            st.dataframe(
                format_table(selected[["Campaign_ID", "Campaign_Name", "Channel", *CAMPAIGN_METRICS]]),
                width="stretch", hide_index=True,
            )

elif page.endswith("Period-over-Period"):
    st.markdown('<p class="section-intro">Compare the selected date range with the immediately preceding period of equal length, using the same channel filter.</p>', unsafe_allow_html=True)
    change = period_over_period(base_data, date_range, selected_channels)
    current_period, previous_period, start, end, previous_start, previous_end = period_frames(
        base_data, date_range, selected_channels
    )
    current_label = f"{start.date()} to {end.date()}" if start is not None else "Unavailable"
    previous_label = f"{previous_start.date()} to {previous_end.date()}" if previous_start is not None else "Unavailable"
    st.caption(f"Selected period: {current_label} · Previous equivalent period: {previous_label}")
    delta_specs = [
        ("Revenue change", "Revenue Change (%)", "percent", "normal"),
        ("Spend change", "Spend Change (%)", "percent", "inverse"),
        ("ROI change", "ROI Change (pp)", "points", "normal"),
        ("Conversion change", "Conversion Change (%)", "percent", "normal"),
        ("Lead change", "Lead Change (%)", "percent", "normal"),
    ]
    metric_columns = st.columns(5)
    for column, (label, key, style, direction) in zip(metric_columns, delta_specs):
        value = change[key]
        if pd.isna(value):
            formatted = "N/A"
        elif style == "points":
            formatted = f"{value:+.1f} pp"
        else:
            formatted = f"{value:+.1f}%"
        column.metric(label, formatted, delta_color=direction)
    if not len(previous_period):
        st.info("No records were found in the previous equivalent period. Changes are unavailable until a prior baseline exists.")
    elif not len(current_period):
        st.info("No records match the selected period. Changes are unavailable for this selection.")
    else:
        selected_period_metric = st.selectbox(
            "Compare period totals", ["Revenue", "Spend", "Conversions", "Leads", "ROI (%)"]
        )
        st.plotly_chart(period_comparison_chart(change, selected_period_metric), width="stretch", theme=None)
    detail_rows = []
    for label, current_key, previous_key, change_key in [
        ("Revenue", "Current Revenue", "Previous Revenue", "Revenue Change (%)"),
        ("Spend", "Current Spend", "Previous Spend", "Spend Change (%)"),
        ("ROI (%)", "Current ROI (%)", "Previous ROI (%)", "ROI Change (pp)"),
        ("Conversions", "Current Conversions", "Previous Conversions", "Conversion Change (%)"),
        ("Leads", "Current Leads", "Previous Leads", "Lead Change (%)"),
    ]:
        detail_rows.append({
            "Metric": label,
            "Previous period": change[previous_key],
            "Selected period": change[current_key],
            "Change": change[change_key],
        })
    st.dataframe(pd.DataFrame(detail_rows), width="stretch", hide_index=True)
    st.caption("Percent change = (selected − previous) ÷ previous. A zero or missing previous-period denominator is shown as unavailable. ROI change is in percentage points.")

elif page.endswith("Campaign Rankings"):
    st.markdown('<p class="section-intro">Rank campaigns using observed totals and rates from the current filters. Rates are recalculated from each campaign’s aggregated numerators and denominators.</p>', unsafe_allow_html=True)
    rank_filter_columns = st.columns([1.3, 1, 1])
    ranking_choice = rank_filter_columns[0].selectbox("Rank by", list(RANKING_METRICS))
    rank_channels = rank_filter_columns[1].multiselect(
        "Ranking channels", sorted(filtered_data.Channel.unique().tolist()),
        default=sorted(filtered_data.Channel.unique().tolist()),
    )
    max_rows = max(1, len(campaign_metrics(filter_data(filtered_data, channels=rank_channels))))
    top_n = rank_filter_columns[2].slider("Show campaigns", min_value=1, max_value=max_rows,
                                         value=min(10, max_rows))
    ranked = rank_campaigns(filter_data(filtered_data, channels=rank_channels), ranking_choice, top_n)
    if ranked.empty:
        st.info("No campaigns have a usable value for this ranking under the current filters.")
    else:
        metric, _ascending = RANKING_METRICS[ranking_choice]
        currency_metric = metric in {"Revenue", "CPA"}
        st.plotly_chart(ranking_chart(ranked, metric, ranking_choice, currency_metric), width="stretch", theme=None)
        st.subheader("Sortable campaign ranking")
        st.dataframe(format_table(ranked), width="stretch", hide_index=True)

elif page.endswith("Performance Alerts"):
    st.markdown('<p class="section-intro">Rule-based checks against filtered campaign results. Default CPA and spend thresholds come from the current campaign distribution and can be adjusted.</p>', unsafe_allow_html=True)
    current_period, previous_period, start, end, previous_start, previous_end = period_frames(
        base_data, date_range, selected_channels
    )
    defaults = default_alert_thresholds(current_period)
    alert_controls = st.columns(3)
    cpa_value = alert_controls[0].number_input(
        "High CPA threshold (INR)", min_value=0.0,
        value=float(defaults["High CPA threshold (INR)"] or 0), step=100.0,
        help="Default is the median positive, finite campaign CPA in the selected period. Set a threshold that fits your business rule.",
    )
    spend_value = alert_controls[1].number_input(
        "High spend threshold (INR)", min_value=0.0,
        value=float(defaults["High spend threshold (INR)"] or 0), step=1000.0,
        help="Default is the 75th percentile of positive campaign spend in the selected period.",
    )
    change_threshold = alert_controls[2].number_input(
        "Significant conversion change (%)", min_value=1.0, max_value=1000.0,
        value=20.0, step=5.0,
    )
    cpa_threshold = cpa_value if defaults["High CPA threshold (INR)"] is not None or cpa_value > 0 else None
    spend_threshold = spend_value if defaults["High spend threshold (INR)"] is not None or spend_value > 0 else None
    alerts = generate_performance_alerts(
        current_period, previous_period, cpa_threshold, spend_threshold, change_threshold
    )
    st.caption(
        "Alerts use current campaign totals. Revenue declines and significant conversion changes compare matching campaign IDs in the selected period and the immediately preceding equal-length period."
    )
    if alerts.empty:
        st.success("No alert rules were triggered for the current filtered records.")
    else:
        count_columns = st.columns(3)
        count_columns[0].metric("Active alerts", len(alerts))
        count_columns[1].metric("High severity", int(alerts["Severity"].eq("High").sum()))
        count_columns[2].metric("Medium severity", int(alerts["Severity"].eq("Medium").sum()))
        st.dataframe(alerts, width="stretch", hide_index=True)
    if not len(previous_period):
        st.info("No prior-period records are available; period-change alert rules are omitted. Current-period rules remain active.")

elif page.endswith("Marketing Goals & Targets"):
    st.markdown('<p class="section-intro">Set your own goals and compare them with actuals in the selected filters. Monthly revenue and conversion targets are prorated to the selected calendar days.</p>', unsafe_allow_html=True)
    target_top = st.columns(2)
    target_bottom = st.columns(2)
    monthly_revenue_target = target_top[0].number_input(
        "Monthly revenue target (INR)", min_value=0.0, value=0.0, step=10000.0,
        help="The target for each full calendar month in the selected range.",
    )
    monthly_conversion_target = target_top[1].number_input(
        "Monthly conversion target", min_value=0, value=0, step=10,
    )
    maximum_cpa = target_bottom[0].number_input(
        "Maximum CPA (INR)", min_value=0.0, value=0.0, step=100.0,
    )
    minimum_roi = target_bottom[1].number_input(
        "Minimum revenue-based ROI (%)", min_value=0.0, value=0.0, step=10.0,
    )
    goals = goal_attainment(
        filtered_data, date_range, monthly_revenue_target,
        monthly_conversion_target, maximum_cpa, minimum_roi,
    )
    st.caption("A target value of 0 is treated as unset. Revenue-based ROI is not profit-based ROI.")
    goal_columns = st.columns(4)
    for column, (_, row) in zip(goal_columns, goals.iterrows()):
        actual, target, progress = row["Actual"], row["Target"], row["Progress"]
        metric = row["Metric"]
        if pd.isna(actual):
            actual_text = "N/A"
        elif metric in {"Revenue", "CPA"}:
            actual_text = format_inr(actual, 2 if metric == "CPA" else 0)
        elif metric == "ROI (%)":
            actual_text = format_percent(actual, 1)
        else:
            actual_text = f"{actual:,.0f}"
        if pd.isna(target):
            target_text = "Target not set"
        elif metric in {"Revenue", "CPA"}:
            target_text = format_inr(target, 2 if metric == "CPA" else 0)
        elif metric == "ROI (%)":
            target_text = format_percent(target, 1)
        else:
            target_text = f"{target:,.0f}"
        column.metric(metric, actual_text, delta=row["Status"], delta_color=("normal" if row["Status"] == "Met" else "inverse"))
        column.caption(f"Target: {target_text}")
        if pd.notna(progress):
            column.progress(float(progress), text=f"{progress:.0%} of goal")
        else:
            column.caption("Set a positive target to display progress.")

    st.subheader("Actual versus target")
    st.dataframe(goals[["Metric", "Actual", "Target", "Status"]], width="stretch", hide_index=True)

st.caption(
    "Method note: ROI is revenue-based: (revenue − ad spend) ÷ ad spend. "
    "Product costs and profit are not included, so this is not profit-based ROI. "
    "All monetary amounts are shown in INR."
)
