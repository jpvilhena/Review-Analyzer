# Review-Analyzer
AI/ML project for analyzing video game reviews, classifying feedback usefulness, relevance, and expressed emotions.

## Collection with Docker

Add `POSTGRES_PASSWORD` (a URL-safe password) to the existing `.env`, preserving Azure credentials. `.env.example` lists the configuration keys.

```sh
docker compose up -d db
docker compose run --build --rm app collect 1000360 --pages 10
```

The collector uses the Steamworks GetAppReviews API and stores English reviews in PostgreSQL. Each page contains up to 100 reviews. HTTP and response errors abort collection rather than writing partial results.

Distinct source payloads are stored as immutable snapshots, with Steam creation/edit timestamps and an observation timestamp. Repeating identical data creates no duplicate snapshot. Older versions predating collection cannot be recovered.

Snapshots expose `review_text`, `language`, and `steam_recommended` as required columns for SQL queries and analysis. The complete source response remains in `payload`. Schema initialization backfills existing rows transactionally without deleting snapshots or changing their IDs. `steam_recommended` is the Steam recommendation flag, not predicted sentiment.

Database data persists in the `postgres_data` volume across container replacement. `docker compose down` retains it; `docker compose down -v` deletes it. Volumes are not backups.

## DREDGE pilot

The curated v1.1.0 case covers hidden quest timers and map markers. Source links, original change text, expanded retrieval terms and UTC date boundaries are in `review_analyzer/cases/dredge.py`. The collection window is March 30 through June 10, 2023, inclusive. The May 11 release day is separated because the exact release time is not asserted.

```sh
docker compose build app
docker compose run --rm --entrypoint python app -m unittest discover -s tests
docker compose run --rm app pilot collect --pages 100
docker compose run --rm app pilot analyze --output output/dredge.json
```

The page limit applies separately before and after release. Collection runs record the parameters and whether an empty page confirmed exhaustion. A page limit can produce an incomplete sample. Analysis uses the latest observed snapshot per review, stores its exact snapshot IDs and persists the report in PostgreSQL. Source payloads remain in the database; exports are optional and ignored by Git.

TF-IDF cosine similarity ranks the best passage per review/change. The default 0.15 threshold is exploratory and requires calibration against manually labeled examples. Matches remain `unreviewed`; relevant praise and requests can both match. Similarity is neither a probability nor evidence of causation. Reviews edited after the patch boundary are explicitly separated from pre-update evidence.

Weekly summaries include counts, matching-review fractions and empty weeks. Sentiment is absent unless requested; Steam recommendation flags are preserved separately and never treated as model sentiment.

```sh
docker compose run --rm app pilot analyze --sentiment --output output/dredge-sentiment.json
```

The optional command submits only human-validated relevant passages to Azure using the existing credentials. No requests are made when no relevant judgments exist. Individual service errors remain separate from neutral sentiment. Azure selects its latest model, so exact service-model reproducibility is not guaranteed. Embedding-based retrieval is not implemented.

## Evidence validation and evaluation

The current matcher uses curated search terms rather than generic patch-note wording. Its method ID is `tfidf-search-terms-v2`; old runs remain unchanged and the legacy method remains available for reproducing their benchmarks. Similarity remains a retrieval signal, not a complaint classifier.

An analysis creates a database run ID. A review batch freezes the run's exact snapshots, retrieves all above-threshold review/topic pairs and samples below-threshold pairs to investigate misses. Calibration and evaluation splits are deterministic by review ID, so both topics from a review stay together.

```sh
docker compose run --rm app pilot analyze --output output/dredge-validated.json --html output/dredge-report.html
docker compose run --rm app review prepare --run-id RUN_ID --below 50 --output output/validation.html
```

`RUN_ID` is the integer printed by analysis. The offline HTML review file opens directly in a browser. It includes the patch change, quoted passage, full review, source and creation/edit dates. Scores and benchmark splits are hidden during labeling. Available topic judgments are complaint/request, praise, neutral mention, unrelated and uncertain. Optional sentiment labels apply to the quoted passage. Each completed judgment requires a rationale. The page can download judgments or load a saved judgment file to resume work.

The downloaded file can be saved under `output/` and imported with an explicit reviewer identity:

```sh
docker compose run --rm app review import output/judgments-BATCH_ID.json --reviewer REVIEWER_NAME
docker compose run --rm app review evaluate --batch BATCH_ID --split calibration --threshold 0.15 --output output/calibration.json
docker compose run --rm app review evaluate --batch BATCH_ID --split evaluation --threshold 0.15 --output output/evaluation.json
```

`BATCH_ID` is the integer returned by preparation. Imports validate the entire file before writing. Duplicate identical imports are skipped; revisions append to the audit history. Each reviewer's latest judgment is used. Disagreement remains `disputed` and is excluded from confirmed counts and evaluation until the reviewers agree. Judgments are tied to exact snapshots and topics, never transferred to edited review text.

Threshold selection belongs to the calibration split. A chosen threshold is then evaluated on the held-out split, without retuning against its results. Precision, recall and F1 describe the labeled, stratified sample only; they are not estimates of population-wide recall. Missing, uncertain and disputed labels are explicitly excluded, and metrics without denominators are null. Each evaluation is persisted with its annotation IDs. A new seed or batch is not a new independent test set if it reuses previously examined reviews.

After annotation, another analysis incorporates the judgments. Confirmed relevant pairs missed by the threshold remain in the evidence report as manually included pairs. The report separates candidates from confirmed complaints and preserves annotation IDs. Sentiment counts include only validated relevant pairs. A requested HTML report also writes an adjacent PNG timeline. Release-day and later-edited pre-release reviews remain excluded from the plotted comparison; missing sentiment is a gap rather than a zero. Confirmed counts depend on annotation coverage, not total complaint prevalence. No labels are generated automatically.

```sh
docker compose run --rm app pilot analyze --sentiment --output output/dredge-validated.json --html output/dredge-report.html
docker compose run --rm -e RUN_DATABASE_TESTS=1 --entrypoint python app -m unittest discover -s tests
```

Database integration tests roll back their synthetic fixtures. The report currently marks the curated v1.1.0 release; additional patch discovery and semantic embeddings remain separate future work.

## Package layout

```text
review_analyzer/
  __main__.py        Command dispatcher (collect, pilot, review)
  cli/               Command-line orchestration
  collection/        Steam API client
  storage/           PostgreSQL repositories and schema
  analysis/          Matching, sentiment and temporal summaries
  validation/        Human judgments, sampling and evaluation
  reporting/         Offline HTML pages and PNG plots
  cases/             Curated study definitions
  time.py            Shared UTC date boundaries
```

Local execution follows the same commands: `python -m review_analyzer collect --help`, `python -m review_analyzer pilot --help`, and `python -m review_analyzer review --help`. Dependencies come from `requirements.txt`. Docker defaults to command help when no command is supplied. The obsolete hardcoded Azure demo and original JSON sample have been removed. The legacy TF-IDF scoring method remains solely for reproducing saved runs.
