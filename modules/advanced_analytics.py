"""Additional campaign comparisons, alerts, and target calculations.

All functions use observed campaign records. Threshold defaults are derived
from the supplied filtered population; no forecasts or fabricated results are
produced here.
"""
import calendar

import numpy as np
import pandas as pd

from .data_processing import filter_data
from .metrics import campaign_performance, safe_divide, summarize


CAMPAIGN_METRICS = [
    "Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue",
    "CTR (%)", "CPC", "CPA", "ROI (%)", "ROAS",
]
RANKING_METRICS = {
    "Highest ROI": ("ROI (%)", False),
    "Highest revenue": ("Revenue", False),
    "Lowest CPA": ("CPA", True),
    "Highest conversion rate": ("Conversion Rate (%)", False),
    "Highest conversions": ("Conversions", False),
}
ALERT_COLUMNS = ["Severity", "Alert", "Campaign", "Evidence", "Recommended action"]


def campaign_metrics(frame):
    """Return campaign totals with efficiency measures recomputed from totals."""
    result = campaign_performance(frame)
    if result.empty:
        for col in ["CTR (%)", "CPC", "CPA", "Conversion Rate (%)", "Campaign Key"]:
            result[col] = pd.Series(dtype="object" if col == "Campaign Key" else "float64")
        return result
    result["CTR (%)"] = result.apply(lambda r: safe_divide(r.Clicks, r.Impressions, 100), axis=1)
    result["CPC"] = result.apply(lambda r: safe_divide(r.Ad_Spend, r.Clicks), axis=1)
    result["CPA"] = result.apply(lambda r: safe_divide(r.Ad_Spend, r.Conversions), axis=1)
    result["Conversion Rate (%)"] = result.apply(
        lambda r: safe_divide(r.Conversions, r.Clicks, 100), axis=1
    )
    result["Campaign Key"] = result.apply(
        lambda r: f"{r.Campaign_Name} · {r.Campaign_ID}", axis=1
    )
    return result


def _resolve_range(frame, date_range):
    if date_range is not None:
        start, end = pd.Timestamp(date_range[0]).normalize(), pd.Timestamp(date_range[-1]).normalize()
        return (end, start) if end < start else (start, end)
    if frame.empty:
        return None, None
    return frame["Date"].min().normalize(), frame["Date"].max().normalize()


def period_frames(frame, date_range=None, channels=None):
    """Return current and immediately preceding equal-length date windows."""
    start, end = _resolve_range(frame, date_range)
    if start is None:
        empty = frame.iloc[0:0].copy()
        return empty, empty.copy(), None, None, None, None
    days = (end - start).days + 1
    previous_end = start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=days - 1)
    current = filter_data(frame, (start, end), channels)
    previous = filter_data(frame, (previous_start, previous_end), channels)
    return current, previous, start, end, previous_start, previous_end


def _percent_change(current, previous):
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return np.nan
    return (current - previous) / abs(previous) * 100


def period_over_period(frame, date_range=None, channels=None):
    """Summarize two equal-length periods; unavailable baselines remain NaN."""
    current, previous, start, end, prior_start, prior_end = period_frames(
        frame, date_range, channels
    )
    result = {
        "Current Start": start,
        "Current End": end,
        "Previous Start": prior_start,
        "Previous End": prior_end,
        "Current Records": len(current),
        "Previous Records": len(previous),
    }
    metrics = {
        "Revenue": ("Revenue", "Revenue Change (%)"),
        "Spend": ("Ad_Spend", "Spend Change (%)"),
        "Conversions": ("Conversions", "Conversion Change (%)"),
        "Leads": ("Leads", "Lead Change (%)"),
    }
    curr_summary, prev_summary = summarize(current), summarize(previous)
    for label, (source, change_name) in metrics.items():
        curr_value = curr_summary[source] if len(current) else np.nan
        prev_value = prev_summary[source] if len(previous) else np.nan
        result[f"Current {label}"] = curr_value
        result[f"Previous {label}"] = prev_value
        result[change_name] = _percent_change(curr_value, prev_value)
    curr_roi = curr_summary["ROI"] if len(current) else np.nan
    prev_roi = prev_summary["ROI"] if len(previous) else np.nan
    result["Current ROI (%)"] = curr_roi
    result["Previous ROI (%)"] = prev_roi
    result["ROI Change (pp)"] = (
        curr_roi - prev_roi if pd.notna(curr_roi) and pd.notna(prev_roi) else np.nan
    )
    return result


