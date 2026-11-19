"""Append-only annotation history with explicit reviewer disagreement."""
from psycopg.rows import dict_row
from review_analyzer.validation.batches import resolve_annotations, validate_import


def load_judgments(connection, case_id):
    with connection.cursor(row_factory=dict_row) as cursor:
        rows = cursor.execute("SELECT * FROM review_annotations WHERE case_id=%s ORDER BY id",
                              (case_id,)).fetchall()
    return resolve_annotations(rows)


def import_annotations(connection, document, batch, reviewer):
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("Reviewer identity is required")
    accepted = validate_import(document, batch)
    inserted = 0
    for row in accepted:
        item = row["item"]
        previous = connection.execute(
            """SELECT label, sentiment, rationale FROM review_annotations
            WHERE case_id=%s AND snapshot_id=%s AND change_id=%s AND reviewer=%s
            ORDER BY id DESC LIMIT 1""",
            (batch["case"]["id"], item["snapshot_id"], item["change_id"], reviewer)).fetchone()
        values = (row["label"], row["sentiment"], row["rationale"])
        if previous == values:
            continue
        connection.execute(
            """INSERT INTO review_annotations
            (batch_id, case_id, snapshot_id, change_id, reviewer, label, sentiment, rationale)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (batch["batch_id"], batch["case"]["id"], item["snapshot_id"], item["change_id"], reviewer, *values))
        inserted += 1
    return inserted
