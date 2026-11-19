"""Versioned TF-IDF passage retrieval for patch topics."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


METHOD = "tfidf-search-terms-v2"
LEGACY_METHOD = "tfidf-word-unigram-bigram-cosine-v1"


def match_reviews(reviews, changes, threshold=0.15, method=METHOD):
    """Retrieve candidates, retaining the best passage per review and change."""
    passages = []
    for review in reviews:
        text = re.sub(r"\[/?[^\]]+\]", " ", review["review"])
        passages.extend((str(review["recommendationid"]), s.strip())
                        for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip())
    if not passages:
        return []
    if method not in (METHOD, LEGACY_METHOD):
        raise ValueError(f"Unsupported matching method: {method}")
    # Curated topic terms avoid matching generic changelog wording such as 'different types'.
    queries = [c["search_terms"] if method == METHOD else
               c["text"] + " " + c["search_terms"] for c in changes]
    matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(
        queries + [p[1] for p in passages])
    scores = cosine_similarity(matrix[len(queries):], matrix[:len(queries)])
    best = {}
    for (review_id, passage), row in zip(passages, scores):
        for change, score in zip(changes, row):
            key = (review_id, change["id"])
            if score >= threshold and (key not in best or score > best[key]["similarity"]):
                best[key] = {"review_id": review_id, "change_id": change["id"],
                             "passage": passage, "similarity": float(score), "validation": "unreviewed"}
    return sorted(best.values(), key=lambda x: x["similarity"], reverse=True)
