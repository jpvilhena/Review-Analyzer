"""DREDGE historical collection, passage matching and weekly reporting."""
import argparse
import json
import os
from importlib.metadata import version
from pathlib import Path
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb
from review_analyzer.cases.dredge import DREDGE
from review_analyzer.storage.reviews import initialize, save_reviews
from review_analyzer.time import timestamp, period
from review_analyzer.analysis.matching import match_reviews, METHOD
from review_analyzer.analysis.timeline import summarize
from review_analyzer.storage.annotations import load_judgments
from review_analyzer.validation.batches import RELEVANT
from review_analyzer.collection.steam import fetch_reviews


def collect(connection, case, pages):
    runs = []
    for start, end in [(case["start"], case["release_date"]), (case["release_date"], case["end"])]:
        coverage = {}
        reviews = fetch_reviews(case["app_id"], pages, start=timestamp(start), end=timestamp(end), metadata=coverage)
        save_reviews(connection, case["app_id"], reviews)
        params = {"app_id": case["app_id"], "start": start, "end_exclusive": end,
                  "language": "english", "page_limit": pages, "page_size": 100}
        coverage["retrieved"] = len(reviews)
        connection.execute("INSERT INTO collection_runs (parameters, coverage) VALUES (%s,%s)",
                           (Jsonb(params), Jsonb(coverage)))
        runs.append({"parameters": params, "coverage": coverage})
    return {"collections": runs}


def analyze(connection, case, threshold, sentiment):
    rows = connection.execute(
        """SELECT DISTINCT ON (review_id) id,
        payload || jsonb_build_object('review', review_text, 'language', language,
                                      'voted_up', steam_recommended)
        FROM review_snapshots
        WHERE app_id=%s AND created_at>=to_timestamp(%s) AND created_at<to_timestamp(%s)
        ORDER BY review_id, observed_at DESC, id DESC""",
        (case["app_id"], timestamp(case["start"]), timestamp(case["end"]))).fetchall()
    if not rows:
        raise ValueError("No reviews collected for this case")
    reviews = [r[1] for r in rows]
    judgments = load_judgments(connection, case["id"])
    scored = match_reviews(reviews, case["changes"], 0)
    matches = []
    by_id = {str(r[1]["recommendationid"]): r for r in rows}
    for match in scored:
        snapshot_id, review = by_id[match["review_id"]]
        judgment = judgments.get((snapshot_id, match["change_id"]), {})
        selected = match["similarity"] >= threshold
        if not selected and judgment.get("validation") not in RELEVANT:
            continue
        match.update(judgment)
        match.update(snapshot_id=snapshot_id, period=period(review, case["release_date"]),
                     created_at=review["timestamp_created"], updated_at=review["timestamp_updated"],
                     steam_recommended=review["voted_up"],
                     review_text=review["review"], selected_by_model=selected,
                     source=f"https://steamcommunity.com/profiles/{review['author']['steamid']}/recommended/{case['app_id']}/")
        matches.append(match)
    sentiment_matches = [m for m in matches if m["validation"] in RELEVANT]
    if sentiment:
        from review_analyzer.analysis.sentiment import analyze_passages
        if sentiment_matches:
            analyze_passages(sentiment_matches)
    collections = connection.execute(
        "SELECT id, parameters, coverage FROM collection_runs WHERE parameters->>'app_id'=%s ORDER BY id",
        (str(case["app_id"]),)).fetchall()
    return {"case": case, "method": METHOD,
            "sklearn_version": version("scikit-learn"), "threshold": threshold,
            "sentiment_provider": "azure-latest" if sentiment and sentiment_matches else None,
            "sentiment_requested": sentiment,
            "annotation_ids": sorted({i for m in matches for i in m.get("annotation_ids", [])}),
            "events": [{"date": case["release_date"], "title": f"Update {case['version']}", "source": case["source"]}],
            "snapshot_ids": [r[0] for r in rows], "review_count": len(reviews),
            "collections": [{"id": r[0], "parameters": r[1], "coverage": r[2]} for r in collections],
            "matches": matches, "timeline": summarize(reviews, matches, case),
            "limitations": ["Unreviewed matches are candidates, not confirmed complaints or causal evidence.",
                            "Confirmed counts depend on annotation coverage and are not total complaint prevalence.",
                            "Sentiment is computed only for human-validated relevant pairs when requested.",
                            "Later edits and release-day reviews are separated from pre-patch evidence.",
                            "Counts describe collected data; coverage may be incomplete.",
                            "Patch timing has UTC day precision."]}


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["collect", "analyze"])
    parser.add_argument("--pages", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.15)
    parser.add_argument("--sentiment", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--html", type=Path, help="Offline evidence report and PNG timeline")
    args = parser.parse_args(argv)
    if args.pages <= 0 or not 0 < args.threshold <= 1:
        parser.error("Pages must be positive and threshold must be in (0, 1]")
    if args.html and args.action != "analyze":
        parser.error("HTML reporting requires analyze")
    case = DREDGE
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        initialize(connection)
        connection.execute("INSERT INTO patches VALUES (%s,%s) ON CONFLICT DO NOTHING", (case["id"], Jsonb(case)))
        if connection.execute("SELECT definition FROM patches WHERE case_id=%s", (case["id"],)).fetchone()[0] != case:
            raise ValueError("Changed definitions require a new case ID")
        report = collect(connection, case, args.pages) if args.action == "collect" else analyze(connection, case, args.threshold, args.sentiment)
        if args.action == "analyze":
            report["run_id"] = connection.execute(
                "INSERT INTO analysis_runs (case_id, report) VALUES (%s,%s) RETURNING id",
                (case["id"], Jsonb(report))).fetchone()[0]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.html:
        from review_analyzer.reporting.html import write_report
        write_report(report, args.html)
    print(json.dumps({k: v for k, v in report.items() if k not in ("matches", "timeline", "snapshot_ids")}, indent=2))


if __name__ == "__main__":
    main()
