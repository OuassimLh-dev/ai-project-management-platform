import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { teamsApi } from "../api/teams";
import { projectsApi } from "../api/projects";
import { useAuth } from "../auth/AuthContext";
import { useResource } from "../hooks/useResource";
import { Loading, ErrorMessage, EmptyState } from "../components/Feedback";
import { WorkspaceForm } from "../components/WorkspaceForm";
export function TeamPage({ id }: { id: number }) {
  const { user } = useAuth();
  const resource = useResource(
    useCallback(async () => {
      const [team, projects, members] = await Promise.all([
        teamsApi.get(id),
        projectsApi.list(id),
        teamsApi.members(id),
      ]);
      return { team, projects, members };
    }, [id]),
  );
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  if (resource.loading) return <Loading label="Loading team…" />;
  if (resource.error || !resource.data)
    return <ErrorMessage message={resource.error} retry={resource.reload} />;
  const { team, projects, members } = resource.data;
  const role = members.find((member) => member.user_id === user?.id)?.role;
  return (
    <>
      <Link className="breadcrumb" to="/app/teams">
        ← All teams
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">TEAM WORKSPACE</p>
          <h1>{team.name}</h1>
          <p>{team.description || "Your team’s projects, in one place."}</p>
        </div>
        {(role === "owner" || role === "admin") && (
          <button disabled={creating} onClick={() => setCreating(true)}>
            + Create project
          </button>
        )}
      </div>
      {creating && (
        <WorkspaceForm
          project
          onCancel={() => setCreating(false)}
          onSave={async (body) => {
            const project = await projectsApi.create(id, body);
            navigate(`/app/projects/${project.id}`);
          }}
        />
      )}
      <h2>
        Projects <span className="count">{projects.length}</span>
      </h2>
      {projects.length ? (
        <div className="card-grid">
          {projects.map((project) => (
            <article className="panel" key={project.id}>
              <span className="project-key">{project.key}</span>
              <h3>
                <Link to={`/app/projects/${project.id}`}>{project.name}</Link>
              </h3>
              <p>{project.description || "No description yet."}</p>
              <small>
                {project.is_active ? "Active project" : "Inactive project"}
              </small>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No projects yet"
          detail={
            role === "member"
              ? "Projects assigned to you will appear here."
              : "Create a project to start tracking issues."
          }
        />
      )}
    </>
  );
}
