import numpy as np
import pandas as pd
from .data_processing import CHANNELS

def safe_divide(numerator, denominator, multiplier=1.0):
    if denominator is None or denominator == 0 or pd.isna(denominator): return np.nan
    return numerator / denominator * multiplier

def summarize(frame):
    fields = ["Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue"]
    result = {c: float(frame[c].sum()) if len(frame) else 0.0 for c in fields}
    result.update(
        CTR=safe_divide(result["Clicks"], result["Impressions"], 100),
        CPC=safe_divide(result["Ad_Spend"], result["Clicks"]),
        CPL=safe_divide(result["Ad_Spend"], result["Leads"]),
        CPA=safe_divide(result["Ad_Spend"], result["Conversions"]),
        Conversion_Rate=safe_divide(result["Conversions"], result["Clicks"], 100),
        ROI=safe_divide(result["Revenue"] - result["Ad_Spend"], result["Ad_Spend"], 100),
        ROAS=safe_divide(result["Revenue"], result["Ad_Spend"]),
    )
    return result

def channel_performance(frame):
    fields = ["Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue"]
    if frame.empty: return pd.DataFrame(columns=["Channel", *fields, "CTR (%)", "CPC", "CPL", "CPA", "Conversion Rate (%)", "ROI (%)", "ROAS"])
    x = frame.groupby("Channel", as_index=False)[fields].sum().set_index("Channel").reindex(CHANNELS, fill_value=0).rename_axis("Channel").reset_index()
    calc = {"CTR (%)": ("Clicks", "Impressions", 100), "CPC": ("Ad_Spend", "Clicks", 1), "CPL": ("Ad_Spend", "Leads", 1), "CPA": ("Ad_Spend", "Conversions", 1), "Conversion Rate (%)": ("Conversions", "Clicks", 100), "ROAS": ("Revenue", "Ad_Spend", 1)}
    for name, (num, den, mult) in calc.items(): x[name] = x.apply(lambda r: safe_divide(r[num], r[den], mult), axis=1)
    x["ROI (%)"] = x.apply(lambda r: safe_divide(r.Revenue-r.Ad_Spend, r.Ad_Spend, 100), axis=1)
    return x

def monthly_performance(frame):
    columns = ["Month", "Channel", "Ad_Spend", "Revenue", "Conversions", "ROI (%)"]
    if frame.empty: return pd.DataFrame(columns=columns)
    x = frame.assign(Month=frame.Date.dt.to_period("M").dt.to_timestamp()).groupby(["Month", "Channel"], as_index=False)[["Ad_Spend", "Revenue", "Conversions"]].sum()
    x["ROI (%)"] = x.apply(lambda r: safe_divide(r.Revenue-r.Ad_Spend, r.Ad_Spend, 100), axis=1)
    return x

def campaign_performance(frame):
    """Aggregate the filtered records to campaign level for the overview table."""
    columns = ["Campaign_ID", "Campaign_Name", "Channel", "Impressions", "Clicks",
               "Leads", "Conversions", "Ad_Spend", "Revenue", "ROI (%)", "ROAS"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    fields = ["Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue"]
    result = frame.groupby(["Campaign_ID", "Campaign_Name", "Channel"], as_index=False)[fields].sum()
    result["ROI (%)"] = result.apply(lambda r: safe_divide(r.Revenue-r.Ad_Spend, r.Ad_Spend, 100), axis=1)
    result["ROAS"] = result.apply(lambda r: safe_divide(r.Revenue, r.Ad_Spend), axis=1)
    return result[columns].sort_values(["Revenue", "Ad_Spend"], ascending=False).reset_index(drop=True)

def funnel_metrics(frame):
    totals = summarize(frame); stages = ["Impressions", "Clicks", "Leads", "Conversions"]; rows=[]; drops=[]
    for i, stage in enumerate(stages):
        volume=totals[stage]; conv=safe_divide(volume, totals[stages[i-1]], 100) if i else np.nan; drop=100-conv if i and not pd.isna(conv) else np.nan
        if i and not pd.isna(drop): drops.append((stage, drop))
        rows.append({"Stage":stage,"Volume":volume,"Conversion from prior (%)":conv,"Drop-off from prior (%)":drop})
    return pd.DataFrame(rows), (max(drops,key=lambda p:p[1])[0] if drops else "Not available")