def rank_campaigns(frame, ranking="Highest ROI", limit=None):
    """Rank observed campaigns for a supported metric; missing rates are omitted."""
    if ranking not in RANKING_METRICS:
        raise ValueError(f"Unsupported ranking: {ranking}")
    column, ascending = RANKING_METRICS[ranking]
    result = campaign_metrics(frame)
    if result.empty:
        result["Rank"] = pd.Series(dtype="int64")
        return result
    result = result[result[column].notna()].sort_values(
        [column, "Campaign_Name"], ascending=[ascending, True], kind="stable"
    ).reset_index(drop=True)
    result.insert(0, "Rank", np.arange(1, len(result) + 1))
    return result.head(limit).reset_index(drop=True) if limit is not None else result


def default_alert_thresholds(frame):
    """Use the filtered campaigns' median finite CPA and 75th-percentile spend."""
    campaigns = campaign_metrics(frame)
    cpa_values = campaigns.loc[campaigns["CPA"].gt(0), "CPA"].replace([np.inf, -np.inf], np.nan).dropna()
    spend_values = campaigns.loc[campaigns["Ad_Spend"].gt(0), "Ad_Spend"]
    return {
        "High CPA threshold (INR)": float(cpa_values.median()) if not cpa_values.empty else None,
        "High spend threshold (INR)": float(spend_values.quantile(.75)) if not spend_values.empty else None,
    }


def generate_performance_alerts(
    current_frame,
    previous_frame=None,
    cpa_threshold=None,
    spend_threshold=None,
    significant_change_pct=20.0,
):
    """Create rules-based alerts from current and, when supplied, prior records."""
    alerts = []
    current = campaign_metrics(current_frame)
    if current.empty:
        return pd.DataFrame(columns=ALERT_COLUMNS)

    def add(severity, alert, row, evidence, action):
        alerts.append({
            "Severity": severity,
            "Alert": alert,
            "Campaign": f"{row.Campaign_Name} · {row.Campaign_ID}",
            "Evidence": evidence,
            "Recommended action": action,
        })

    for _, row in current.iterrows():
        if pd.notna(row["ROI (%)"]) and row["ROI (%)"] < 0:
            add("High", "Negative ROI", row,
                f"Revenue-based ROI {row['ROI (%)']:.1f}% · spend ₹{row.Ad_Spend:,.0f} · revenue ₹{row.Revenue:,.0f}",
                "Review attribution, campaign setup, and spend before continuing investment.")
        if cpa_threshold is not None and pd.notna(row.CPA) and row.CPA > cpa_threshold:
            add("Medium", "High CPA", row,
                f"CPA ₹{row.CPA:,.2f} exceeds the ₹{cpa_threshold:,.2f} threshold.",
                "Inspect targeting and conversion quality; compare with the campaign's prior period.")
        if (spend_threshold is not None and row.Ad_Spend > 0
                and row.Ad_Spend >= spend_threshold and row.Conversions == 0):
            add("High", "High spend without conversions", row,
                f"Spend ₹{row.Ad_Spend:,.2f} is at or above ₹{spend_threshold:,.2f}; conversions: 0.",
                "Check tracking and pause or review the campaign until conversion measurement is verified.")

    previous_frame = previous_frame if previous_frame is not None else current_frame.iloc[0:0]
    previous = campaign_metrics(previous_frame)
    if not previous.empty:
        keys = ["Campaign_ID", "Campaign_Name", "Channel"]
        fields = ["Revenue", "Conversions"]
        comparison = current[keys + fields].merge(
            previous[keys + fields], on=keys, how="outer", suffixes=(" Current", " Previous")
        )
        for _, pair in comparison.iterrows():
            current_values = pair[[f"{field} Current" for field in fields]]
            if current_values.isna().all():
                continue
            curr_revenue = pair.get("Revenue Current", 0)
            prev_revenue = pair.get("Revenue Previous", 0)
            curr_conversions = pair.get("Conversions Current", 0)
            prev_conversions = pair.get("Conversions Previous", 0)
            identity = current[(current.Campaign_ID == pair.Campaign_ID)
                               & (current.Campaign_Name == pair.Campaign_Name)
                               & (current.Channel == pair.Channel)]
            if identity.empty:
                identity = previous[(previous.Campaign_ID == pair.Campaign_ID)
                                    & (previous.Campaign_Name == pair.Campaign_Name)
                                    & (previous.Channel == pair.Channel)]
            row = next(identity.itertuples(index=False))
            revenue_change = _percent_change(curr_revenue, prev_revenue)
            if pd.notna(revenue_change) and revenue_change < 0:
                severity = "High" if revenue_change <= -abs(significant_change_pct) else "Medium"
                add(severity, "Revenue decline", row,
                    f"Revenue changed {revenue_change:+.1f}% (₹{curr_revenue:,.2f} vs ₹{prev_revenue:,.2f}).",
                    "Review delivery, spend, attribution, and conversion tracking against the prior period.")
            conversion_change = _percent_change(curr_conversions, prev_conversions)
            if (pd.notna(conversion_change)
                    and abs(conversion_change) >= abs(significant_change_pct)):
                add("High" if conversion_change < 0 else "Medium", "Significant campaign change", row,
                    f"Conversions changed {conversion_change:+.1f}% ({curr_conversions:,.0f} vs {prev_conversions:,.0f}).",
                    "Investigate the campaign's delivery and measurement changes before adjusting budget.")
    return pd.DataFrame(alerts, columns=ALERT_COLUMNS)


