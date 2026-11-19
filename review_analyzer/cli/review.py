"""Preparation, audited import and evaluation of human review judgments."""
import argparse
import json
import os
from pathlib import Path
from importlib.metadata import version
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb
from review_analyzer.storage.reviews import initialize
from review_analyzer.storage.annotations import import_annotations, load_judgments
from review_analyzer.validation.evaluation import evaluate
from review_analyzer.analysis.matching import match_reviews
from review_analyzer.validation.batches import make_batch


def prepare(connection, run_id, below, seed):
    row = connection.execute("SELECT report FROM analysis_runs WHERE id=%s", (run_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown analysis run")
    report = row[0]
    if report["sklearn_version"] != version("scikit-learn"):
        raise ValueError("Analysis and benchmark preparation require the same scikit-learn version")
    rows = connection.execute("SELECT id, payload FROM review_snapshots WHERE id=ANY(%s) ORDER BY id",
                              (report["snapshot_ids"],)).fetchall()
    if len(rows) != len(report["snapshot_ids"]):
        raise ValueError("Some source snapshots are missing")
    snapshots = {str(review["recommendationid"]): (snapshot_id, review) for snapshot_id, review in rows}
    scored = match_reviews([r[1] for r in rows], report["case"]["changes"], 0, method=report["method"])
    batch = make_batch(report, scored, snapshots, below, seed)
    batch["run_id"] = run_id
    batch_id = connection.execute("INSERT INTO validation_batches (run_id,data) VALUES (%s,%s) RETURNING id",
                                  (run_id, Jsonb(batch))).fetchone()[0]
    batch["batch_id"] = batch_id
    return batch


def load_batch(connection, batch_id):
    row = connection.execute("SELECT data FROM validation_batches WHERE id=%s", (batch_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown validation batch")
    return {**row[0], "batch_id": batch_id}


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--run-id", type=int, required=True)
    prepare_parser.add_argument("--below", type=int, default=50)
    prepare_parser.add_argument("--seed", type=int, default=42)
    prepare_parser.add_argument("--output", type=Path, required=True)
    import_parser = commands.add_parser("import")
    import_parser.add_argument("file", type=Path)
    import_parser.add_argument("--reviewer", required=True)
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("--batch", type=int, required=True)
    evaluate_parser.add_argument("--threshold", type=float, required=True)
    evaluate_parser.add_argument("--split", choices=["calibration", "evaluation"], default="evaluation")
    evaluate_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        initialize(connection)
        if args.command == "prepare":
            batch = prepare(connection, args.run_id, args.below, args.seed)
            from review_analyzer.reporting.html import write_validation
            write_validation(batch, args.output)
            result = {"batch_id": batch["batch_id"], "items": len(batch["items"]), "file": str(args.output)}
        elif args.command == "import":
            document = json.loads(args.file.read_text(encoding="utf-8"))
            batch = load_batch(connection, document["batch_id"])
            result = {"inserted": import_annotations(connection, document, batch, args.reviewer)}
        else:
            batch = load_batch(connection, args.batch)
            judgments = load_judgments(connection, batch["case"]["id"])
            result = evaluate(batch, judgments, args.threshold, args.split)
            result["annotation_ids"] = sorted({i for item in batch["items"] if item["split"] == args.split
                for i in judgments.get((item["snapshot_id"], item["change_id"]), {}).get("annotation_ids", [])})
            result["batch_id"] = args.batch
            result["method"] = batch["method"]
            result["evaluation_id"] = connection.execute(
                "INSERT INTO benchmark_evaluations (batch_id,result) VALUES (%s,%s) RETURNING id",
                (args.batch, Jsonb(result))).fetchone()[0]
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
