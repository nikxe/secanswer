"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Citation = {
  index: number;
  title: string;
  version: number;
  page: number | null;
  section: string | null;
};

type QResult = {
  question: string;
  answer: string;
  citations: Citation[];
  run_id: string | null;
  status: string;
  error?: string;
};

type Trace = {
  span_id: string;
  name: string;
  status: string;
  duration_ms: number | null;
  attributes: Record<string, string>;
};

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [questionsText, setQuestionsText] = useState("");
  const [results, setResults] = useState<QResult[]>([]);
  const [qLoading, setQLoading] = useState(false);
  const [qError, setQError] = useState("");

  const [traces, setTraces] = useState<Trace[]>([]);

  async function ask() {
    setLoading(true);
    setError("");
    setAnswer("");
    setCitations([]);
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, thread_id: "web" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAnswer(data.answer);
      setCitations(data.citations ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function parseQuestions(): string[] {
    return questionsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function draftAll() {
    const questions = parseQuestions();
    if (questions.length === 0) return;
    setQLoading(true);
    setQError("");
    setResults([]);
    try {
      const res = await fetch(`${API_URL}/questionnaire`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questions }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(data.results ?? []);
    } catch (e) {
      setQError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setQLoading(false);
    }
  }

  async function exportCsv() {
    const questions = parseQuestions();
    const res = await fetch(`${API_URL}/questionnaire/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questions }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "answers.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function markReviewed(runId: string | null) {
    if (!runId) return;
    await fetch(`${API_URL}/answers/${runId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "reviewed" }),
    });
    setResults((prev) =>
      prev.map((r) => (r.run_id === runId ? { ...r, status: "reviewed" } : r))
    );
  }

  async function loadTraces() {
    try {
      const res = await fetch(`${API_URL}/traces?limit=20`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTraces(data.traces ?? []);
    } catch {
      // traces are optional — ignore fetch errors
    }
  }

  return (
    <main style={{ maxWidth: 860, margin: "0 auto", padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1>SecAnswer</h1>
      <p style={{ color: "#555" }}>
        Security-questionnaire response assistant — grounded, cited, version-aware.
      </p>

      <section style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 24 }}>
        <h2>Ask a question</h2>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={2}
          placeholder="e.g. What is our data retention period?"
          style={{ width: "100%", padding: 8, fontSize: 15 }}
        />
        <button
          onClick={ask}
          disabled={loading || !question.trim()}
          style={{ marginTop: 8, padding: "8px 16px" }}
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
        {answer && (
          <div style={{ marginTop: 12 }}>
            <p style={{ whiteSpace: "pre-wrap" }}>{answer}</p>
            {citations.length > 0 && (
              <ul style={{ color: "#555", fontSize: 14 }}>
                {citations.map((c) => (
                  <li key={c.index}>
                    [{c.index}] {c.title} v{c.version} — “{c.section ?? "n/a"}”, page {c.page ?? "n/a"}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
        <h2>Answer a questionnaire</h2>
        <p style={{ color: "#555" }}>Paste one question per line, then draft, review, and export.</p>
        <textarea
          value={questionsText}
          onChange={(e) => setQuestionsText(e.target.value)}
          rows={6}
          placeholder={"What is your data retention period?\nHow long are backups retained?\nDo you encrypt data at rest?"}
          style={{ width: "100%", padding: 8, fontSize: 15 }}
        />
        <div style={{ marginTop: 8 }}>
          <button
            onClick={draftAll}
            disabled={qLoading || parseQuestions().length === 0}
            style={{ padding: "8px 16px", marginRight: 8 }}
          >
            {qLoading ? "Drafting…" : "Draft all"}
          </button>
          <button onClick={exportCsv} disabled={parseQuestions().length === 0} style={{ padding: "8px 16px" }}>
            Export CSV
          </button>
        </div>
        {qError && <p style={{ color: "crimson" }}>{qError}</p>}
        {results.map((r, i) => (
          <div key={i} style={{ borderTop: "1px solid #eee", marginTop: 12, paddingTop: 12 }}>
            <strong>{r.question}</strong>
            <span
              style={{
                marginLeft: 8,
                fontSize: 12,
                color: r.status === "reviewed" ? "green" : r.status === "error" ? "crimson" : "#888",
              }}
            >
              {r.status}
            </span>
            {r.error && <p style={{ color: "crimson" }}>{r.error}</p>}
            <p style={{ whiteSpace: "pre-wrap", margin: "8px 0" }}>{r.answer}</p>
            {r.citations.length > 0 && (
              <ul style={{ color: "#555", fontSize: 13 }}>
                {r.citations.map((c) => (
                  <li key={c.index}>
                    [{c.index}] {c.title} v{c.version} — “{c.section ?? "n/a"}”, page {c.page ?? "n/a"}
                  </li>
                ))}
              </ul>
            )}
            {r.status !== "reviewed" && r.run_id && (
              <button onClick={() => markReviewed(r.run_id)} style={{ fontSize: 12, padding: "4px 10px" }}>
                Mark reviewed
              </button>
            )}
          </div>
        ))}
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginTop: 24 }}>
        <h2>Traces</h2>
        <p style={{ color: "#555" }}>OpenTelemetry spans — see exactly where a tool call succeeded or failed.</p>
        <button onClick={loadTraces} style={{ padding: "8px 16px", marginBottom: 12 }}>
          Refresh traces
        </button>
        {traces.length === 0 && <p style={{ color: "#888" }}>No traces yet — ask a question, then refresh.</p>}
        {traces.map((t, i) => (
          <div key={i} style={{ borderTop: "1px solid #eee", padding: "8px 0", fontSize: 14 }}>
            <span style={{ fontFamily: "monospace" }}>{t.name}</span>
            <span style={{ marginLeft: 8, color: t.status === "error" ? "crimson" : "green" }}>{t.status}</span>
            <span style={{ marginLeft: 8, color: "#888" }}>
              {t.duration_ms != null ? `${t.duration_ms.toFixed(1)} ms` : ""}
            </span>
            {t.attributes?.question && (
              <span style={{ marginLeft: 8, color: "#555" }}>“{t.attributes.question}”</span>
            )}
          </div>
        ))}
      </section>
    </main>
  );
}
