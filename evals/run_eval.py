"""Eval harness: proves the craft items against a small fixture corpus.

Requires: DB running + schema applied + Ollama running + corpus ingested
(see scripts/demo.sh for the one-command path).

Run from the repo root (or backend/):

    python evals/run_eval.py

Asserts:
  1. Retrieval returns ONLY current-version chunks (the stale-doc fix).
  2. The generated answer reflects the current version (soft check; answer
     printed for human inspection).
  3. Idempotent save: run twice -> exactly one saved_answers row (the
     duplicate-write fix).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import get_conn  # noqa: E402
from app.graph import run as run_workflow  # noqa: E402
from app.retrieval import retrieve  # noqa: E402


def load_questions() -> list[dict]:
    with open(Path(__file__).parent / "questions.json") as f:
        return json.load(f)


def test_version_filtering(questions: list[dict]) -> int:
    print("\n[1] Version filtering — retrieval must return the CURRENT version")
    failures = 0
    for q in questions:
        chunks = retrieve(q["question"])
        if not chunks:
            print(f"  FAIL (no results): '{q['question']}'")
            failures += 1
            continue
        top = chunks[0]
        ok = top["version"] == q["expect_version"] and top["title"] == q["title"]
        failures += 0 if ok else 1
        print(
            f"  {'PASS' if ok else 'FAIL'}: '{q['question']}' -> "
            f"{top['title']} v{top['version']} (expected v{q['expect_version']})"
        )
    return failures


def test_answer_grounding(questions: list[dict]) -> int:
    print("\n[2] Answer grounding — answer reflects the current version (soft check)")
    failures = 0
    for q in questions:
        result = run_workflow(q["question"], thread_id="eval")
        answer = result["answer"]
        needles = q.get("answer_needles", [])
        ok = any(n.lower() in answer.lower() for n in needles)
        failures += 0 if ok else 1
        print(f"  {'PASS' if ok else 'FAIL'}: '{q['question']}'")
        print(f"       answer: {answer[:160]}")
    return failures


def test_idempotent_save() -> int:
    print("\n[3] Idempotent save — two runs must produce ONE row")
    question = "What is our data retention period?"
    thread = "eval-idempotency"
    run_id = hashlib.sha256(f"{thread}:{question}".encode()).hexdigest()

    run_workflow(question, thread_id=thread)
    run_workflow(question, thread_id=thread)  # simulate a retry after a timeout

    with get_conn() as conn:
        n = conn.execute(
            "SELECT count(*) FROM saved_answers WHERE run_id = %s", (run_id,)
        ).fetchone()[0]
    ok = n == 1
    print(f"  {'PASS' if ok else 'FAIL'}: run twice -> {n} row(s) for run_id (expected 1)")
    return 0 if ok else 1


def main() -> None:
    questions = load_questions()
    failures = 0
    failures += test_version_filtering(questions)
    failures += test_answer_grounding(questions)
    failures += test_idempotent_save()
    print("\n" + ("ALL PASS" if failures == 0 else f"{failures} FAILURE(S)"))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
