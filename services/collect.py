"""Collect reviews and commit them in a single database transaction."""
import argparse
import os
import psycopg
from dotenv import load_dotenv
from services.database import save_reviews
from services.steam_scraper import fetch_reviews


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_id", type=int)
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args()
    if args.app_id <= 0 or args.pages <= 0:
        parser.error("App ID and pages must be positive")
    reviews = fetch_reviews(args.app_id, args.pages)
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        save_reviews(connection, args.app_id, reviews)
    print(f"Processed {len(reviews)} reviews")


if __name__ == "__main__":
    main()
