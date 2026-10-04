import { useCallback, useRef, useState } from "react";
import { aiApi } from "../api/ai";
import { errorMessage } from "../api/client";
import { useResource } from "../hooks/useResource";
import type { AIAnalysis } from "../types/api";
import { dateLabel, userLabel } from "../utils/format";
import { Badge } from "./Badge";
import { EmptyState, ErrorMessage, Loading } from "./Feedback";

// SQLite test responses may omit a timezone; database timestamps represent UTC.
const timestamp = (value: string) =>
  Date.parse(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value + "Z");

export function IssueAIAnalysis({ issueId }: { issueId: number }) {
  const history = useResource(
    useCallback(() => aiApi.history(issueId), [issueId]),
  );
  const [created, setCreated] = useState<AIAnalysis[]>([]);
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState<string | null>(null);
  // Merge by record ID so a late history response cannot discard a new result.
  // Backend history is chronological by created_at then ID; present newest first.
  const records = [
    ...new Map(
      [...(history.data ?? []), ...created].map((record) => [
        record.id,
        record,
      ]),
    ).values(),
  ].sort(
    (a, b) => timestamp(b.created_at) - timestamp(a.created_at) || b.id - a.id,
  );

  async function analyze() {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setError(null);
    try {
      const result = await aiApi.analyze(issueId);
      setCreated((previous) => [...previous, result]);
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  return (
    <section className="panel stack ai-analysis" aria-labelledby="ai-heading">
      <div className="section-heading">
        <h2 id="ai-heading">AI analysis</h2>
        <button type="button" disabled={pending} onClick={() => void analyze()}>
          {pending ? "Analyzing…" : "Analyze issue"}
        </button>
      </div>
      <p className="muted">
        AI suggestions are advisory and do not change this issue. Review them
        before making your own edits.
      </p>
      {pending && <Loading label="Analyzing issue…" />}
      <ErrorMessage message={error} />
      {history.loading && <Loading label="Loading analysis history…" />}
      <ErrorMessage message={history.error} retry={history.reload} />
      {!history.loading && !history.error && records.length === 0 && (
        <EmptyState
          title="No AI analyses yet"
          detail="Analyze this issue to get an advisory summary and suggestions."
        />
      )}
      <div className="stack" aria-live="polite">
        {records.map((record, index) => (
          <article
            className="analysis-result"
            key={record.id}
            aria-label={
              index === 0
                ? "Latest analysis"
                : `Previous analysis #${record.id}`
            }
          >
            <h3>{index === 0 ? "Latest analysis" : "Previous analysis"}</h3>
            <dl className="analysis-fields">
              <dt>Summary</dt>
              <dd className="prose">{record.summary}</dd>
              <dt>Suggested type</dt>
              <dd>
                <Badge value={record.suggested_type} />
              </dd>
              <dt>Suggested priority</dt>
              <dd>
                <Badge value={record.suggested_priority} />
              </dd>
              <dt>Priority explanation</dt>
              <dd className="prose">{record.explanation}</dd>
            </dl>
            <p className="analysis-meta">
              {userLabel(record.requested_by_id)} · {record.model_name} ·{" "}
              <time dateTime={record.created_at}>
                {dateLabel(record.created_at)}
              </time>
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
