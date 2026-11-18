"""Passage retrieval and conservative temporal classification."""
import re
from datetime import datetime, timezone, timedelta
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def timestamp(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def period(review, release_date):
    """Separate later edits from evidence whose wording predates the update."""
    boundary = timestamp(release_date)
    if review["timestamp_created"] < boundary:
        return "edited_after_boundary" if review["timestamp_updated"] >= boundary else "before"
    return "release_day" if review["timestamp_created"] < boundary + 86400 else "after"


def match_reviews(reviews, changes, threshold=0.15):
    """Retrieve candidates, retaining the best passage per review and change."""
    passages = []
    for review in reviews:
        text = re.sub(r"\[/?[^\]]+\]", " ", review["review"])
        passages.extend((str(review["recommendationid"]), s.strip())
                        for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip())
    if not passages:
        return []
    queries = [c["text"] + " " + c["search_terms"] for c in changes]
    matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(
        queries + [p[1] for p in passages])
    scores = cosine_similarity(matrix[len(queries):], matrix[:len(queries)])
    best = {}
    for (review_id, passage), row in zip(passages, scores):
        for change, score in zip(changes, row):
            key = (review_id, change["id"])
            if score >= threshold and (key not in best or score > best[key]["similarity"]):
                best[key] = {"review_id": review_id, "change_id": change["id"],
                             "passage": passage, "similarity": float(score), "validation": "unreviewed"}
    return sorted(best.values(), key=lambda x: x["similarity"], reverse=True)


def summarize(reviews, matches, case):
    """Include empty weeks and explicit denominators for each topic and period."""
    rows = []
    day = datetime.fromisoformat(case["start"]).replace(tzinfo=timezone.utc)
    while day.timestamp() < timestamp(case["end"]):
        lo, hi = int(day.timestamp()), min(int((day + timedelta(days=7)).timestamp()), timestamp(case["end"]))
        for group in ("before", "release_day", "after", "edited_after_boundary"):
            ids = {str(r["recommendationid"]) for r in reviews
                   if lo <= r["timestamp_created"] < hi and period(r, case["release_date"]) == group}
            for change in case["changes"]:
                selected = [m for m in matches if m["review_id"] in ids and m["change_id"] == change["id"]]
                counts = Counter(m.get("sentiment", {}).get("label", "not_analyzed") for m in selected)
                rows.append({"week_start": day.date().isoformat(), "period": group,
                             "topic": change["id"], "reviews": len(ids), "matched_reviews": len(selected),
                             "match_fraction": len(selected) / len(ids) if ids else None,
                             "sentiment_counts": dict(counts)})
        day += timedelta(days=7)
    return rows
