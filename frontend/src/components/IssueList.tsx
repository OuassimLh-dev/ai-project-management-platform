import { useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { issuesApi } from "../api/issues";
import { useResource } from "../hooks/useResource";
import {
  issueSchema,
  issueTypes,
  priorities,
  statuses,
  type IssueFilters,
} from "../types/api";
import { label, userLabel } from "../utils/format";
import { Badge } from "./Badge";
import { Loading, ErrorMessage, EmptyState } from "./Feedback";
export function IssueList({ projectId }: { projectId: number }) {
  const [params, setParams] = useSearchParams();
  const status = issueSchema.shape.status.safeParse(params.get("status"));
  const priority = issueSchema.shape.priority.safeParse(params.get("priority"));
  const type = issueSchema.shape.issue_type.safeParse(params.get("issue_type"));
  const statusValue = status.success ? status.data : undefined;
  const priorityValue = priority.success ? priority.data : undefined;
  const typeValue = type.success ? type.data : undefined;
  const load = useCallback(() => {
    const filters: IssueFilters = {
      ...(statusValue ? { status: statusValue } : {}),
      ...(priorityValue ? { priority: priorityValue } : {}),
      ...(typeValue ? { issue_type: typeValue } : {}),
    };
    return issuesApi.list(projectId, filters);
  }, [projectId, statusValue, priorityValue, typeValue]);
  const resource = useResource(load);
  const filtered = !!(statusValue || priorityValue || typeValue);
  function change(name: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    setParams(next, { replace: true });
  }
  return (
    <section className="panel issue-list">
      <div className="section-heading">
        <h2>Issues</h2>
        <span className="muted">Your project’s work, at a glance</span>
      </div>
      <div className="filters">
        {[
          {
            name: "status",
            text: "Filter status",
            values: statuses,
            value: statusValue,
          },
          {
            name: "priority",
            text: "Filter priority",
            values: priorities,
            value: priorityValue,
          },
          {
            name: "issue_type",
            text: "Filter type",
            values: issueTypes,
            value: typeValue,
          },
        ].map((field) => (
          <label key={field.name}>
            {field.text}
            <select
              value={field.value ?? ""}
              onChange={(event) => change(field.name, event.target.value)}
            >
              <option value="">
                All{" "}
                {field.name === "issue_type"
                  ? "types"
                  : field.name === "priority"
                    ? "priorities"
                    : "statuses"}
              </option>
              {field.values.map((value) => (
                <option key={value} value={value}>
                  {label(value)}
                </option>
              ))}
            </select>
          </label>
        ))}
        {filtered && (
          <button className="secondary" onClick={() => setParams({})}>
            Clear filters
          </button>
        )}
      </div>
      {resource.loading ? (
        <Loading label="Loading issues…" />
      ) : resource.error ? (
        <ErrorMessage message={resource.error} retry={resource.reload} />
      ) : !resource.data?.length ? (
        <EmptyState
          title={filtered ? "No matching issues" : "No issues yet"}
          detail={
            filtered
              ? "Try another filter or clear your selection."
              : "Create the first issue to give your project a clear next step."
          }
        />
      ) : (
        <ul className="issue-rows">
          {resource.data.map((issue) => (
            <li key={issue.id}>
              <div className="issue-primary">
                <Link className="issue-link" to={`/app/issues/${issue.id}`}>
                  <span className="project-key">{issue.issue_key}</span>
                  <strong>{issue.title}</strong>
                </Link>
                <small>
                  {userLabel(issue.assignee_id)} ·{" "}
                  {issue.sprint_id ? `Sprint #${issue.sprint_id}` : "No sprint"}
                </small>
              </div>
              <div className="badges">
                <Badge value={issue.issue_type} />
                <Badge value={issue.priority} />
                <Badge value={issue.status} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
