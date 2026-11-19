"""PostgreSQL storage for immutable source snapshots."""
import hashlib
import json
from pathlib import Path
from psycopg.types.json import Jsonb


def initialize(connection):
    """Apply the additive schema without replacing source data."""
    connection.execute(Path(__file__).with_name("schema.sql").read_text())


def save_reviews(connection, app_id, reviews):
    """Persist each distinct payload without replacing earlier observations."""
    initialize(connection)
    for review in reviews:
        fingerprint = hashlib.sha256(json.dumps(review, sort_keys=True).encode()).hexdigest()
        connection.execute(
            """INSERT INTO review_snapshots
            (app_id, review_id, fingerprint, created_at, updated_at, payload,
             review_text, language, steam_recommended)
            VALUES (%s, %s, %s, to_timestamp(%s), to_timestamp(%s), %s, %s, %s, %s)
            ON CONFLICT (app_id, review_id, fingerprint) DO NOTHING""",
            (app_id, str(review["recommendationid"]), fingerprint,
             review["timestamp_created"], review["timestamp_updated"], Jsonb(review),
             review["review"], review["language"], review["voted_up"]),
        )
