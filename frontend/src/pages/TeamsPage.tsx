import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { teamsApi } from "../api/teams";
import { useResource } from "../hooks/useResource";
import { Loading, ErrorMessage, EmptyState } from "../components/Feedback";
import { WorkspaceForm } from "../components/WorkspaceForm";
export function TeamsPage() {
  const resource = useResource(teamsApi.list);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE</p>
          <h1>Your teams</h1>
          <p>Choose a team to explore projects and move work forward.</p>
        </div>
        <button onClick={() => setCreating(true)} disabled={creating}>
          + Create team
        </button>
      </div>
      {creating && (
        <WorkspaceForm
          onCancel={() => setCreating(false)}
          onSave={async ({ name, description }) => {
            const team = await teamsApi.create({ name, description });
            navigate(`/app/teams/${team.id}`);
          }}
        />
      )}
      {resource.loading ? (
        <Loading label="Loading teams…" />
      ) : resource.error ? (
        <ErrorMessage message={resource.error} retry={resource.reload} />
      ) : !resource.data?.length ? (
        <EmptyState
          title="A place for your next project"
          detail="Create your first team to start organizing work together."
        />
      ) : (
        <div className="card-grid">
          {resource.data.map((team) => (
            <article className="panel team-card" key={team.id}>
              <span className="tile-icon">
                {team.name.slice(0, 1).toUpperCase()}
              </span>
              <h2>
                <Link to={`/app/teams/${team.id}`}>{team.name}</Link>
              </h2>
              <p>{team.description || "A shared workspace for your team."}</p>
              <Link className="text-link" to={`/app/teams/${team.id}`}>
                View projects →
              </Link>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
