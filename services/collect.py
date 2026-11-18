"""Collect reviews and commit them in a single database transaction."""
import argparse
import os
import psycopg
from dotenv import load_dotenv
from services.database import save_reviews
from services.steam_scraper import fetch_reviews
from services.matching import timestamp


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_id", type=int)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--language", default="english")
    parser.add_argument("--start", help="Inclusive UTC date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Exclusive UTC date (YYYY-MM-DD)")
    args = parser.parse_args()
    if args.app_id <= 0 or args.pages <= 0:
        parser.error("App ID and pages must be positive")
    reviews = fetch_reviews(args.app_id, args.pages, language=args.language,
                            start=timestamp(args.start) if args.start else None,
                            end=timestamp(args.end) if args.end else None)
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        save_reviews(connection, args.app_id, reviews)
    print(f"Processed {len(reviews)} reviews")


if __name__ == "__main__":
    main()
