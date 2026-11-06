"""OpenTelemetry tracing with a Postgres-backed exporter.

Each LangGraph node (retrieve / generate / save) emits a span with timing and
attributes; errors mark the span status so a failed tool call is visible. Spans
are written to the `traces` table so the system keeps a single datastore (no
Docker, no vendor account). Swap in an OTLP exporter later to ship the same
spans to Langfuse/Jaeger/any collector in the cloud phase.
"""
from __future__ import annotations

import json
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode

from .db import get_conn

SERVICE_NAME = "secanswer"


def _hex(value: int, width: int) -> str:
    return format(value, f"0{width}x")


class PostgresSpanExporter(SpanExporter):
    def export(self, spans):
        try:
            with get_conn() as conn:
                for span in spans:
                    ctx = span.get_span_context()
                    parent = span.parent
                    duration_ms = (
                        (span.end_time - span.start_time) / 1e6
                        if span.end_time and span.start_time
                        else None
                    )
                    conn.execute(
                        """
                        INSERT INTO traces
                            (span_id, trace_id, parent_span_id, name,
                             start_time_ns, duration_ms, status, attributes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (span_id) DO NOTHING
                        """,
                        (
                            _hex(ctx.span_id, 16),
                            _hex(ctx.trace_id, 32),
                            _hex(parent.span_id, 16) if parent else None,
                            span.name,
                            span.start_time,
                            duration_ms,
                            "error" if span.status.status_code == StatusCode.ERROR else "ok",
                            json.dumps(dict(span.attributes) if span.attributes else {}),
                        ),
                    )
        except Exception as exc:  # tracing must never break the application
            print(f"[tracing] export failed: {exc}")
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def _setup_tracing():
    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
    provider.add_span_processor(SimpleSpanProcessor(PostgresSpanExporter()))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME)


tracer = _setup_tracing()


@contextmanager
def traced(name: str, **attrs):
    """Start a span for a unit of work; mark it error and re-raise on failure."""
    with tracer.start_as_current_span(name) as span:
        for key, value in attrs.items():
            span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error", str(exc))
            raise
