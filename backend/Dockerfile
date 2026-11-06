# Backend image: FastAPI + LangGraph + pgvector client.
# Build from the repo root:  docker build -f backend/Dockerfile -t secanswer backend
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ingest.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
