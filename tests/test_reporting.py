"""Offline review pages preserve source text without executing it."""
import tempfile
import unittest
from pathlib import Path
from review_analyzer.reporting.html import write_validation
from tests import test_validation


class ReportingTests(unittest.TestCase):
    def test_source_text_is_escaped_and_benchmark_details_are_blinded(self):
        batch = test_validation.ValidationTests().batch()
        batch["items"][0]["review_text"] = '<script>alert("source")</script>'
        batch["items"][0]["passage"] = '<img src=x onerror=alert(1)>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.html"
            write_validation(batch, path)
            text = path.read_text(encoding="utf-8")
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('<script>alert', text)
        self.assertNotIn('<img src=x', text)
        self.assertEqual(text.count('<article data-key='), len(batch["items"]))
        self.assertNotIn('"similarity":', text)
        self.assertNotIn('"split":', text)
