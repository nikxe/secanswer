#!/usr/bin/env bash
# One-command demo: start db -> apply schema -> ingest v1 then v2 -> run evals.
# Assumes Docker + Ollama + Python 3.12 are installed and models are pulled.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Starting database (Postgres + pgvector)"
docker compose up -d db

echo "==> Applying schema"
docker compose exec -T db psql -U secanswer -d secanswer -f - < backend/schema.sql

cd backend

echo "==> Ingesting v1 (1-year retention)"
python -m ingest --file ../data/policy_v1.md --title "Data Retention Policy"

echo "==> Ingesting v2 (7-year retention) — v1 is now superseded"
python -m ingest --file ../data/policy_v2.md --title "Data Retention Policy"

echo "==> Running eval suite"
python ../evals/run_eval.py
