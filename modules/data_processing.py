from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = ["Date", "Campaign_ID", "Campaign_Name", "Channel", "Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue"]
NUMERIC_COLUMNS = ["Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue"]
CHANNELS = ["Google Ads", "Meta Ads", "Email Marketing", "Influencer Marketing"]
ALIASES = {"Google": "Google Ads", "Meta": "Meta Ads", "Facebook/Instagram": "Meta Ads", "Email": "Email Marketing", "Influencer": "Influencer Marketing"}

def validate_data(frame):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("The uploaded file has no campaign records.")
    out = frame.copy()
    out.columns = [str(c).strip() for c in out.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    out = out[REQUIRED_COLUMNS].copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    if out.Date.isna().any():
        raise ValueError(f"Date contains {int(out.Date.isna().sum())} invalid or blank value(s).")
    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        if out[col].isna().any(): raise ValueError(f"{col} contains blank or non-numeric values.")
        if (out[col] < 0).any(): raise ValueError(f"{col} cannot contain negative values.")
    for current, previous in [("Clicks", "Impressions"), ("Leads", "Clicks"), ("Conversions", "Leads")]:
        if (out[current] > out[previous]).any(): raise ValueError(f"{current} cannot exceed {previous}.")
    for col in ["Campaign_ID", "Campaign_Name", "Channel"]:
        out[col] = out[col].astype(str).str.strip()
        if out[col].eq("").any(): raise ValueError(f"{col} contains blank values.")
    out["Channel"] = out["Channel"].replace(ALIASES)
    unknown = sorted(set(out.Channel) - set(CHANNELS))
    if unknown: raise ValueError("Unsupported channel(s): " + ", ".join(unknown) + ".")
    return out.sort_values("Date").reset_index(drop=True)

def load_sample_data(path=None):
    if path is None: path = Path(__file__).resolve().parents[1] / "data" / "sample_campaign_data.csv"
    return validate_data(pd.read_csv(path))

def filter_data(frame, date_range=None, channels=None):
    result = frame.copy()
    if date_range:
        if not isinstance(date_range, (tuple, list)):
            date_range = (date_range, date_range)
        if len(date_range) == 1:
            date_range = (date_range[0], date_range[0])
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[-1])
        result = result[result.Date.between(start, end + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1))]
    # An empty multiselect means the user selected no channels, not "all channels".
    if channels is not None:
        result = result[result.Channel.isin(channels)]
    return result.reset_index(drop=True)
