"""Weekly topic summaries with explicit evidence denominators."""
from collections import Counter
from datetime import datetime, timezone, timedelta
from review_analyzer.time import timestamp, period


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
                confirmed = [m for m in selected if m.get("validation") == "complaint_request"]
                relevant = [m for m in selected if m.get("validation") in
                            ("complaint_request", "praise", "neutral_mention")]
                candidates = [m for m in selected if m.get("selected_by_model", True)]
                adjudicated = sum(m.get("validation") in
                                  ("complaint_request", "praise", "neutral_mention", "unrelated") for m in selected)
                counts = Counter(m.get("sentiment", {}).get("label", "not_analyzed") for m in relevant)
                rows.append({"week_start": day.date().isoformat(), "period": group,
                             "topic": change["id"], "reviews": len(ids), "matched_reviews": len(candidates),
                             "match_fraction": len(candidates) / len(ids) if ids else None,
                             "confirmed_complaints": len(confirmed),
                             "confirmed_complaint_fraction": len(confirmed) / len(ids) if ids and adjudicated else None,
                             "adjudicated": adjudicated,
                             "validated_relevant": len(relevant),
                             "unreviewed": sum(m.get("validation", "unreviewed") == "unreviewed" for m in selected),
                             "sentiment_counts": dict(counts)})
        day += timedelta(days=7)
    return rows
