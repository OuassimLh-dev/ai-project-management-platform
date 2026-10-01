import { useCallback } from "react";
import { issuesApi } from "../api/issues";
import { useResource } from "../hooks/useResource";
import { dateLabel, label, userLabel } from "../utils/format";
import { EmptyState, ErrorMessage, Loading } from "./Feedback";
export function Activity({ issueId }: { issueId: number }) {
  const activity = useResource(
    useCallback(() => issuesApi.activity(issueId), [issueId]),
  );
  return (
    <section className="panel">
      <h2>Activity</h2>
      {activity.loading ? (
        <Loading label="Loading activity…" />
      ) : activity.error ? (
        <ErrorMessage message={activity.error} retry={activity.reload} />
      ) : !activity.data?.length ? (
        <EmptyState
          title="No activity yet"
          detail="Changes to this issue will appear here."
        />
      ) : (
        <ol className="timeline">
          {activity.data.map((entry) => (
            <li key={entry.id}>
              {entry.action === "created" ? (
                <p>Created by {userLabel(entry.actor_id)}</p>
              ) : (
                <>
                  <p>
                    <strong>
                      {label((entry.field_name || "Issue").replace(/_id$/, ""))}
                    </strong>{" "}
                    changed by {userLabel(entry.actor_id)}
                  </p>
                  <p className="activity-values">
                    {entry.old_value ?? "None"}{" "}
                    <span aria-label="changed to">→</span>{" "}
                    {entry.new_value ?? "None"}
                  </p>
                </>
              )}
              <time dateTime={entry.created_at}>
                {dateLabel(entry.created_at)}
              </time>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
