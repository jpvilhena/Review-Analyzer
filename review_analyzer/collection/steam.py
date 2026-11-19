import requests
import json

def fetch_reviews(app_id, num_pages=1, *, language="english", start=None, end=None,
                  page_size=100, metadata=None) -> list:
  """Collect unique reviews in a half-open UTC interval and record page coverage."""
  all_reviews = []
  if app_id <= 0 or num_pages <= 0 or not 1 <= page_size <= 100:
    raise ValueError("Invalid app ID, page limit or page size")
  if (start is None) != (end is None) or (start is not None and start >= end):
    raise ValueError("Both bounds are required, with start before end")
  cursor = "*"

  for _ in range(num_pages):
    url = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
    params = {
      "appid": app_id,
      "filter": 1,
      "languages": [language],
      "purchase_type": 1,
      "num_per_page": page_size,
      "cursor": cursor
    }

    if start is not None:
      params.update(date_range_start=start, date_range_end=end - 1)
    response = requests.get(url, params={"input_json": json.dumps(params)}, timeout=30)
    response.raise_for_status()
    data = response.json()["response"]
    
    # Steam omits the repeated reviews field when a page is empty.
    if "reviews" not in data and data.get("query_summary", {}).get("num_reviews") != 0:
      raise ValueError("Steam response is missing reviews")

    reviews = data.get("reviews", [])
    all_reviews.extend(reviews)

    next_cursor = data.get('cursor')
    if metadata is not None:
      metadata.update(pages=_ + 1, exhausted=not reviews, total_matching=data.get("total_matching"))
    if not next_cursor or not reviews or next_cursor == cursor:
      break
    cursor = next_cursor
  

  return list({str(r["recommendationid"]): r for r in all_reviews}.values())
