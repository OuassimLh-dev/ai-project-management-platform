import { useCallback, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { sprintsApi } from "../api/sprints";
import { errorMessage } from "../api/client";
import { useResource } from "../hooks/useResource";
import type { Sprint, SprintUpdate } from "../types/api";
import { Badge } from "../components/Badge";
import { ErrorMessage, Loading } from "../components/Feedback";
import { SprintForm } from "../components/SprintForm";
import { IssueList } from "../components/IssueList";

// Mirrors app.services.sprint.TRANSITIONS; the backend authorizes and validates every change.
const actions: Record<
  Sprint["status"],
  { status: Sprint["status"]; label: string }[]
> = {
  planned: [
    { status: "active", label: "Start sprint" },
    { status: "cancelled", label: "Cancel sprint" },
  ],
  active: [
    { status: "completed", label: "Complete sprint" },
    { status: "cancelled", label: "Cancel sprint" },
  ],
  completed: [],
  cancelled: [],
};
export function SprintPage({ id }: { id: number }) {
  const resource = useResource(useCallback(() => sprintsApi.get(id), [id]));
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState<string | null>(null);
  async function transition(status: Sprint["status"]) {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setError(null);
    try {
      resource.setData(await sprintsApi.update(id, { status }));
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }
  if (resource.loading) return <Loading label="Loading sprint…" />;
  if (resource.error || !resource.data)
    return <ErrorMessage message={resource.error} retry={resource.reload} />;
  const sprint = resource.data;
  return (
    <>
      <Link className="breadcrumb" to={`/app/projects/${sprint.project_id}`}>
        ← Back to project
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">SPRINT</p>
          <h1>{sprint.name}</h1>
          <Badge value={sprint.status} />
        </div>
        <button
          className="secondary"
          disabled={editing || pending}
          onClick={() => {
            setError(null);
            setEditing(true);
          }}
        >
          Edit sprint
        </button>
      </div>
      <section className="panel stack sprint-overview">
        <h2>Sprint plan</h2>
        <p className="prose">{sprint.goal || "No goal provided."}</p>
        <p>
          <time dateTime={sprint.start_date}>{sprint.start_date}</time> –{" "}
          <time dateTime={sprint.end_date}>{sprint.end_date}</time>
        </p>
        <div className="actions">
          {actions[sprint.status].map((action) => (
            <button
              key={action.status}
              disabled={pending || editing}
              onClick={() => void transition(action.status)}
            >
              {action.label}
            </button>
          ))}
        </div>
        {pending && <Loading label="Updating sprint…" />}
        <ErrorMessage message={error} />
      </section>
      {editing && (
        <SprintForm
          initial={sprint}
          onCancel={() => setEditing(false)}
          onSave={async (input) => {
            const changes: SprintUpdate = {};
            if (input.name !== sprint.name) changes.name = input.name;
            if (input.goal !== sprint.goal) changes.goal = input.goal;
            if (input.start_date !== sprint.start_date)
              changes.start_date = input.start_date;
            if (input.end_date !== sprint.end_date)
              changes.end_date = input.end_date;
            if (Object.keys(changes).length)
              resource.setData(await sprintsApi.update(id, changes));
            setEditing(false);
          }}
        />
      )}
      <IssueList projectId={sprint.project_id} fixedSprintId={sprint.id} />
    </>
  );
}
