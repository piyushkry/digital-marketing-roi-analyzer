"""Streamlit business intelligence dashboard for campaign ROI and funnel analysis."""
from pathlib import Path
from datetime import datetime
import html
import re
import sys
import uuid

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.data_processing import CHANNELS, filter_data, load_sample_data, validate_data
from modules.metrics import campaign_performance, channel_performance, funnel_metrics, monthly_performance, summarize
from modules.recommendations import budget_allocation, generate_insights, generate_recommendations
from modules.report_generator import create_pdf_report
from modules.visualizations import (
    budget_chart, channel_bar, channel_contribution_chart, funnel_chart,
    monthly_chart, revenue_spend_chart,
)


st.set_page_config(
    page_title="Campaign Intelligence | Marketing BI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "1.0.0"
PREFERENCE_DEFAULTS = {
    "currency": "INR",
    "inr_per_usd": 0.0,
    "number_format": "Indian",
    "number_decimals": 2,
    "theme": "Light",
    "show_kpi_cards": True,
    "show_chart_legends": True,
    "show_tables": True,
    "display_name": "Workspace user",
}
for preference, default in PREFERENCE_DEFAULTS.items():
    st.session_state.setdefault(f"pref_{preference}", default)
st.session_state.setdefault("utility_page", None)
st.session_state.setdefault("notifications", [])
st.session_state.setdefault("seen_notification_ids", [])


def add_notification(event_id, title, description, notification_type="info"):
    """Add one real event at most once in this session."""
    seen = st.session_state.seen_notification_ids
    if event_id in seen:
        return
    seen.append(event_id)
    st.session_state.notifications.insert(0, {
        "id": event_id,
        "title": title,
        "description": description,
        "type": notification_type,
        "timestamp": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "read": False,
    })


def mark_notification_read(event_id):
    for notification in st.session_state.notifications:
        if notification["id"] == event_id:
            notification["read"] = True
            break


def mark_all_notifications_read():
    for notification in st.session_state.notifications:
        notification["read"] = True


def clear_notifications():
    st.session_state.notifications.clear()


def notify_pdf_download():
    event_id = f"pdf-generated:{uuid.uuid4()}"
    add_notification(event_id, "PDF report generated", "The filtered analytics report was prepared for download.", "success")


def clear_utility_page():
    st.session_state.utility_page = None


def persist_setting(name):
    """Copy a transient settings widget value into persistent session preference state."""
    st.session_state[f"pref_{name}"] = st.session_state[f"settings_{name}"]


def persist_display_name():
    st.session_state.pref_display_name = st.session_state.profile_display_name_input.strip() or "Workspace user"

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
    .app-brand { display:flex; align-items:center; gap:.72rem; min-height:2.6rem; }
    .app-brand .brand-icon { width:40px; height:40px; }
    .app-brand-name { color:#142B4A; font-size:1.06rem; line-height:1.1; font-weight:760; letter-spacing:-.02em; }
    .app-brand-caption { color:#64748B; font-size:.76rem; margin-top:.22rem; }
    .header-divider { height:1px; background:#E5EAF2; margin:.45rem 0 1.2rem; }
    .page-note { color:#53657C; background:#EEF3F9; border:1px solid #E0E7F0;
      border-radius:10px; padding:.7rem .9rem; line-height:1.45; }
    .settings-section { color:#142B4A; font-size:1rem; font-weight:700; margin:.4rem 0 .15rem; }
    .profile-card { display:flex; align-items:center; gap:.8rem; margin:.25rem 0 1rem; }
    .profile-avatar { display:flex; align-items:center; justify-content:center; flex:none; width:52px; height:52px;
      border-radius:50%; background:#2457A7; color:#FFFFFF; font-size:1.1rem; font-weight:750; }
    .profile-name { color:#142B4A; font-weight:700; font-size:1.02rem; }
    .notification-unread { border-left:4px solid #3B82F6; padding-left:.65rem; }
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
    .st-key-top_nav_actions { gap:16px !important; justify-content:flex-end !important; align-items:center !important; }
    .st-key-notification_menu, .st-key-settings_shortcut, .st-key-profile_menu { position:relative; flex:0 0 fit-content !important; }
    .st-key-notification_menu [data-testid="stPopoverButton"], .st-key-settings_shortcut button {
      width:42px !important; min-width:42px !important; height:42px !important; padding:0 !important;
      background:#F1F5F9 !important; color:#334155 !important; border:0 !important;
      border-radius:50% !important; box-shadow:none !important; transition:background-color .16s ease,color .16s ease !important; }
    .st-key-notification_menu [data-testid="stPopoverButton"]:hover,
    .st-key-settings_shortcut button:hover { background:#E2E8F0 !important; color:#142B4A !important; }
    .st-key-notification_menu [data-testid="stPopoverButton"][aria-expanded="true"],
    .st-key-settings_shortcut button:active { background:#DBEAFE !important; }
    .st-key-profile_menu [data-testid="stPopoverButton"] {
      width:68px !important; min-width:68px !important; height:42px !important; padding:0 7px !important;
      background:#F1F5F9 !important; color:#2457A7 !important; border:0 !important;
      border-radius:999px !important; box-shadow:none !important; font-weight:750 !important;
      transition:background-color .16s ease !important; }
    .st-key-profile_menu [data-testid="stPopoverButton"]:hover { background:#E2E8F0 !important; }
    .st-key-profile_menu [data-testid="stPopoverButton"][aria-expanded="true"] { background:#DBEAFE !important; }
    .st-key-notification_menu [data-testid="stPopoverButton"] > div > div[aria-hidden="true"] { display:none !important; }
    .st-key-notification_menu [data-testid="stPopoverButton"] > div > div:first-child { margin:auto !important; }
    .st-key-profile_menu [data-testid="stPopoverButton"] > div > div:first-child > span { display:flex !important; align-items:center; }
    .st-key-profile_menu [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] {
      display:flex !important; align-items:center; justify-content:center; width:29px; height:29px;
      border-radius:50%; background:#2457A7 !important; color:#FFFFFF !important; overflow:hidden; }
    .st-key-profile_menu [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p {
      margin:0 !important; color:#FFFFFF !important; font-size:.72rem !important; line-height:1 !important; }
    .st-key-profile_menu [data-testid="stPopoverButton"] [data-testid="stIconMaterial"] { color:#334155 !important; }
    @media (max-width:800px) {
      .app-brand .brand-icon { width:32px; height:32px; }
      .app-brand-name { max-width:105px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.88rem; }
      .app-brand-caption { display:none; }
      .st-key-notification_menu [data-testid="stPopoverButton"], .st-key-settings_shortcut button { width:38px !important; min-width:38px !important; height:38px !important; }
      .st-key-profile_menu [data-testid="stPopoverButton"] { width:64px !important; min-width:64px !important; height:38px !important; }
      .st-key-profile_menu [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] { width:27px; height:27px; }
    }
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
    @media (max-width: 680px) {
      .app-brand-caption { display:none; }
      .app-brand-name { font-size:.92rem; }
      [data-testid="stMainBlockContainer"] { padding-left:1rem !important; padding-right:1rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.pref_theme == "Dark":
    st.markdown(
        """
        <style>
        :root { --ink:#E6EDF7; --muted:#AAB8CA; --line:#31435B; --canvas:#101A2A; }
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:#101A2A !important; color:#E6EDF7 !important; }
        [data-testid="stMainBlockContainer"] { color:#E6EDF7 !important; }
        .app-brand-name, .settings-section, .profile-name, h1, h2, h3, h4, p, label { color:#E6EDF7; }
        .app-brand-caption, .section-intro, .stCaption, [data-testid="stCaptionContainer"] { color:#AAB8CA !important; }
        .header-divider { background:#31435B; }
        div[data-testid="stMetric"], .insight-card, [data-testid="stDataFrame"],
        [data-testid="stTable"], [data-testid="stPopover"] { background:#172438 !important; border-color:#31435B !important; }
        div[data-testid="stMetric"] [data-testid="stMetricLabel"],
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] *,
        div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * { color:#B9C7D9 !important; -webkit-text-fill-color:#B9C7D9 !important; }
        div[data-testid="stMetricValue"], .insight-card h4, .insight-card p { color:#E6EDF7 !important; }
        .page-note, .method-note { color:#DAE5F3 !important; background:#1B2B42 !important; border-color:#344A67 !important; }
        [data-baseweb="input"] input, [data-baseweb="select"] > div, [data-baseweb="textarea"] textarea,
        [data-testid="stNumberInput"] input { background:#172438 !important; color:#E6EDF7 !important; }
        [data-testid="stPopoverButton"] { color:#334155 !important; }
        .st-key-notification_menu [data-testid="stPopoverButton"], .st-key-settings_shortcut button,
        .st-key-profile_menu [data-testid="stPopoverButton"] { background:#F1F5F9 !important; color:#334155 !important; }
        .st-key-profile_menu [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p { color:#FFFFFF !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
def format_number(value, decimals=None):
    """Apply the chosen visual number style; underlying metrics remain unchanged."""
    if value is None or pd.isna(value):
        return "N/A"
    decimals = st.session_state.pref_number_decimals if decimals is None else decimals
    value = float(value)
    absolute = abs(value)
    number = f"{absolute:.{decimals}f}"
    whole, dot, fraction = number.partition(".")
    if st.session_state.pref_number_format == "Indian" and len(whole) > 3:
        last_three, prefix = whole[-3:], whole[:-3]
        pairs = []
        while prefix:
            pairs.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        whole = ",".join(pairs + [last_three])
    elif st.session_state.pref_number_format == "International":
        whole = f"{int(whole):,}"
    return f"{'-' if value < 0 else ''}{whole}{dot}{fraction if dot else ''}"


def format_inr(value, decimals=None):
    """Format an INR source amount according to display preferences."""
    if value is None or pd.isna(value):
        return "N/A"
    value = float(value)
    symbol = "₹"
    if st.session_state.pref_currency == "USD":
        rate = float(st.session_state.pref_inr_per_usd or 0)
        if rate <= 0:
            return "Set USD rate"
        value /= rate
        symbol = "$"
    return f"{'-' if value < 0 else ''}{symbol}{format_number(abs(value), decimals)}"


def display_currency_text(text):
    """Convert existing narrative INR labels for dashboard display only."""
    rate = float(st.session_state.pref_inr_per_usd or 0)
    if st.session_state.pref_currency != "USD" or rate <= 0:
        return text

    def convert(match):
        amount = float(match.group(1).replace(",", "")) / rate
        sign = "-" if amount < 0 else ""
        return f"{sign}${format_number(abs(amount))}"

    return re.sub(r"₹\s*(-?[\d,]+(?:\.\d+)?)", convert, str(text))


def format_percent(value, decimals=None):
    if value is None or pd.isna(value):
        return "N/A"
    decimals = st.session_state.pref_number_decimals if decimals is None else decimals
    return f"{format_number(value, decimals)}%"


def show_kpis(kpis):
    if not st.session_state.pref_show_kpi_cards:
        return
    cards = [
        ("Revenue", format_inr(kpis["Revenue"]), "Observed revenue in the filtered period."),
        ("Marketing Spend", format_inr(kpis["Ad_Spend"]), "Observed campaign ad spend in INR."),
        ("ROI", format_percent(kpis["ROI"]), "Revenue-based ROI; it is not profit-based ROI."),
        ("ROAS", "N/A" if pd.isna(kpis["ROAS"]) else f"{format_number(kpis['ROAS'])}x", "Revenue divided by ad spend."),
        ("Impressions", format_number(kpis["Impressions"], 0), "Campaign impressions in the filtered period."),
        ("Clicks", format_number(kpis["Clicks"], 0), "Campaign clicks in the filtered period."),
        ("Leads", format_number(kpis["Leads"], 0), "Leads recorded in the filtered period."),
        ("Conversions", format_number(kpis["Conversions"], 0), "Conversions recorded in the filtered period."),
    ]
    for start in range(0, len(cards), 4):
        row = cards[start : start + 4]
        columns = st.columns(4)
        for column, (label, value, help_text) in zip(columns, row):
            column.metric(label, value, help=help_text)


def format_table(frame):
    formats = {}
    currency_columns = ["Ad_Spend", "Revenue", "CPC", "CPL", "CPA", "Proposed Budget"]
    percent_columns = [
        "CTR (%)", "Conversion Rate (%)", "ROI (%)", "Allocation (%)",
        "Current Allocation (%)", "Conversion from prior (%)", "Drop-off from prior (%)",
    ]
    count_columns = ["Impressions", "Clicks", "Leads", "Conversions", "Volume"]
    for column in currency_columns:
        if column in frame.columns:
            formats[column] = lambda value: format_inr(value)
    for column in percent_columns:
        if column in frame.columns:
            formats[column] = lambda value: format_percent(value)
    for column in count_columns:
        if column in frame.columns:
            formats[column] = lambda value: format_number(value, 0)
    if "ROAS" in frame.columns:
        formats["ROAS"] = lambda value: "N/A" if pd.isna(value) else f"{format_number(value)}x"
    return frame.style.format(formats, na_rep="—")


def show_chart(fig, currency=False):
    """Apply visual theme and optional currency conversion to a display copy."""
    dark = st.session_state.pref_theme == "Dark"
    paper, ink, grid = ("#172438", "#E6EDF7", "#31435B") if dark else ("#FFFFFF", "#142B4A", "#E5EAF2")
    converted = currency and st.session_state.pref_currency == "USD"
    rate = float(st.session_state.pref_inr_per_usd or 0)
    if converted and rate > 0:
        for trace in fig.data:
            if getattr(trace, "y", None) is not None:
                trace.y = [None if value is None else value / rate for value in trace.y]
            if getattr(trace, "values", None) is not None:
                trace.values = [None if value is None else value / rate for value in trace.values]
            if getattr(trace, "hovertemplate", None):
                trace.hovertemplate = trace.hovertemplate.replace("₹", "$")
        if fig.layout.annotations:
            total = sum(
                float(value)
                for trace in fig.data
                if getattr(trace, "values", None) is not None
                for value in trace.values
                if value is not None
            )
            for annotation in fig.layout.annotations:
                if annotation.text and "₹" in annotation.text:
                    annotation.text = f"Revenue<br><b>${total:,.0f}</b>"
    elif converted:
        converted = False
    if currency:
        fig.update_yaxes(tickprefix="$" if converted else "₹")
        fig.update_yaxes(title_text="USD ($)" if converted else "INR (₹)")
    fig.update_layout(
        paper_bgcolor=paper, plot_bgcolor=paper, font={"color": ink},
        title_font_color=ink, legend_font_color=ink,
        showlegend=st.session_state.pref_show_chart_legends,
        hoverlabel={"bgcolor": "#10213D", "font": {"color": "#FFFFFF"}},
    )
    fig.update_xaxes(color=ink, gridcolor=grid, linecolor=grid)
    fig.update_yaxes(color=ink, gridcolor=grid, linecolor=grid)
    st.plotly_chart(fig, width="stretch", theme=None)


def show_table(frame, **kwargs):
    if st.session_state.pref_show_tables:
        st.dataframe(frame, **kwargs)


def transition_for(stage):
    previous = {"Clicks": "Impressions", "Leads": "Clicks", "Conversions": "Leads"}
    return f"{previous[stage]} → {stage}" if stage in previous else stage


def open_utility_page(label):
    st.session_state.utility_page = label


def return_to_workspace():
    st.session_state.utility_page = None


def show_settings_page():
    st.markdown(
        "<p class='section-intro'>Display preferences are saved for this browser session. "
        "Source data and calculations remain in INR.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='settings-section'>Regional display</div>", unsafe_allow_html=True)
    setting_names = [
        "currency", "inr_per_usd", "number_format", "number_decimals", "theme",
        "show_kpi_cards", "show_chart_legends", "show_tables",
    ]
    for name in setting_names:
        st.session_state.setdefault(f"settings_{name}", st.session_state[f"pref_{name}"])
    left, right = st.columns(2)
    with left:
        st.selectbox("Currency preference", ["INR", "USD"], key="settings_currency",
                     on_change=persist_setting, args=("currency",))
        if st.session_state.pref_currency == "USD":
            st.number_input(
                "INR per 1 USD · display only", min_value=0.0, step=0.1,
                key="settings_inr_per_usd", on_change=persist_setting, args=("inr_per_usd",),
                help="Enter the exchange rate you want used for display. No rate is fetched or assumed.",
            )
            if st.session_state.pref_inr_per_usd <= 0:
                st.info("Enter an exchange rate to display converted USD values. Until then, monetary values remain in INR.")
        st.selectbox("Number format", ["Indian", "International"], key="settings_number_format",
                     on_change=persist_setting, args=("number_format",))
    with right:
        st.selectbox("Decimal places", [0, 1, 2], key="settings_number_decimals",
                     on_change=persist_setting, args=("number_decimals",))
        st.selectbox("Appearance", ["Light", "Dark"], key="settings_theme",
                     on_change=persist_setting, args=("theme",))
    st.markdown("<div class='settings-section'>Dashboard display</div>", unsafe_allow_html=True)
    st.toggle("Show KPI cards", key="settings_show_kpi_cards", on_change=persist_setting, args=("show_kpi_cards",))
    st.toggle("Show chart legends", key="settings_show_chart_legends", on_change=persist_setting, args=("show_chart_legends",))
    st.toggle("Show data tables", key="settings_show_tables", on_change=persist_setting, args=("show_tables",))
    st.caption(
        "These settings affect dashboard presentation only. Downloads and PDF reports retain source INR values."
    )


def show_about_page():
    st.markdown("<div class='settings-section'>About Campaign Intelligence</div>", unsafe_allow_html=True)
    st.write(
        "Campaign Intelligence is a marketing analytics dashboard for reviewing campaign efficiency, channel "
        "performance, funnel movement, monthly results, and budget scenarios."
    )
    st.write(
        "**Project purpose:** help academic and business users explore campaign performance from uploaded or bundled data."
    )
    st.write("**Technology stack:** Python, Streamlit, Pandas, NumPy, and Plotly.")
    st.write(f"**Application version:** {APP_VERSION}")


def show_help_page():
    st.markdown("<div class='settings-section'>Help & Support</div>", unsafe_allow_html=True)
    st.write("**Upload campaign data:** use the sidebar uploader to select a CSV or Excel file with the required campaign columns. A validation message appears if the file cannot be used.")
    st.write("**Apply filters:** set the campaign date range and select one or more marketing channels in the sidebar. Dashboard views use those active filters.")
    st.write("**Interpret KPIs:** CTR is clicks ÷ impressions; CPC, CPL and CPA divide spend by clicks, leads and conversions; conversion rate is conversions ÷ clicks; ROI is revenue-based, not profit-based; ROAS is revenue ÷ spend.")
    st.write("**Download reports:** open Reports & Downloads from the workspace navigation to download filtered CSV files or generate a PDF report.")


def profile_initials(display_name):
    parts = display_name.strip().split()
    if not parts:
        return "WU"
    return "".join(part[0] for part in parts[:2]).upper()


def show_profile_page():
    display_name = st.session_state.pref_display_name.strip() or "Workspace user"
    initials = profile_initials(display_name)
    safe_name = html.escape(display_name)
    st.markdown(
        f"<div class='profile-card'><div class='profile-avatar'>{initials}</div>"
        f"<div><div class='profile-name'>{safe_name}</div><div>Local workspace user</div></div></div>",
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("profile_display_name_input", st.session_state.pref_display_name)
    st.text_input("Display name", key="profile_display_name_input", max_chars=60, on_change=persist_display_name)
    st.caption("This local display name is stored only in this Streamlit session. No account, sign-in, or logout is provided.")


def queue_analytics_notifications(performance, monthly, selected_channels, period):
    """Queue only current, observable issues from the filtered records."""
    scope = f"{period}|{','.join(sorted(selected_channels))}"
    for _, row in performance.iterrows():
        roi = row.get("ROI (%)")
        if pd.notna(roi) and roi < 0:
            add_notification(
                f"negative-roi:{scope}:{row['Channel']}",
                f"Negative ROI · {row['Channel']}",
                f"Revenue-based ROI is {format_percent(roi)} for {row['Channel']} in the current filtered view.",
                "error",
            )

    valid_cpa = performance.loc[performance["CPA"].notna() & performance["CPA"].gt(0), ["Channel", "CPA"]]
    if len(valid_cpa) > 1:
        median_cpa = float(valid_cpa["CPA"].median())
        for _, row in valid_cpa.loc[valid_cpa["CPA"] > median_cpa].iterrows():
            add_notification(
                f"high-cpa:{scope}:{row['Channel']}",
                f"High CPA · {row['Channel']}",
                f"CPA is {format_inr(row['CPA'])}, above the selected-channel median of {format_inr(median_cpa)}.",
                "warning",
            )

    if not monthly.empty:
        monthly_totals = monthly.groupby("Month", as_index=True)["Revenue"].sum().sort_index()
        if len(monthly_totals) >= 2:
            previous_month, current_month = monthly_totals.index[-2], monthly_totals.index[-1]
            previous_revenue, current_revenue = float(monthly_totals.iloc[-2]), float(monthly_totals.iloc[-1])
            if previous_revenue > 0 and current_revenue < previous_revenue:
                change = (current_revenue - previous_revenue) / previous_revenue * 100
                add_notification(
                    f"revenue-decline:{scope}:{previous_month.date()}:{current_month.date()}",
                    "Revenue decline detected",
                    f"Filtered revenue declined {abs(change):.1f}% from {previous_month:%b %Y} "
                    f"({format_inr(previous_revenue)}) to {current_month:%b %Y} ({format_inr(current_revenue)}).",
                    "warning",
                )


# Data source: a validated user upload replaces the bundled sample for this session.
uploaded_file = st.sidebar.file_uploader(
    "Upload campaign data",
    type=["csv", "xlsx", "xls"],
    help="Required columns: " + ", ".join([
        "Date", "Campaign_ID", "Campaign_Name", "Channel", "Impressions",
        "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue",
    ]),
)

if uploaded_file is not None:
    upload_event_key = getattr(uploaded_file, "file_id", None) or f"{uploaded_file.name}:{uploaded_file.size}"
    try:
        if uploaded_file.name.lower().endswith((".xlsx", ".xls")):
            raw_data = pd.read_excel(uploaded_file)
        else:
            raw_data = pd.read_csv(uploaded_file)
        base_data = validate_data(raw_data)
        connection_message = f"Uploaded data connected · {len(base_data):,} valid records"
        upload_error = None
        add_notification(
            f"upload-success:{upload_event_key}",
            "Dataset uploaded successfully",
            f"{uploaded_file.name} passed validation with {len(base_data):,} campaign records.",
            "success",
        )
        st.sidebar.success(f"Connected · {len(base_data):,} valid records")
    except Exception as exc:
        upload_error = str(exc)
        connection_message = "The upload could not be used; sample data is active."
        add_notification(
            f"upload-failed:{upload_event_key}:{upload_error}",
            "Dataset validation failed",
            f"{uploaded_file.name} could not be loaded: {upload_error}",
            "error",
        )
        st.sidebar.error(f"Upload error: {exc}")
        base_data = load_sample_data()
        st.sidebar.info("The bundled sample data is active until the upload is corrected.")
else:
    base_data = load_sample_data()
    connection_message = f"Sample data connected · {len(base_data):,} records"
    upload_error = None
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
]
selected_page = st.sidebar.radio("WORKSPACE", pages, key="workspace_page", on_change=clear_utility_page)
previous_workspace_page = st.session_state.get("last_workspace_page")
if previous_workspace_page is not None and previous_workspace_page != selected_page:
    st.session_state.utility_page = None
st.session_state.last_workspace_page = selected_page
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
queue_analytics_notifications(performance, monthly, selected_channels, period)

logo_svg = '''<svg class="brand-icon" viewBox="0 0 44 44" role="img" aria-label="Campaign Intelligence analytics logo">
<rect x="1" y="1" width="42" height="42" rx="12" fill="#2457A7"/>
<path d="M10 33V23h5v10m6 0V16h5v17m6 0V11h5v22" fill="#FFFFFF" opacity=".95"/>
<path d="m10 19 8-5 7 2 9-7" fill="none" stroke="#79D7B2" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''

brand_col, actions_col = st.columns([7, 3], vertical_alignment="center")
with brand_col:
    st.markdown(
        f'<div class="app-brand">{logo_svg}<div><div class="app-brand-name">Campaign Intelligence</div>'
        '<div class="app-brand-caption">Marketing performance workspace</div></div></div>',
        unsafe_allow_html=True,
    )
unread_count = sum(not item["read"] for item in st.session_state.notifications)
if unread_count:
    st.markdown(
        f"<style>.st-key-notification_menu::after{{content:'{unread_count}';position:absolute;right:-2px;top:-3px;"
        "min-width:16px;height:16px;padding:0 3px;border-radius:999px;background:#EF4444;color:#FFFFFF;"
        "font:700 10px/16px Inter,Arial,sans-serif;text-align:center;z-index:3;}}</style>",
        unsafe_allow_html=True,
    )
with actions_col:
    with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="right", gap="small", key="top_nav_actions"):
        notification_label = " "
        with st.popover(notification_label, icon=":material/notifications:", help="Notifications", key="notification_menu", width="content"):
            st.markdown("**Notifications**")
            st.caption(connection_message)
            if upload_error:
                st.error(f"Upload issue: {upload_error}")
            if unread_count:
                st.button("Mark all as read", key="mark_all_notifications_read", on_click=mark_all_notifications_read, use_container_width=True)
            if st.session_state.notifications:
                for notification in st.session_state.notifications:
                    with st.container(border=True):
                        st.markdown(f"**{notification['title']}**")
                        status = "Unread" if not notification["read"] else "Read"
                        st.caption(f"{notification['type'].title()} · {status} · {notification['timestamp']}")
                        st.write(notification["description"])
                        if not notification["read"]:
                            st.button(
                                "Mark as read", key=f"mark_notification_{notification['id']}",
                                on_click=mark_notification_read, args=(notification["id"],),
                            )
                st.button("Clear notifications", key="clear_notifications", on_click=clear_notifications, use_container_width=True)
            else:
                st.info("No notifications yet.")
        if st.button(" ", icon=":material/settings:", key="settings_shortcut", help="Open display settings", type="tertiary"):
            open_utility_page("Settings")
        profile_label = profile_initials(st.session_state.pref_display_name)
        with st.popover(profile_label, help="Profile and application menu", key="profile_menu", width="content"):
            st.markdown(f"**{html.escape(st.session_state.pref_display_name.strip() or 'Workspace user')}**")
            st.caption("Local workspace · no account sign-in")
            st.button("My Profile", key="menu_my_profile", on_click=open_utility_page, args=("My Profile",), use_container_width=True)
            st.button("About Campaign Intelligence", key="menu_about", on_click=open_utility_page, args=("About Campaign Intelligence",), use_container_width=True)
            st.button("Help & Support", key="menu_help_support", on_click=open_utility_page, args=("Help & Support",), use_container_width=True)
if st.session_state.utility_page is None:
    page = selected_page
else:
    page = st.session_state.utility_page
st.markdown('<div class="header-divider"></div>', unsafe_allow_html=True)
if st.session_state.pref_currency == "USD" and st.session_state.pref_inr_per_usd <= 0:
    st.info("USD display is selected. Enter an INR-per-USD rate in Settings to convert monetary values; until then they remain in INR.")

if page == "Settings":
    period = "Display preferences"
elif page == "About Campaign Intelligence":
    period = "Application information"
elif page == "Help & Support":
    period = "Usage instructions"
elif page == "My Profile":
    period = "Local-only workspace profile"

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
        show_chart(revenue_spend_chart(performance), currency=True)
    with right:
        show_chart(channel_bar(performance, "ROI (%)", "ROI by channel · revenue-based"))
    show_chart(channel_contribution_chart(performance), currency=True)
    if st.session_state.pref_show_tables:
        st.subheader("Campaign performance")
        st.caption("Campaign-level totals within the selected date range and channels. Select a table header to sort.")
        show_table(format_table(campaigns), width="stretch", hide_index=True, height=360)

elif page.endswith("Channel Performance"):
    st.markdown('<p class="section-intro">Compare channel scale, efficiency, and revenue return. '
                'Rates are recalculated from filtered aggregate totals.</p>', unsafe_allow_html=True)
    show_table(format_table(performance), width="stretch", hide_index=True)
    chart_specs = [
        ("ROI (%)", "ROI comparison", False), ("ROAS", "ROAS comparison", False),
        ("CTR (%)", "CTR comparison", False), ("CPA", "CPA comparison", True),
        ("CPC", "CPC comparison", True), ("Revenue", "Revenue comparison", True),
    ]
    for start in range(0, len(chart_specs), 2):
        left, right = st.columns(2)
        for column, (metric, title, currency) in zip((left, right), chart_specs[start:start + 2]):
            with column:
                show_chart(channel_bar(performance, metric, title, currency), currency=currency)

elif page.endswith("Funnel Analysis"):
    st.markdown('<p class="section-intro">Track volume and conversion through each campaign stage.</p>', unsafe_allow_html=True)
    left, right = st.columns([1.08, 1])
    with left:
        show_chart(funnel_chart(funnel))
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
        show_table(format_table(funnel), width="stretch", hide_index=True)
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
                show_chart(monthly_chart(monthly, metric, title, currency), currency=currency)

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
    show_chart(budget_chart(allocation), currency=True)
    if st.session_state.pref_show_tables:
        st.subheader("Channel allocation detail")
        st.caption("Compare each channel’s observed spend with the proposed share of the entered budget.")
        show_table(format_table(allocation), width="stretch", hide_index=True)
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
            f'<h4>{item["finding"]}</h4><p class="insight-evidence">{display_currency_text(item["evidence"])}</p>'
            f'<p><b>Business implication:</b> {display_currency_text(item["implication"])}</p>'
            f'<p><b>Recommended action:</b> {display_currency_text(item["action"])}</p></div>',
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
        on_click=notify_pdf_download,
    )
    st.subheader("Filtered KPI and channel preview")
    show_kpis(kpis)
    show_table(format_table(performance), width="stretch", hide_index=True)
    st.subheader("Recommendations in this report")
    for item in recommendations:
        st.markdown(f"- {display_currency_text(item)}")
    st.caption("The PDF includes the ROI definition and its revenue-based limitation.")

elif page == "Settings":
    show_settings_page()
    st.button("Return to workspace", key="return_from_settings", type="secondary", on_click=return_to_workspace)

elif page == "About Campaign Intelligence":
    show_about_page()
    st.button("Return to workspace", key="return_from_about", type="secondary", on_click=return_to_workspace)

elif page == "Help & Support":
    show_help_page()
    st.button("Return to workspace", key="return_from_help_support", type="secondary", on_click=return_to_workspace)

elif page == "My Profile":
    show_profile_page()
    st.button("Return to workspace", key="return_from_profile", type="secondary", on_click=return_to_workspace)

if page in pages:
    monetary_note = "All calculations and report exports remain in INR."
    if st.session_state.pref_currency == "USD":
        monetary_note = "Dashboard currency is display-only; calculations and report exports remain in INR."
    st.caption(
        "Method note: ROI is revenue-based: (revenue − ad spend) ÷ ad spend. "
        "Product costs and profit are not included, so this is not profit-based ROI. "
        + monetary_note
    )


