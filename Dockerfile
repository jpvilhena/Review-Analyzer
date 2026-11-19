FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY review_analyzer/ review_analyzer/
COPY tests/ tests/
ENTRYPOINT ["python", "-m", "review_analyzer"]
