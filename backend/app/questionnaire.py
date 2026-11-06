"""Batch questionnaire answering + export.

Turns the single-question chat into the product: paste a list of questionnaire
questions, get a cited draft answer for each, review, then export as CSV.
"""
from __future__ import annotations

import csv
import io

from .graph import run


def answer_questionnaire(questions: list[str], thread_id: str = "questionnaire") -> list[dict]:
    """Draft a cited answer for each question. A per-question failure is recorded
    as `status="error"` instead of aborting the whole batch."""
    results: list[dict] = []
    for q in questions:
        q = q.strip()
        if not q:
            continue
        try:
            r = run(q, thread_id=thread_id)
            results.append(
                {
                    "question": q,
                    "answer": r["answer"],
                    "citations": r["citations"],
                    "run_id": r["run_id"],
                    "status": "draft",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "question": q,
                    "answer": "",
                    "citations": [],
                    "run_id": None,
                    "status": "error",
                    "error": str(exc),
                }
            )
    return results


def to_csv(results: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["question", "answer", "sources"])
    for r in results:
        sources = "; ".join(
            f"{c['title']} v{c['version']} [{c.get('section') or 'n/a'}]"
            for c in r.get("citations", [])
        )
        writer.writerow([r["question"], r["answer"], sources])
    return buf.getvalue()
