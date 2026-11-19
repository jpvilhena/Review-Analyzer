"""Optional Azure sentiment analysis for retrieved English passages."""
import os
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential


def analyze_passages(matches):
    """Attach document scores and retain per-document errors for reporting."""
    with TextAnalyticsClient(os.environ["AZURE_ENDPOINT"], AzureKeyCredential(os.environ["AZURE_KEY"])) as client:
        for offset in range(0, len(matches), 10):
            batch = matches[offset:offset + 10]
            results = client.analyze_sentiment([m["passage"] for m in batch], language="en",
                                               model_version="latest", disable_service_logs=True)
            for match, result in zip(batch, results):
                match["sentiment"] = ({"label": "error", "code": result.error.code} if result.is_error else
                    {"label": result.sentiment, "scores": {key: getattr(result.confidence_scores, key)
                     for key in ("positive", "neutral", "negative")}})
