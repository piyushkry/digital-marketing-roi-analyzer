import pandas as pd

def generate_insights(performance, funnel, frame):
    """Create evidence-backed insight cards from the currently filtered data."""
    insights = []
    active = performance[(performance.Ad_Spend > 0) & performance["ROI (%)"].notna()]
    if not active.empty:
        best = active.sort_values(["ROI (%)", "ROAS"], ascending=False).iloc[0]
        insights.append({
            "priority": "High" if best["ROI (%)"] > 0 else "Medium",
            "finding": f"{best.Channel} leads the filtered channels on revenue-based ROI.",
            "evidence": f"ROI {best['ROI (%)']:.1f}% · ROAS {best.ROAS:.2f}x · spend ₹{best.Ad_Spend:,.0f}",
            "implication": "This channel produced the strongest observed revenue return per rupee spent in this selection.",
            "action": "Consider a measured budget test and monitor marginal returns before scaling.",
        })
        lowest = active.sort_values(["ROI (%)", "CPA"], ascending=[True, False]).iloc[0]
        if lowest.Channel != best.Channel:
            cpa = f"₹{lowest.CPA:,.0f}" if pd.notna(lowest.CPA) else "unavailable"
            insights.append({
                "priority": "High" if lowest["ROI (%)"] <= 0 else "Medium",
                "finding": f"{lowest.Channel} has the weakest observed ROI among channels with spend.",
                "evidence": f"ROI {lowest['ROI (%)']:.1f}% · CPA {cpa} · revenue ₹{lowest.Revenue:,.0f}",
                "implication": "Its recent return is below the other active channels in this filtered view.",
                "action": "Review campaign mix, audience, attribution, and conversion quality before reallocating.",
            })
    steps = funnel.iloc[1:] if not funnel.empty else funnel
    if not steps.empty and steps["Drop-off from prior (%)"].notna().any():
        row = steps.loc[steps["Drop-off from prior (%)"].idxmax()]
        advice = {
            "Clicks": "Review creative, audience relevance, and placement.",
            "Leads": "Review landing page message match, speed, and form friction.",
            "Conversions": "Review lead quality, follow-up time, and nurturing.",
        }
        insights.append({
            "priority": "High",
            "finding": f"The largest funnel drop-off occurs before {row.Stage.lower()}.",
            "evidence": f"{row['Drop-off from prior (%)']:.1f}% drop-off from the prior stage · {row.Volume:,.0f} {row.Stage.lower()}",
            "implication": "The largest observed volume loss is concentrated at this transition.",
            "action": advice.get(row.Stage, "Investigate the transition and tracking quality."),
        })
    spenders = performance[performance.Ad_Spend > 0]
    if not spenders.empty:
        cpa_rows = spenders[spenders.CPA.notna()]
        if not cpa_rows.empty:
            row = cpa_rows.sort_values("CPA", ascending=False).iloc[0]
            insights.append({
                "priority": "Medium",
                "finding": f"{row.Channel} has the highest observed acquisition cost.",
                "evidence": f"CPA ₹{row.CPA:,.0f} · {row.Conversions:,.0f} conversions · spend ₹{row.Ad_Spend:,.0f}",
                "implication": "Acquiring a conversion costs more here than in the other channels with conversions.",
                "action": "Inspect campaign-level CPA and test lower-cost audiences or creative.",
            })
    if frame.empty:
        return [{"priority": "Low", "finding": "No campaign records match the selected filters.",
                 "evidence": "No filtered observations", "implication": "There is no current evidence to compare.",
                 "action": "Expand the date range or select one or more channels."}]
    if not insights:
        insights.append({"priority": "Low", "finding": "No clear channel priority is present in this selection.",
                         "evidence": f"{len(frame):,} filtered campaign records", "implication": "The available metrics do not identify a clear leader.",
                         "action": "Review performance over a longer period and verify tracking completeness."})
    return insights

