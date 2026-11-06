"""LangGraph workflow: retrieve -> generate -> save.

The save node is idempotent: it uses a deterministic run_id (derived from the
thread + question) and `INSERT ... ON CONFLICT DO NOTHING`. A retry of the same
question therefore cannot create a duplicate row, even if the previous attempt
timed out after the DB had already committed.

Each node is traced (OpenTelemetry) so a failed tool call is visible.
"""
import json
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .db import get_conn
from .llm import generate
from .retrieval import retrieve
from .text import build_context, make_run_id
from .tracing import traced

logger = logging.getLogger("secanswer")

SYSTEM_PROMPT = (
    "You answer security-questionnaire questions using ONLY the document excerpts "
    "provided below. For every claim, cite the source as [source: N] where N is the "
    "excerpt number. Never invent page numbers or facts. If the excerpts do not "
    "contain the answer, say so explicitly."
)


class State(TypedDict):
    question: str
    thread_id: str
    run_id: str
    context: str
    citations: list
    answer: str


def retrieve_node(state: State) -> dict:
    with traced("retrieve", question=state["question"]):
        chunks = retrieve(state["question"])
        context, citations = build_context(chunks)
    return {"context": context, "citations": citations}


def generate_node(state: State) -> dict:
    with traced("generate"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Question: {state['question']}\n\nSources:\n{state['context']}",
            },
        ]
        answer = generate(messages)
    return {"answer": answer}


def save_node(state: State) -> dict:
    with traced("save", run_id=state["run_id"]):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO saved_answers (run_id, question, answer, citations)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (run_id) DO NOTHING
                """,
                (
                    state["run_id"],
                    state["question"],
                    state["answer"],
                    json.dumps(state["citations"]),
                ),
            )
    logger.info("saved answer run_id=%s", state["run_id"])
    return {}


def _build_graph():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_node("save", save_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "save")
    g.add_edge("save", END)
    return g.compile()


def run(question: str, thread_id: str = "default") -> dict:
    # Deterministic idempotency key: same thread + question -> same run_id,
    # so a retry is deduplicated at the database layer.
    run_id = make_run_id(thread_id, question)

    graph = _build_graph()
    # One root span so retrieve/generate/save become a proper trace tree.
    with traced("workflow", question=question, thread_id=thread_id, run_id=run_id):
        return graph.invoke(
            {
                "question": question,
                "thread_id": thread_id,
                "run_id": run_id,
                "context": "",
                "citations": [],
                "answer": "",
            }
        )
