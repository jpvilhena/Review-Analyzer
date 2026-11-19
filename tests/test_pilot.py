"""Regression checks for historical evidence and review retrieval."""
import json
import unittest
from unittest.mock import patch, Mock
from review_analyzer.cases.dredge import DREDGE
from review_analyzer.time import period, timestamp
from review_analyzer.analysis.matching import match_reviews
from review_analyzer.analysis.timeline import summarize
from review_analyzer.collection.steam import fetch_reviews


class PilotTests(unittest.TestCase):
    def test_temporal_boundaries(self):
        boundary = timestamp(DREDGE["release_date"])
        for created, updated, expected in [(boundary-1, boundary-1, "before"),
                (boundary-1, boundary, "edited_after_boundary"),
                (boundary, boundary, "release_day"), (boundary+86400, boundary+86400, "after")]:
            self.assertEqual(period({"timestamp_created": created, "timestamp_updated": updated},
                                    DREDGE["release_date"]), expected)

    @patch("review_analyzer.collection.steam.requests.get")
    def test_pagination_bounds_and_duplicates(self, get):
        responses = []
        for reviews, cursor in [([{"recommendationid": "1"}], "next"),
                                ([{"recommendationid": "1"}], "last"), ([], "last")]:
            response = Mock()
            response.json.return_value = {"response": {"reviews": reviews, "cursor": cursor}}
            responses.append(response)
        get.side_effect = responses
        coverage = {}
        self.assertEqual(len(fetch_reviews(1, 5, start=100, end=200, metadata=coverage)), 1)
        self.assertTrue(coverage["exhausted"])
        params = json.loads(get.call_args_list[1].kwargs["params"]["input_json"])
        self.assertEqual(params["cursor"], "next")
        self.assertEqual(params["date_range_end"], 199)

    def test_matching_empty_and_relevant_passages(self):
        self.assertEqual(match_reviews([], DREDGE["changes"]), [])
        matches = match_reviews([{"recommendationid": "1", "review":
            "Wonderful soundtrack. Remove the hidden timers on timed quests."}], DREDGE["changes"])
        self.assertTrue(any(m["change_id"] == "quest-timers" for m in matches))
        self.assertTrue(all(m["validation"] == "unreviewed" for m in matches))

    def test_empty_weeks_have_no_fabricated_sentiment(self):
        rows = summarize([], [], DREDGE)
        self.assertTrue(rows)
        self.assertTrue(all(r["match_fraction"] is None and r["sentiment_counts"] == {} for r in rows))

    @patch("review_analyzer.collection.steam.requests.get")
    def test_http_errors_are_not_empty_collections(self, get):
        get.return_value.raise_for_status.side_effect = RuntimeError("HTTP error")
        with self.assertRaises(RuntimeError):
            fetch_reviews(1)

    @patch("review_analyzer.collection.steam.requests.get")
    def test_steam_omits_empty_repeated_field(self, get):
        get.return_value.json.return_value = {"response": {"query_summary": {"num_reviews": 0}}}
        metadata = {}
        self.assertEqual(fetch_reviews(1, metadata=metadata), [])
        self.assertTrue(metadata["exhausted"])

    @patch.dict("os.environ", {"AZURE_ENDPOINT": "https://example.test", "AZURE_KEY": "test"})
    @patch("review_analyzer.analysis.sentiment.TextAnalyticsClient")
    def test_sentiment_preserves_errors(self, client):
        from review_analyzer.analysis.sentiment import analyze_passages
        success = Mock(is_error=False, sentiment="negative")
        success.confidence_scores.positive = 0.01
        success.confidence_scores.neutral = 0.09
        success.confidence_scores.negative = 0.9
        error = Mock(is_error=True)
        error.error.code = "InvalidDocument"
        client.return_value.__enter__.return_value.analyze_sentiment.return_value = [success, error]
        matches = [{"passage": "Hidden timers are frustrating."}, {"passage": "Bad document"}]
        analyze_passages(matches)
        self.assertEqual(matches[0]["sentiment"]["label"], "negative")
        self.assertEqual(matches[1]["sentiment"]["label"], "error")


if __name__ == "__main__":
    unittest.main()
