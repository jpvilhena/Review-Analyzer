import os
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential


client = TextAnalyticsClient(
    endpoint=os.getenv("AZURE_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_KEY"))
)

reviews = [
    "WHY IS IT SOO HARRDD?\nits a good game but why is it so hard",
    "Fun fighting mechanics. Not a lot of content but what is there looks promising and makes me want the developer to further the storylines.",
    "Peak of combat"
]

resultados = client.analyze_sentiment(
    reviews,
    language="en",
    show_opinion_mining=True
)

for review, resultado in zip(reviews, resultados):
    if resultado.is_error:
        print("Analysis failed:", resultado.error)
        continue

    print("Review:", review)
    print("Sentiment:", resultado.sentiment)
    print("Scores:", resultado.confidence_scores)
    print()