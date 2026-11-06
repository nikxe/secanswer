"""CLI entrypoint for document ingestion.

Run from the backend/ directory:

    python -m ingest --file ../data/policy_v1.md --title "Data Retention Policy"
"""
import argparse

from app.ingestion import ingest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to a PDF or Markdown file")
    parser.add_argument("--title", required=True, help="Human-readable document title")
    args = parser.parse_args()
    try:
        ingest(args.file, args.title)
    except ValueError as e:
        print(e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