def _prorated_monthly_target(start, end, monthly_target):
    if start is None or end is None or monthly_target <= 0:
        return np.nan
    total = 0.0
    for period in pd.period_range(start=start, end=end, freq="M"):
        month_start = period.start_time.normalize()
        month_end = period.end_time.normalize()
        included_start, included_end = max(start, month_start), min(end, month_end)
        selected_days = max(0, (included_end - included_start).days + 1)
        total += monthly_target * selected_days / calendar.monthrange(period.year, period.month)[1]
    return total


def goal_attainment(
    frame,
    date_range,
    monthly_revenue_target,
    monthly_conversion_target,
    maximum_cpa,
    minimum_roi,
):
    """Compare filtered actuals to user targets, prorating monthly goals by days."""
    start, end = _resolve_range(frame, date_range)
    totals = summarize(frame)
    has_data = not frame.empty
    goals = [
        ("Revenue", totals["Revenue"] if has_data else np.nan,
         _prorated_monthly_target(start, end, monthly_revenue_target), "higher"),
        ("Conversions", totals["Conversions"] if has_data else np.nan,
         _prorated_monthly_target(start, end, monthly_conversion_target), "higher"),
        ("CPA", totals["CPA"] if has_data else np.nan, maximum_cpa, "lower"),
        ("ROI (%)", totals["ROI"] if has_data else np.nan, minimum_roi, "higher"),
    ]
    rows = []
    for metric, actual, target, direction in goals:
        target_is_set = pd.notna(target) and target > 0
        if not has_data or pd.isna(actual):
            progress, status = np.nan, "No data"
        elif not target_is_set:
            progress, status = np.nan, "Set target"
        elif direction == "higher":
            progress = min(max(actual / target, 0.0), 1.0)
            status = "Met" if actual >= target else "Below target"
        else:
            progress = 1.0 if actual <= target else (target / actual if actual > 0 else 0.0)
            progress = min(max(progress, 0.0), 1.0)
            status = "Met" if actual <= target else "Above maximum"
        rows.append({
            "Metric": metric, "Actual": actual, "Target": target,
            "Progress": progress, "Status": status, "Direction": direction,
        })
    return pd.DataFrame(rows)
