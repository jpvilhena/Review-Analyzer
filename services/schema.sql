CREATE TABLE IF NOT EXISTS review_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    app_id BIGINT NOT NULL,
    review_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    review_text TEXT NOT NULL,
    language TEXT NOT NULL,
    steam_recommended BOOLEAN NOT NULL,
    UNIQUE (app_id, review_id, fingerprint)
);
-- Existing payloads retain the original source values during migration.
ALTER TABLE review_snapshots ADD COLUMN IF NOT EXISTS review_text TEXT;
ALTER TABLE review_snapshots ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE review_snapshots ADD COLUMN IF NOT EXISTS steam_recommended BOOLEAN;
UPDATE review_snapshots
SET review_text = payload->>'review',
    language = payload->>'language',
    steam_recommended = (payload->>'voted_up')::BOOLEAN
WHERE review_text IS NULL OR language IS NULL OR steam_recommended IS NULL;
ALTER TABLE review_snapshots ALTER COLUMN review_text SET NOT NULL;
ALTER TABLE review_snapshots ALTER COLUMN language SET NOT NULL;
ALTER TABLE review_snapshots ALTER COLUMN steam_recommended SET NOT NULL;
CREATE INDEX IF NOT EXISTS snapshots_timeline_idx ON review_snapshots(app_id, created_at);
CREATE TABLE IF NOT EXISTS collection_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    parameters JSONB NOT NULL,
    coverage JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS patches (
    case_id TEXT PRIMARY KEY,
    definition JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    case_id TEXT NOT NULL REFERENCES patches(case_id),
    report JSONB NOT NULL
);
