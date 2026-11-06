-- ---------------------------------------------------------------------------
-- SecAnswer schema: versioned documents + pgvector chunks + idempotent answers
-- Run once against the Postgres database (docker compose up db, then apply).
-- ---------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector;

-- One row per document VERSION. `doc_key` is the stable identity (slug of the
-- title); `version` increments on re-ingest; only one version is current.
CREATE TABLE IF NOT EXISTS documents (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key      text NOT NULL,
    title        text NOT NULL,
    version      integer NOT NULL DEFAULT 1,
    is_current   boolean NOT NULL DEFAULT true,
    effective_at timestamptz,
    file_path    text,
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- Enforce at most ONE current version per document, in the database itself.
CREATE UNIQUE INDEX IF NOT EXISTS one_current_version_per_doc
    ON documents (doc_key)
    WHERE is_current;

-- Searchable chunks. `page_number` / `section_heading` are captured from the
-- parser, never derived from chunk_index. `chunk_uid` makes re-indexing
-- idempotent (same text -> same uid -> safe upsert).
CREATE TABLE IF NOT EXISTS document_chunks (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id    uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version        integer NOT NULL,
    chunk_index    integer NOT NULL,
    page_number    integer,
    section_heading text,
    chunk_text     text NOT NULL,
    embedding      vector(768),
    chunk_uid      text NOT NULL UNIQUE,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- Cosine similarity index for pgvector.
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON document_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS chunks_document_idx
    ON document_chunks (document_id, version);

-- Answers produced by the agent. `run_id` is the idempotency key: the unique
-- constraint is the real guard against duplicate writes on retry.
CREATE TABLE IF NOT EXISTS saved_answers (
    id         bigserial PRIMARY KEY,
    run_id     text NOT NULL UNIQUE,
    question   text NOT NULL,
    answer     text NOT NULL,
    citations  jsonb,
    status     text NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- OpenTelemetry spans, persisted so the whole system keeps a single datastore.
-- Lets us answer "why did a tool call fail?" without extra infrastructure.
CREATE TABLE IF NOT EXISTS traces (
    id             bigserial PRIMARY KEY,
    span_id        text NOT NULL UNIQUE,
    trace_id       text NOT NULL,
    parent_span_id text,
    name           text NOT NULL,
    start_time_ns  bigint NOT NULL,
    duration_ms    double precision,
    status         text NOT NULL,
    attributes     jsonb,
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS traces_trace_id_idx ON traces (trace_id);
