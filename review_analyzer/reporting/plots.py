"""Standalone research figures for temporal evidence."""
from datetime import datetime


def plot_timeline(report, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from collections import defaultdict
    topics = report["case"]["changes"]
    figure, axes = plt.subplots(len(topics), 2, figsize=(13, 4 * len(topics)), squeeze=False)
    for index, change in enumerate(topics):
        weeks = defaultdict(lambda: {"reviews": 0, "candidates": 0, "confirmed": 0, "reviewed": 0,
                                     "positive": 0, "negative": 0, "neutral": 0, "mixed": 0})
        for row in report["timeline"]:
            if row["topic"] != change["id"] or row["period"] not in ("before", "after"):
                continue
            week = weeks[row["week_start"]]
            week["reviews"] += row["reviews"]
            week["candidates"] += row["matched_reviews"]
            week["confirmed"] += row.get("confirmed_complaints", 0)
            week["reviewed"] += row.get("adjudicated", 0)
            for label in ("positive", "negative", "neutral", "mixed"):
                week[label] += row["sentiment_counts"].get(label, 0)
        dates = [datetime.fromisoformat(w) for w in sorted(weeks)]
        values = [weeks[w] for w in sorted(weeks)]
        missing = float("nan")
        axes[index, 0].plot(dates, [100*w["candidates"]/w["reviews"] if w["reviews"] else missing for w in values], 'o--', label="Retrieved candidates")
        if any(w["reviewed"] for w in values):
            axes[index, 0].plot(dates, [100*w["confirmed"]/w["reviews"] if w["reviews"] and w["reviewed"] else missing for w in values], 's-', label="Validated complaints")
        else:
            axes[index, 0].text(.5, .03, "Human validation pending", transform=axes[index, 0].transAxes,
                                ha="center", fontsize=9, bbox={"facecolor": "white", "alpha": .85, "edgecolor": "none"})
        axes[index, 0].set_ylabel("% of collected reviews")
        sentiments = ("positive", "negative", "neutral", "mixed")
        if any(sum(w[label] for label in sentiments) for w in values):
            for label in sentiments:
                axes[index, 1].plot(dates, [w[label] if sum(w[s] for s in sentiments) else missing for w in values], 'o-', label=label.capitalize())
        else:
            axes[index, 1].text(.5, .5, "Sentiment pending validation and analysis", ha="center",
                                va="center", transform=axes[index, 1].transAxes, fontsize=10)
            axes[index, 1].set_ylim(0, 1)
        axes[index, 1].set_ylabel("Passages with model sentiment\n(human-validated relevant pairs only)")
        for column in range(2):
            axis = axes[index, column]
            for event in report.get("events", [{"date": report["case"]["release_date"], "title": "Patch release"}]):
                axis.axvline(datetime.fromisoformat(event["date"]), color="#754a89", alpha=0.6, linestyle=":", label=event["title"])
            axis.set_title(change["id"].replace("-", " ").title())
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            axis.set_xlim(datetime.fromisoformat(report["case"]["start"]), datetime.fromisoformat(report["case"]["end"]))
            axis.set_ylim(bottom=0)
            axis.tick_params(axis="x", rotation=30)
            axis.grid(alpha=0.2)
            axis.legend(fontsize=8)
    figure.suptitle(f"{report['case']['game']} · topic evidence over time", fontsize=15)
    figure.text(0.02, 0.01, "UTC weekly bins; edited pre-release reviews and release-day reviews excluded. Gaps indicate absent evidence. Candidate matches are not confirmed complaints.", fontsize=8)
    figure.tight_layout(rect=(0, 0.04, 1, 0.95))
    figure.savefig(output, dpi=160)
    plt.close(figure)
