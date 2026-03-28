"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface SummaryData {
  exercises: string[] | null;
  coaching_notes: string | null;
  next_recommendations: string | null;
  status: string;
}

export function SessionSummary({ sessionId }: { sessionId: number }) {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    if (!polling) return;

    const intervalId = setInterval(async () => {
      try {
        const data = await api.summaries.get(sessionId);
        if (data.status === "done") {
          setSummary(data as SummaryData);
          setPolling(false);
        }
      } catch {
        // Keep polling
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [sessionId, polling]);

  if (polling && !summary) {
    return (
      <div data-testid="summary-loading" style={{ textAlign: "center", padding: 24, color: "#6b7280" }}>
        Generating your session summary…
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div data-testid="summary-card" style={{ background: "#fff", borderRadius: 12, padding: 24, marginTop: 24 }}>
      <h2 style={{ marginTop: 0 }}>Session Summary</h2>

      <div data-testid="summary-exercises">
        <h3 style={{ fontSize: 15, color: "#374151" }}>Exercises Covered</h3>
        {summary.exercises && summary.exercises.length > 0 ? (
          <ul>{summary.exercises.map((ex, i) => <li key={i}>{ex}</li>)}</ul>
        ) : (
          <p style={{ color: "#6b7280" }}>No exercises recorded.</p>
        )}
      </div>

      <div data-testid="summary-coaching-notes">
        <h3 style={{ fontSize: 15, color: "#374151" }}>Coaching Notes</h3>
        <p>{summary.coaching_notes || "No notes."}</p>
      </div>

      <div data-testid="summary-recommendations">
        <h3 style={{ fontSize: 15, color: "#374151" }}>Next Session</h3>
        <p>{summary.next_recommendations || "Keep it up!"}</p>
      </div>
    </div>
  );
}
