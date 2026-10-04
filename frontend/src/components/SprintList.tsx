import { Link } from "react-router-dom";
import type { Sprint } from "../types/api";
import { Badge } from "./Badge";
import { EmptyState, ErrorMessage, Loading } from "./Feedback";
export function SprintList({
  data,
  loading,
  error,
  retry,
}: {
  data: Sprint[] | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}) {
  if (loading) return <Loading label="Loading sprints…" />;
  if (error) return <ErrorMessage message={error} retry={retry} />;
  if (!data?.length)
    return (
      <EmptyState
        title="No sprints yet"
        detail="Create one to organize a focused iteration."
      />
    );
  return (
    <div className="card-grid">
      {data.map((sprint) => (
        <article className="panel sprint-card" key={sprint.id}>
          <h3>
            <Link to={`/app/sprints/${sprint.id}`}>{sprint.name}</Link>
          </h3>
          <Badge value={sprint.status} />
          <p>
            <time dateTime={sprint.start_date}>{sprint.start_date}</time> –{" "}
            <time dateTime={sprint.end_date}>{sprint.end_date}</time>
          </p>
          <p className="prose">{sprint.goal || "No goal provided."}</p>
        </article>
      ))}
    </div>
  );
}
