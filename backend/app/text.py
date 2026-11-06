"""Pure, dependency-free helpers.

These functions do no I/O and import nothing but the standard library, so they
can be unit-tested with zero setup (no DB, no model runtime). The retrieval,
graph, and ingestion modules delegate to them so the tricky logic lives in one
testable place.
"""
from __future__ import annotations

import hashlib
import re


def slugify(title: str) -> str:
    """Stable document key from a human-readable title."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def section_heading(text: str) -> str | None:
    """Best-effort section heading detection (lightweight heuristic).

    Matches numbered headings like '3.2 Data Retention' or short ALL-CAPS lines.
    pypdf exposes no heading structure, so this is deliberately a heuristic; a
    production PDF pipeline should use a layout-aware parser."""
    for line in text.splitlines()[:40]:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+(\.\d+)*\s+\S", line) and len(line) < 80:
            return line
        if line.isupper() and 3 < len(line) < 80:
            return line
    return None


def chunk_words(
    words: list[str],
    page_number,
    section,
    size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """Split a word list into fixed-size chunks with overlap, recording the
    page/section each chunk came from (captured metadata, never derived)."""
    chunks: list[dict] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        if chunk.strip():
            chunks.append(
                {"text": chunk, "page_number": page_number, "section_heading": section}
            )
        i += size - overlap
    return chunks


def vector_literal(vec: list[float]) -> str:
    """pgvector accepts a comma-separated list in brackets."""
    return "[" + ",".join(str(x) for x in vec) + "]"


def make_run_id(thread_id: str, question: str) -> str:
    """Deterministic idempotency key: same thread + question -> same run_id.

    This is what lets a retry be deduplicated at the database layer."""
    return hashlib.sha256(f"{thread_id}:{question}".encode()).hexdigest()


def build_context(chunks: list[dict]) -> tuple[str, list[dict]]:
    """Turn retrieved chunks into (prompt text, citation metadata).

    Page/section come from the chunk METADATA — the model only sees captured
    values and is never asked to invent them."""
    parts: list[str] = []
    citations: list[dict] = []
    for i, c in enumerate(chunks):
        section = c["section_heading"] or "n/a"
        page = c["page_number"] if c["page_number"] is not None else "n/a"
        parts.append(
            f"[{i + 1}] (from \"{c['title']}\" v{c['version']}, "
            f"section \"{section}\", page {page})\n{c['text']}"
        )
        citations.append(
            {
                "index": i + 1,
                "title": c["title"],
                "version": c["version"],
                "page": c["page_number"],
                "section": c["section_heading"],
                "chunk_id": c["chunk_id"],
            }
        )
    return "\n\n".join(parts), citations
