"""Judgment integrity, held-out sampling and honest temporal summaries."""
import unittest
from review_analyzer.validation.batches import make_batch, validate_import, resolve_annotations
from review_analyzer.validation.evaluation import evaluate
from review_analyzer.analysis.matching import match_reviews, METHOD
from review_analyzer.analysis.timeline import summarize
from review_analyzer.time import timestamp
from review_analyzer.cases.dredge import DREDGE


class ValidationTests(unittest.TestCase):
    def batch(self):
        reviews = {str(i): (i, {"recommendationid": str(i), "review": "Timed quests are frustrating.",
                   "timestamp_created": 1680300000, "timestamp_updated": 1680300000,
                   "author": {"steamid": "123"}}) for i in range(1, 11)}
        scored = [{"review_id": str(i), "change_id": topic, "passage": "Timed quests",
                   "similarity": 0.3 if i < 4 else 0.01} for i in range(1, 11)
                  for topic in ("quest-timers", "map-markers")]
        report = {"case": DREDGE, "method": METHOD, "threshold": 0.15}
        return {**make_batch(report, scored, reviews, below=14, seed=42), "batch_id": 1}

    def test_grouped_reproducible_split(self):
        batch = self.batch()
        self.assertEqual(batch, self.batch())
        grouped = {}
        for item in batch["items"]:
            grouped.setdefault(item["review_id"], set()).add(item["split"])
        self.assertTrue(all(len(splits) == 1 for splits in grouped.values()))
        self.assertEqual(len(batch["items"]), 20)

    def test_import_rejects_unknown_duplicate_or_incomplete_judgments(self):
        batch = self.batch()
        valid = {"key": batch["items"][0]["key"], "label": "complaint_request", "rationale": "Explicit request"}
        self.assertEqual(len(validate_import({"batch_id": 1, "annotations": [valid]}, batch)), 1)
        for rows in ([{**valid, "key": "unknown"}], [valid, valid], [{**valid, "rationale": ""}],
                     [{**valid, "label": "invented"}]):
            with self.assertRaises(ValueError):
                validate_import({"batch_id": 1, "annotations": rows}, batch)

    def test_latest_judgment_and_disagreement(self):
        def row(identifier, reviewer, label):
            return {"id": identifier, "snapshot_id": 1, "change_id": "quest-timers",
                    "reviewer": reviewer, "label": label, "sentiment": None}
        rows = [row(1, "a", "unrelated"), row(2, "a", "complaint_request")]
        self.assertEqual(resolve_annotations(rows)[(1, "quest-timers")]["validation"], "complaint_request")
        rows.append(row(3, "b", "neutral_mention"))
        self.assertEqual(resolve_annotations(rows)[(1, "quest-timers")]["validation"], "disputed")

    def test_evaluation_excludes_uncertain_and_other_split(self):
        items = [{"snapshot_id": i, "change_id": "x", "similarity": score, "split": split}
                 for i, score, split in [(1, .9, "evaluation"), (2, .8, "evaluation"),
                                        (3, .1, "evaluation"), (4, .9, "calibration"), (5, .9, "evaluation")]]
        judgments = {(i, "x"): {"validation": label} for i, label in
                     [(1, "complaint_request"), (2, "unrelated"), (3, "praise"), (4, "unrelated"), (5, "uncertain")]}
        result = evaluate({"items": items}, judgments, .5)
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (1, 1, 1))
        self.assertEqual(result["precision"], .5)
        self.assertEqual(result["recall"], .5)
        self.assertEqual(result["labeled"], 3)

    def test_generic_patch_words_no_longer_match_fish(self):
        reviews = [{"recommendationid": "1", "review": "Different types of fish?"}]
        self.assertEqual(match_reviews(reviews, DREDGE["changes"]), [])

    def test_candidates_are_not_confirmed_complaints(self):
        review = {"recommendationid": "1", "timestamp_created": timestamp("2023-04-01"),
                  "timestamp_updated": timestamp("2023-04-01")}
        match = {"review_id": "1", "change_id": "quest-timers", "validation": "unreviewed",
                 "sentiment": {"label": "negative"}}
        row = next(r for r in summarize([review], [match], DREDGE) if r["matched_reviews"])
        self.assertEqual(row["confirmed_complaints"], 0)
        self.assertEqual(row["sentiment_counts"], {})
        self.assertIsNone(row["confirmed_complaint_fraction"])
        match["validation"] = "complaint_request"
        row = next(r for r in summarize([review], [match], DREDGE) if r["matched_reviews"])
        self.assertEqual(row["confirmed_complaints"], 1)
        self.assertEqual(row["sentiment_counts"], {"negative": 1})


if __name__ == "__main__":
    unittest.main()
