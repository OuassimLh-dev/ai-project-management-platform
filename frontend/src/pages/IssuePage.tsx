import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { issuesApi } from "../api/issues";
import { useResource } from "../hooks/useResource";
import { Loading, ErrorMessage } from "../components/Feedback";
import { Badge } from "../components/Badge";
import { IssueForm } from "../components/IssueForm";
import { Comments } from "../components/Comments";
import { Activity } from "../components/Activity";
import { dateLabel, userLabel } from "../utils/format";
import type { IssueUpdate } from "../types/api";
export function IssuePage({ id }: { id: number }) {
  const resource = useResource(useCallback(() => issuesApi.get(id), [id]));
  const [editing, setEditing] = useState(false);
  const [historyVersion, setHistoryVersion] = useState(0);
  if (resource.loading) return <Loading label="Loading issue…" />;
  if (resource.error || !resource.data)
    return <ErrorMessage message={resource.error} retry={resource.reload} />;
  const issue = resource.data;
  return (
    <>
      <Link
        className="breadcrumb"
        to={`/app/projects/${issue.project_id}/issues`}
      >
        ← Project issues
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">{issue.issue_key}</p>
          <h1>{issue.title}</h1>
          <div className="badges">
            <Badge value={issue.issue_type} />
            <Badge value={issue.priority} />
            <Badge value={issue.status} />
          </div>
        </div>
        <button
          className="secondary"
          disabled={editing}
          onClick={() => setEditing(true)}
        >
          Edit issue
        </button>
      </div>
      {editing && (
        <IssueForm
          projectId={issue.project_id}
          initial={issue}
          onCancel={() => setEditing(false)}
          onSave={async (input) => {
            const changes: IssueUpdate = {};
            if (input.title !== issue.title) changes.title = input.title;
            if (input.description !== issue.description)
              changes.description = input.description;
            if (input.issue_type !== issue.issue_type)
              changes.issue_type = input.issue_type;
            if (input.priority !== issue.priority)
              changes.priority = input.priority;
            if (input.status !== issue.status) changes.status = input.status;
            if (input.assignee_id !== issue.assignee_id)
              changes.assignee_id = input.assignee_id;
            if (input.sprint_id !== issue.sprint_id)
              changes.sprint_id = input.sprint_id;
            if (Object.keys(changes).length) {
              resource.setData(await issuesApi.update(id, changes));
              setHistoryVersion((version) => version + 1);
            }
            setEditing(false);
          }}
        />
      )}
      <div className="detail-grid">
        <div className="stack">
          <section className="panel">
            <h2>Description</h2>
            <p className="prose">
              {issue.description || "No description provided."}
            </p>
          </section>
          <Comments issueId={id} />
          <Activity key={historyVersion} issueId={id} />
        </div>
        <aside className="panel details">
          <h2>Issue details</h2>
          <dl>
            <dt>Reporter</dt>
            <dd>{userLabel(issue.reporter_id)}</dd>
            <dt>Assignee</dt>
            <dd>{userLabel(issue.assignee_id)}</dd>
            <dt>Sprint</dt>
            <dd>
              {issue.sprint_id ? `Sprint #${issue.sprint_id}` : "No sprint"}
            </dd>
            <dt>Created</dt>
            <dd>{dateLabel(issue.created_at)}</dd>
            <dt>Updated</dt>
            <dd>{dateLabel(issue.updated_at)}</dd>
          </dl>
        </aside>
      </div>
    </>
  );
}
