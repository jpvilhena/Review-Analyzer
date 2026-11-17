import requests
import json

def fetch_reviews(app_id, num_pages=1) -> list:
  ''' Function to get reviews from steam page of a specified game in multiples of 10 '''
  all_reviews = []
  cursor = "*"

  for _ in range(num_pages):
    url = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
    params = {
      "appid": app_id,
      "filter": 1,
      "languages": ["english"],
      "purchase_type": 1,
      "num_per_page": 10,
      "cursor": cursor
    }

    response = requests.get(url, params={"input_json": json.dumps(params)}, timeout=30)
    response.raise_for_status()
    data = response.json()["response"]
    
    if "reviews" not in data:
      break

    reviews = data["reviews"]
    all_reviews.extend(reviews)

    cursor = data.get('cursor')
    if not cursor or not reviews:
      break
  

  return all_reviews


if __name__ == "__main__":
  reviews = fetch_reviews(1000360)
  with open('steam_reviews.json', 'w', encoding='utf-8') as f:
    json.dump(reviews, f, ensure_ascii=False, indent=4)
