"""Document ingestion: parse -> chunk -> embed -> versioned upsert.

Used by both the CLI (`python -m ingest`) and the web upload endpoint.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .db import get_conn
from .embeddings import embed_many
from .text import chunk_words, section_heading, slugify


def _chunks_from_pdf(path: str) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    chunks: list[dict] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        chunks.extend(chunk_words(text.split(), i + 1, section_heading(text)))
    return chunks


def _chunks_from_markdown(path: str) -> list[dict]:
    """Split Markdown into chunks on heading boundaries; each chunk records the
    heading it belongs to (used as the citation's section)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    chunks: list[dict] = []
    current_section = None
    buf: list[str] = []

    def flush():
        if buf:
            body = " ".join(buf)
            chunks.extend(chunk_words(body.split(), None, current_section))
            buf.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            current_section = stripped.lstrip("#").strip()
        elif stripped:
            buf.append(stripped)
    flush()
    return chunks


def load_chunks(path: str) -> list[dict]:
    if Path(path).suffix.lower() == ".pdf":
        return _chunks_from_pdf(path)
    return _chunks_from_markdown(path)


def ingest(path: str, title: str) -> int:
    """Ingest a PDF/Markdown file as a new document version. Re-ingesting with
    the same title supersedes the previous version."""
    doc_key = slugify(title)
    all_chunks = load_chunks(path)

    if not all_chunks:
        raise ValueError("No text extracted — is this a scanned PDF? (OCR is out of scope)")

    embeddings = embed_many([c["text"] for c in all_chunks])

    conn = get_conn()
    conn.autocommit = False  # one transaction: retire old version + insert new
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) FROM documents WHERE doc_key = %s",
                (doc_key,),
            )
            next_version = cur.fetchone()[0] + 1

            cur.execute(
                "UPDATE documents SET is_current = false WHERE doc_key = %s AND is_current = true",
                (doc_key,),
            )

            cur.execute(
                """
                INSERT INTO documents (doc_key, title, version, is_current, file_path)
                VALUES (%s, %s, %s, true, %s)
                RETURNING id
                """,
                (doc_key, title, next_version, path),
            )
            document_id = cur.fetchone()[0]

            for i, (chunk, emb) in enumerate(zip(all_chunks, embeddings)):
                chunk_uid = hashlib.sha256(
                    f"{doc_key}:{next_version}:{i}:{chunk['text']}".encode()
                ).hexdigest()[:32]
                cur.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, version, chunk_index, page_number,
                         section_heading, chunk_text, embedding, chunk_uid)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_uid) DO NOTHING
                    """,
                    (
                        document_id,
                        next_version,
                        i,
                        chunk["page_number"],
                        chunk["section_heading"],
                        chunk["text"],
                        "[" + ",".join(str(x) for x in emb) + "]",
                        chunk_uid,
                    ),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return len(all_chunks)
