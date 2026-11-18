# Review-Analyzer
AI/ML project for analyzing video game reviews, classifying feedback usefulness, relevance, and expressed emotions.

## Collection with Docker

Add `POSTGRES_PASSWORD` (a URL-safe password) to the existing `.env`, preserving Azure credentials. `.env.example` lists the configuration keys.

```sh
docker compose up -d db
docker compose run --build --rm app 1000360 --pages 10
```

The collector uses the Steamworks GetAppReviews API and stores English reviews in PostgreSQL. Each page contains up to 100 reviews. HTTP and response errors abort collection rather than writing partial results.

Distinct source payloads are stored as immutable snapshots, with Steam creation/edit timestamps and an observation timestamp. Repeating identical data creates no duplicate snapshot. Older versions predating collection cannot be recovered. JSON exports remain available through the standalone scraper.

Snapshots expose `review_text`, `language`, and `steam_recommended` as required columns for SQL queries and analysis. The complete source response remains in `payload`. Schema initialization backfills existing rows transactionally without deleting snapshots or changing their IDs. `steam_recommended` is the Steam recommendation flag, not predicted sentiment.

Database data persists in the `postgres_data` volume across container replacement. `docker compose down` retains it; `docker compose down -v` deletes it. Volumes are not backups.

## DREDGE pilot

The curated v1.1.0 case covers hidden quest timers and map markers. Source links, original change text, expanded retrieval terms and UTC date boundaries are in `services/cases.py`. The collection window is March 30 through June 10, 2023, inclusive. The May 11 release day is separated because the exact release time is not asserted.

```sh
docker compose build app
docker compose run --rm --entrypoint python app -m unittest discover -s tests
docker compose run --rm --entrypoint python app -m services.pilot collect --pages 100
docker compose run --rm --entrypoint python app -m services.pilot analyze --output output/dredge.json
```

The page limit applies separately before and after release. Collection runs record the parameters and whether an empty page confirmed exhaustion. A page limit can produce an incomplete sample. Analysis uses the latest observed snapshot per review, stores its exact snapshot IDs and persists the report in PostgreSQL. Source payloads remain in the database; exports are optional and ignored by Git.

TF-IDF cosine similarity ranks the best passage per review/change. The default 0.15 threshold is exploratory and requires calibration against manually labeled examples. Matches remain `unreviewed`; relevant praise and requests can both match. Similarity is neither a probability nor evidence of causation. Reviews edited after the patch boundary are explicitly separated from pre-update evidence.

Weekly summaries include counts, matching-review fractions and empty weeks. Sentiment is absent unless requested; Steam recommendation flags are preserved separately and never treated as model sentiment.

```sh
docker compose run --rm --entrypoint python app -m services.pilot analyze --sentiment --output output/dredge-sentiment.json
```

The optional command submits matched English passages to Azure using the existing credentials. It records individual service errors rather than counting them as neutral. Azure selects its latest model, so the service model is not pinned; exact model reproducibility is not guaranteed. The pilot does not yet include embeddings, an annotation interface or a chart frontend.
