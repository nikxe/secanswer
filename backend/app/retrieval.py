"""Version-filtered pgvector retrieval.

The key line is the WHERE clause: `d.is_current = true`. This is what stops the
retriever from returning chunks from superseded document versions, no matter how
close their vectors are to the query.
"""
from __future__ import annotations

from .config import settings
from .db import get_conn
from .embeddings import embed
from .text import vector_literal


def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    k = top_k or settings.retrieval_top_k
    qvec = embed(query)

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT dc.chunk_text,
                   dc.page_number,
                   dc.section_heading,
                   d.title,
                   d.version,
                   d.id AS document_id,
                   dc.id AS chunk_id
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.is_current = true
            ORDER BY dc.embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_literal(qvec), k),
        ).fetchall()

    return [
        {
            "text": r[0],
            "page_number": r[1],
            "section_heading": r[2],
            "title": r[3],
            "version": r[4],
            "document_id": str(r[5]),
            "chunk_id": str(r[6]),
        }
        for r in rows
    ]
