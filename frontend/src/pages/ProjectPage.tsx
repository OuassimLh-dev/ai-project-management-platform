import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { projectsApi } from "../api/projects";
import { issuesApi } from "../api/issues";
import { useResource } from "../hooks/useResource";
import { ErrorMessage, Loading } from "../components/Feedback";
import { IssueList } from "../components/IssueList";
import { IssueForm } from "../components/IssueForm";
export function ProjectPage({ id }: { id: number }) {
  const project = useResource(useCallback(() => projectsApi.get(id), [id]));
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  if (project.loading) return <Loading label="Loading project…" />;
  if (project.error || !project.data)
    return <ErrorMessage message={project.error} retry={project.reload} />;
  return (
    <>
      <Link className="breadcrumb" to={`/app/teams/${project.data.team_id}`}>
        ← Back to team
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            {project.data.key} ·{" "}
            {project.data.is_active ? "ACTIVE PROJECT" : "INACTIVE PROJECT"}
          </p>
          <h1>{project.data.name}</h1>
          <p>
            {project.data.description || "Plan the work. Keep the team moving."}
          </p>
        </div>
        <button onClick={() => setCreating(true)} disabled={creating}>
          + Create issue
        </button>
      </div>
      {creating && (
        <IssueForm
          projectId={id}
          onCancel={() => setCreating(false)}
          onSave={async (input) => {
            const issue = await issuesApi.create(id, input);
            navigate(`/app/issues/${issue.id}`);
          }}
        />
      )}
      <IssueList projectId={id} />
    </>
  );
}
