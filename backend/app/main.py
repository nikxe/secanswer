"""FastAPI entrypoint."""
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from .db import get_conn
from .graph import run
from .ingestion import ingest as ingest_document
from .questionnaire import answer_questionnaire, to_csv

app = FastAPI(title="SecAnswer", version="0.2.0")

# Dev only: allow the Next.js frontend (localhost:3000) to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    thread_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    citations: list
    run_id: str


class QuestionnaireRequest(BaseModel):
    questions: list[str]
    thread_id: str = "questionnaire"


class ReviewRequest(BaseModel):
    answer: str | None = None
    status: str = "reviewed"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = run(req.question, req.thread_id)
    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        run_id=result["run_id"],
    )


@app.post("/documents/upload")
async def upload_document(title: str = Form(...), file: UploadFile = File(...)):
    """Upload a PDF/Markdown file and ingest it (versioned, current-version wins)."""
    suffix = Path(file.filename or "doc.md").suffix or ".md"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        n = ingest_document(tmp_path, title)
        return {"title": title, "chunks": n, "status": "ingested"}
    finally:
        os.unlink(tmp_path)


@app.post("/questionnaire")
def questionnaire(req: QuestionnaireRequest):
    """Draft a cited answer for every question in a questionnaire."""
    results = answer_questionnaire(req.questions, req.thread_id)
    return {"results": results}


@app.post("/questionnaire/export")
def questionnaire_export(req: QuestionnaireRequest):
    """Draft every question and return a CSV (idempotent: re-running won't dupe)."""
    results = answer_questionnaire(req.questions, req.thread_id)
    return PlainTextResponse(to_csv(results), media_type="text/csv")


@app.get("/answers")
def list_answers(limit: int = 50):
    """List saved answers for review."""
    cols = ["run_id", "question", "answer", "status", "citations", "created_at"]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT run_id, question, answer, status, citations, created_at "
            "FROM saved_answers ORDER BY created_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return {"answers": [dict(zip(cols, r)) for r in rows]}


@app.post("/answers/{run_id}/review")
def review_answer(run_id: str, req: ReviewRequest):
    """Mark an answer reviewed (optionally storing an edited version)."""
    with get_conn() as conn:
        row = conn.execute(
            "UPDATE saved_answers SET status = %s, answer = COALESCE(%s, answer) "
            "WHERE run_id = %s RETURNING run_id, status",
            (req.status, req.answer, run_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="answer not found")
    return {"run_id": row[0], "status": row[1]}


_TRACE_COLS = [
    "span_id",
    "trace_id",
    "parent_span_id",
    "name",
    "start_time_ns",
    "duration_ms",
    "status",
    "attributes",
]


@app.get("/traces")
def list_traces(limit: int = 20):
    """Return the most recent spans — observability without extra infra."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT span_id, trace_id, parent_span_id, name, start_time_ns, "
            "duration_ms, status, attributes "
            "FROM traces ORDER BY start_time_ns DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return {"traces": [dict(zip(_TRACE_COLS, r)) for r in rows]}
