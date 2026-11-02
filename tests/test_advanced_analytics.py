"""Automated tests for the added comparison, alert, ranking, and goal rules."""
import unittest

import numpy as np
import pandas as pd

from modules.advanced_analytics import (
    campaign_metrics,
    default_alert_thresholds,
    generate_performance_alerts,
    goal_attainment,
    period_frames,
    period_over_period,
    rank_campaigns,
)


def row(day, campaign_id, name, impressions, clicks, leads, conversions, spend, revenue,
        channel="Google Ads"):
    return {
        "Date": pd.Timestamp(day), "Campaign_ID": campaign_id, "Campaign_Name": name,
        "Channel": channel, "Impressions": impressions, "Clicks": clicks,
        "Leads": leads, "Conversions": conversions, "Ad_Spend": spend,
        "Revenue": revenue,
    }


class CampaignMetricsTests(unittest.TestCase):
    def test_campaign_metrics_recompute_ratios_from_totals(self):
        data = pd.DataFrame([
            row("2025-01-01", "A", "Alpha", 100, 50, 20, 5, 100, 300),
            row("2025-01-02", "A", "Alpha", 100, 50, 20, 5, 100, 300),
        ])
        actual = campaign_metrics(data).iloc[0]
        self.assertEqual(actual["Impressions"], 200)
        self.assertAlmostEqual(actual["CTR (%)"], 50.0)
        self.assertAlmostEqual(actual["CPC"], 2.0)
        self.assertAlmostEqual(actual["CPA"], 20.0)
        self.assertAlmostEqual(actual["ROI (%)"], 200.0)
        self.assertAlmostEqual(actual["ROAS"], 3.0)

    def test_zero_denominators_are_unavailable(self):
        actual = campaign_metrics(pd.DataFrame([
            row("2025-01-01", "Z", "Zero", 0, 0, 0, 0, 0, 0),
        ])).iloc[0]
        self.assertTrue(pd.isna(actual["CTR (%)"]))
        self.assertTrue(pd.isna(actual["CPC"]))
        self.assertTrue(pd.isna(actual["CPA"]))
        self.assertTrue(pd.isna(actual["ROI (%)"]))
        self.assertTrue(pd.isna(actual["ROAS"]))

    def test_rankings_follow_selected_metric_and_exclude_unavailable_cpa(self):
        data = pd.DataFrame([
            row("2025-01-01", "A", "Alpha", 100, 50, 20, 5, 100, 300),
            row("2025-01-01", "B", "Beta", 100, 50, 20, 2, 200, 100),
            row("2025-01-01", "C", "Gamma", 100, 50, 20, 0, 50, 100),
        ])
        roi = rank_campaigns(data, "Highest ROI")
        cpa = rank_campaigns(data, "Lowest CPA")
        self.assertEqual(roi.iloc[0]["Campaign_ID"], "A")
        self.assertEqual(cpa["Campaign_ID"].tolist(), ["A", "B"])


class PeriodComparisonTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([
            row("2024-12-30", "A", "Alpha", 100, 50, 10, 5, 40, 100),
            row("2024-12-31", "A", "Alpha", 100, 50, 10, 5, 40, 100),
            row("2025-01-01", "A", "Alpha", 100, 50, 10, 5, 50, 150),
            row("2025-01-02", "A", "Alpha", 100, 50, 10, 5, 50, 150),
        ])

    def test_equal_length_periods_and_changes(self):
        current, previous, start, end, prior_start, prior_end = period_frames(
            self.data, (pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")), ["Google Ads"]
        )
        self.assertEqual(len(current), 2)
        self.assertEqual(len(previous), 2)
        self.assertEqual((prior_start.date(), prior_end.date()),
                         (pd.Timestamp("2024-12-30").date(), pd.Timestamp("2024-12-31").date()))
        result = period_over_period(self.data, (start, end), ["Google Ads"])
        self.assertAlmostEqual(result["Revenue Change (%)"], 50.0)
        self.assertAlmostEqual(result["Spend Change (%)"], 25.0)
        self.assertAlmostEqual(result["ROI Change (pp)"], 50.0)
        self.assertAlmostEqual(result["Conversion Change (%)"], 0.0)
        self.assertAlmostEqual(result["Lead Change (%)"], 0.0)

    def test_missing_and_zero_baselines_are_unavailable(self):
        no_prior = self.data[self.data.Date >= "2025-01-01"]
        missing = period_over_period(no_prior, (pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")))
        self.assertTrue(np.isnan(missing["Revenue Change (%)"]))
        zero_base = pd.DataFrame([
            row("2024-12-30", "A", "Alpha", 100, 20, 0, 0, 40, 0),
            row("2025-01-01", "A", "Alpha", 100, 20, 0, 0, 40, 0),
        ])
        result = period_over_period(zero_base, (pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-01")))
        self.assertTrue(np.isnan(result["Revenue Change (%)"]))
        self.assertTrue(np.isnan(result["Conversion Change (%)"]))


class AlertTests(unittest.TestCase):
    def test_thresholds_and_all_requested_alert_rules(self):
        current = pd.DataFrame([
            row("2025-01-01", "A", "Alpha", 100, 20, 10, 2, 100, 50),
            row("2025-01-01", "B", "Beta", 100, 20, 10, 1, 1000, 150),
            row("2025-01-01", "C", "Gamma", 100, 20, 0, 0, 2000, 0),
        ])
        previous = pd.DataFrame([
            row("2024-12-01", "A", "Alpha", 100, 20, 10, 4, 100, 100),
            row("2024-12-01", "B", "Beta", 100, 20, 10, 1, 900, 100),
            row("2024-12-01", "C", "Gamma", 100, 20, 0, 0, 1000, 0),
        ])
        thresholds = default_alert_thresholds(current)
        self.assertGreater(thresholds["High CPA threshold (INR)"], 0)
        self.assertGreater(thresholds["High spend threshold (INR)"], 0)
        alerts = generate_performance_alerts(
            current, previous, cpa_threshold=500, spend_threshold=1500,
            significant_change_pct=20,
        )
        categories = set(alerts["Alert"])
        self.assertIn("Negative ROI", categories)
        self.assertIn("High CPA", categories)
        self.assertIn("High spend without conversions", categories)
        self.assertIn("Revenue decline", categories)
        self.assertIn("Significant campaign change", categories)

    def test_empty_data_returns_empty_alert_table(self):
        empty = pd.DataFrame(columns=["Date", "Campaign_ID", "Campaign_Name", "Channel",
                                      "Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue"])
        self.assertTrue(generate_performance_alerts(empty).empty)


class GoalTests(unittest.TestCase):
    def test_monthly_targets_prorate_to_selected_days(self):
        data = pd.DataFrame([
            row("2024-02-15", "A", "Alpha", 100, 20, 10, 2, 100, 150),
            row("2024-02-16", "A", "Alpha", 100, 20, 10, 2, 100, 150),
        ])
        goals = goal_attainment(
            data, (pd.Timestamp("2024-02-15"), pd.Timestamp("2024-02-16")),
            monthly_revenue_target=2900, monthly_conversion_target=29,
            maximum_cpa=100, minimum_roi=50,
        ).set_index("Metric")
        self.assertAlmostEqual(goals.loc["Revenue", "Target"], 200.0)
        self.assertAlmostEqual(goals.loc["Conversions", "Target"], 2.0)
        self.assertEqual(goals.loc["CPA", "Status"], "Met")
        self.assertEqual(goals.loc["ROI (%)", "Status"], "Met")

    def test_zero_targets_are_unset_and_empty_data_is_not_claimed_as_met(self):
        data = pd.DataFrame([
            row("2025-01-01", "A", "Alpha", 100, 20, 10, 2, 100, 150),
        ])
        goals = goal_attainment(data, (pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-01")), 0, 0, 0, 0)
        self.assertTrue(goals["Status"].eq("Set target").all())
        empty = data.iloc[0:0]
        no_data = goal_attainment(empty, (pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-01")), 100, 10, 20, 50)
        self.assertTrue(no_data["Status"].eq("No data").all())


if __name__ == "__main__":
    unittest.main()
