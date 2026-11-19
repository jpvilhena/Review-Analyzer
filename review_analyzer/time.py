"""Shared UTC boundaries for collection and historical evidence."""
from datetime import datetime, timezone


def timestamp(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def period(review, release_date):
    """Separate later edits from evidence whose wording predates the update."""
    boundary = timestamp(release_date)
    if review["timestamp_created"] < boundary:
        return "edited_after_boundary" if review["timestamp_updated"] >= boundary else "before"
    return "release_day" if review["timestamp_created"] < boundary + 86400 else "after"
