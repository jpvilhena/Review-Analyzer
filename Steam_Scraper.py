import requests
import json
import re
import string

def fetch_reviews(app_id, num_pages=1) -> list:
  ''' Function to get reviews from steam page of a specified game in multiples of 10 '''
  all_reviews = []
  cursor = "*"

  for _ in range(num_pages):
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    params = {
      "json": 1,
      "filter": "recent",
      "language": "english",
      "num_per_page": 10,
      "cursor": cursor
    }

    response = requests.get(url, params=params)
    data = response.json()
    
    if "reviews" not in data:
      break

    reviews = data["reviews"]
    all_reviews.extend(reviews)

    cursor = data.get('cursor')
    if not cursor:
      break
  

  return all_reviews


reviews = fetch_reviews(730)

with open('steam_reviews.json', 'w', encoding='utf-8') as f:
  json.dump(reviews, f, ensure_ascii=False, indent=4)