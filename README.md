# Review-Analyzer
AI/ML project for analyzing video game reviews, classifying feedback usefulness, relevance, and expressed emotions.

## Collection with Docker

Add `POSTGRES_PASSWORD` (a URL-safe password) to the existing `.env`, preserving Azure credentials. `.env.example` lists the configuration keys.

```sh
docker compose up -d db
docker compose run --build --rm app 1000360 --pages 10
```

The collector uses the Steamworks GetAppReviews API and stores English reviews in PostgreSQL. Each page contains up to ten reviews. HTTP and response errors abort collection rather than writing partial results.

Distinct source payloads are stored as immutable snapshots, with Steam creation/edit timestamps and an observation timestamp. Repeating identical data creates no duplicate snapshot. Older versions predating collection cannot be recovered. JSON exports remain available through the standalone scraper.

Database data persists in the `postgres_data` volume across container replacement. `docker compose down` retains it; `docker compose down -v` deletes it. Volumes are not backups.

The Azure script remains a separate sentiment prototype and is not part of the collection command. Patch matching and analysis provenance are future modules.
