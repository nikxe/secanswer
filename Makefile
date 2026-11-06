.PHONY: test db-up demo

test:          ## run pure unit tests (no DB/Ollama needed)
	cd backend && python -m unittest discover -s tests -v

db-up:         ## start Postgres + pgvector
	docker compose up -d db

demo:          ## db + schema + ingest v1/v2 + eval suite
	./scripts/demo.sh
