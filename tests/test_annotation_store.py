"""Optional PostgreSQL integration tests; every fixture is rolled back."""
import os
import unittest
import uuid
from importlib.metadata import version
import psycopg
from psycopg.types.json import Jsonb
from review_analyzer.cases.dredge import DREDGE
from review_analyzer.storage.reviews import initialize, save_reviews
from review_analyzer.analysis.matching import METHOD
from review_analyzer.cli.review import prepare, load_batch
from review_analyzer.storage.annotations import import_annotations, load_judgments


@unittest.skipUnless(os.getenv("RUN_DATABASE_TESTS") == "1", "Database integration is opt-in")
class AnnotationStoreTests(unittest.TestCase):
    def setUp(self):
        self.connection = psycopg.connect(os.environ["DATABASE_URL"])
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        initialize(self.connection)
        self.case = {**DREDGE, "id": "test-" + uuid.uuid4().hex}
        self.connection.execute("INSERT INTO patches VALUES (%s,%s)", (self.case["id"], Jsonb(self.case)))
        review = {"recommendationid": self.case["id"], "review": "Hidden timed quests need clear timers.",
                  "language": "english", "voted_up": False, "timestamp_created": 1,
                  "timestamp_updated": 1, "author": {"steamid": "123"}}
        save_reviews(self.connection, 1, [review])
        snapshot_id = self.connection.execute("SELECT id FROM review_snapshots WHERE review_id=%s",
                                               (review["recommendationid"],)).fetchone()[0]
        report = {"case": self.case, "threshold": .15, "method": METHOD,
                  "sklearn_version": version("scikit-learn"), "snapshot_ids": [snapshot_id]}
        run_id = self.connection.execute("INSERT INTO analysis_runs (case_id,report) VALUES (%s,%s) RETURNING id",
                                         (self.case["id"], Jsonb(report))).fetchone()[0]
        self.batch = prepare(self.connection, run_id, below=10, seed=42)

    def test_append_only_import_is_idempotent_and_disagreement_is_preserved(self):
        batch = load_batch(self.connection, self.batch["batch_id"])
        item = batch["items"][0]
        row = {"key": item["key"], "label": "complaint_request", "rationale": "Explicit complaint"}
        document = {"batch_id": batch["batch_id"], "annotations": [row]}
        self.assertEqual(import_annotations(self.connection, document, batch, "reviewer-a"), 1)
        self.assertEqual(import_annotations(self.connection, document, batch, "reviewer-a"), 0)
        row["label"] = "unrelated"
        self.assertEqual(import_annotations(self.connection, document, batch, "reviewer-b"), 1)
        judgment = load_judgments(self.connection, self.case["id"])[(item["snapshot_id"], item["change_id"])]
        self.assertEqual(judgment["validation"], "disputed")
        row["label"] = "complaint_request"
        import_annotations(self.connection, document, batch, "reviewer-b")
        judgment = load_judgments(self.connection, self.case["id"])[(item["snapshot_id"], item["change_id"])]
        self.assertEqual(judgment["validation"], "complaint_request")
        self.assertEqual(len(judgment["annotation_ids"]), 2)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM review_annotations WHERE case_id=%s",
                                                (self.case["id"],)).fetchone()[0], 3)

    def test_invalid_submission_writes_no_partial_labels(self):
        item = self.batch["items"][0]
        document = {"batch_id": self.batch["batch_id"], "annotations": [
            {"key": item["key"], "label": "complaint_request", "rationale": "Valid"},
            {"key": "not-in-batch", "label": "unrelated", "rationale": "Invalid"}]}
        with self.assertRaises(ValueError):
            import_annotations(self.connection, document, self.batch, "reviewer")
        self.assertEqual(self.connection.execute("SELECT count(*) FROM review_annotations WHERE case_id=%s",
                                                (self.case["id"],)).fetchone()[0], 0)