def generate_recommendations(performance, funnel, frame):
    recs=[]; active=performance[(performance.Ad_Spend>0)&(performance.Revenue>0)]
    if not active.empty:
        ranked=active.sort_values(["ROI (%)","ROAS"],ascending=False); best=ranked.iloc[0]; worst=ranked.iloc[-1]
        recs.append(f"Prioritize controlled budget tests in {best.Channel}: it has the strongest observed ROI ({best['ROI (%)']:.1f}%) among channels with spend and revenue. Monitor marginal returns before scaling.")
        if best.Channel != worst.Channel: recs.append(f"Review {worst.Channel}: observed ROI is {worst['ROI (%)']:.1f}% and CPA is {'₹'+format(worst.CPA,',.2f') if pd.notna(worst.CPA) else 'unavailable'}. Check targeting, attribution, and setup.")
    steps=funnel.iloc[1:]
    if not steps.empty and steps["Drop-off from prior (%)"].notna().any():
        row=steps.loc[steps["Drop-off from prior (%)"].idxmax()]; drop=row["Drop-off from prior (%)"]
        advice={"Clicks":"Test creative, audience relevance, and placement.","Leads":"Review landing page speed, message match, and form friction.","Conversions":"Review lead quality, follow-up time, and lead nurturing."}
        recs.append(f"The largest funnel loss is before {row.Stage} ({drop:.1f}% drop-off). {advice[row.Stage]}")
    spenders=performance[performance.Ad_Spend>0]
    if not spenders.empty:
        low=spenders.sort_values("Revenue").iloc[0]
        if low.Revenue < low.Ad_Spend: recs.append(f"{low.Channel} has revenue below ad spend in this view (₹{low.Revenue:,.0f} vs ₹{low.Ad_Spend:,.0f}). Inspect campaign outliers and measurement.")
    if frame.empty: recs.append("No campaigns match these filters. Expand the date range or select more channels.")
    elif not recs: recs.append("The selected data shows no clear channel or funnel priority. Monitor over a longer period before reallocating.")
    recs.append("These recommendations describe historical filtered data and do not guarantee future results.")
    return recs

def budget_allocation(performance,total_budget):
    data=performance[["Channel","ROI (%)","CPA","Ad_Spend","Revenue"]].copy()
    data["Proposed Budget"]=0.0
    data["Allocation (%)"]=0.0
    spend_total = data["Ad_Spend"].sum()
    data["Current Allocation (%)"] = data["Ad_Spend"].div(spend_total).mul(100) if spend_total > 0 else 0.0
    data["Recommendation Reason"]=""
    eligible=data[(data.Ad_Spend>0)&data["ROI (%)"].notna()&(data["ROI (%)"]>0)]
    if total_budget>0 and len(eligible):
        raw=eligible["ROI (%)"].clip(lower=0)+100
        if len(eligible)==1: weights=pd.Series(1.0,index=eligible.index)
        else:
            weights=pd.Series(0.0,index=eligible.index); remaining=list(eligible.index); pool_share=1.0
            while remaining:
                proposal=raw.loc[remaining]/raw.loc[remaining].sum()*pool_share; capped=proposal[proposal>0.5]
                if capped.empty: weights.loc[remaining]=proposal; break
                for idx in capped.index: weights.loc[idx]=0.5; pool_share-=0.5; remaining.remove(idx)
                if pool_share<=0 or not remaining: break
        data.loc[eligible.index,"Proposed Budget"]=weights.to_numpy()*total_budget
        data.loc[eligible.index,"Allocation (%)"]=weights.to_numpy()*100
    for idx,row in data.iterrows():
        if row.Ad_Spend <= 0:
            reason="No spend in the filtered period; there is no observed ROI to guide an allocation."
        elif pd.isna(row["ROI (%)"]):
            reason="ROI is unavailable because the denominator (ad spend) is zero or missing."
        elif row["ROI (%)"] <= 0:
            reason=f"Hold or reduce: revenue-based ROI is {row['ROI (%)']:.1f}% for the filtered period."
        else:
            cpa=f"₹{row.CPA:,.2f}" if pd.notna(row.CPA) else "unavailable"
            reason=(f"Eligible based on positive revenue-based ROI ({row['ROI (%)']:.1f}%) and observed CPA ({cpa}). "
                    "Weight is ROI + 100, normalized across eligible channels; capped at 50% when multiple channels qualify.")
        data.loc[idx,"Recommendation Reason"]=reason
    return data
