CREATE TABLE IF NOT EXISTS review_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    app_id BIGINT NOT NULL,
    review_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    UNIQUE (app_id, review_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS snapshots_timeline_idx ON review_snapshots(app_id, created_at);
