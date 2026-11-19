"""Human judgments remain separate from automated retrieval and sentiment."""
import hashlib
import random
from collections import defaultdict

LABELS = ("complaint_request", "praise", "neutral_mention", "unrelated", "uncertain")
RELEVANT = {"complaint_request", "praise", "neutral_mention"}
SENTIMENTS = ("positive", "negative", "neutral", "mixed", "uncertain")


def item_key(snapshot_id, change_id):
    return f"{snapshot_id}:{change_id}"


def make_batch(report, scored, snapshots, below=50, seed=42):
    """Freeze all retrieved pairs and a reproducible sample below the threshold."""
    if below < 0:
        raise ValueError("Below-threshold sample size cannot be negative")
    threshold = report["threshold"]
    above = [m for m in scored if m["similarity"] >= threshold]
    pool = [m for m in scored if m["similarity"] < threshold]
    rng = random.Random(seed)
    sampled = rng.sample(pool, min(below, len(pool)))
    changes = {c["id"]: c for c in report["case"]["changes"]}
    items = []
    for match in above + sampled:
        snapshot_id, review = snapshots[match["review_id"]]
        # Both topics for the same review stay in the same split.
        split_hash = hashlib.sha256(f"{seed}:{match['review_id']}".encode()).digest()[0]
        items.append({**match, "key": item_key(snapshot_id, match["change_id"]),
                      "snapshot_id": snapshot_id, "review_text": review["review"],
                      "created_at": review["timestamp_created"], "updated_at": review["timestamp_updated"],
                      "patch_text": changes[match["change_id"]]["text"],
                      "split": "calibration" if split_hash < 128 else "evaluation",
                      "stratum": "retrieved" if match["similarity"] >= threshold else "below_threshold",
                      "source": f"https://steamcommunity.com/profiles/{review['author']['steamid']}/recommended/{report['case']['app_id']}/"})
    rng.shuffle(items)
    return {"case": report["case"], "method": report["method"], "seed": seed,
            "threshold": threshold, "items": items, "retrieved_population": len(above),
            "below_population": len(pool), "below_sample": len(sampled)}


def validate_import(document, batch):
    """Validate the entire submission before any database writes occur."""
    if document.get("batch_id") != batch["batch_id"]:
        raise ValueError("Annotation file belongs to a different batch")
    known = {item["key"]: item for item in batch["items"]}
    accepted, seen = [], set()
    for row in document.get("annotations", []):
        key = row.get("key")
        if key not in known or key in seen:
            raise ValueError(f"Unknown or duplicate annotation key: {key}")
        seen.add(key)
        label = row.get("label", "")
        if not label:
            continue
        if label not in LABELS:
            raise ValueError(f"Invalid label for {key}")
        sentiment = row.get("sentiment") or None
        if sentiment is not None and sentiment not in SENTIMENTS:
            raise ValueError(f"Invalid sentiment for {key}")
        rationale = row.get("rationale", "").strip()
        if not rationale:
            raise ValueError(f"A rationale is required for {key}")
        accepted.append({"item": known[key], "label": label,
                         "sentiment": sentiment, "rationale": rationale})
    return accepted


def resolve_annotations(rows):
    """Use each reviewer's latest judgment; disagreement remains explicit."""
    latest = {}
    for row in sorted(rows, key=lambda r: r["id"]):
        key = (row["snapshot_id"], row["change_id"], row["reviewer"])
        latest[key] = row
    grouped = defaultdict(list)
    for (snapshot_id, change_id, _), row in latest.items():
        grouped[(snapshot_id, change_id)].append(row)
    resolved = {}
    for key, judgments in grouped.items():
        labels = {r["label"] for r in judgments}
        sentiments = {r["sentiment"] for r in judgments if r.get("sentiment")}
        resolved[key] = {"validation": next(iter(labels)) if len(labels) == 1 else "disputed",
                         "human_sentiment": next(iter(sentiments)) if len(sentiments) == 1 else None,
                         "annotation_ids": [r["id"] for r in judgments]}
    return resolved
