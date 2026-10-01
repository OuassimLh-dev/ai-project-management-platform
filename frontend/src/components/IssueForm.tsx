import { useCallback, useState, type FormEvent } from "react";
import { projectsApi } from "../api/projects";
import { errorMessage } from "../api/client";
import { useResource } from "../hooks/useResource";
import {
  issueTypes,
  priorities,
  statuses,
  issueSchema,
  type Issue,
  type IssueInput,
} from "../types/api";
import { label, userLabel } from "../utils/format";
import { ErrorMessage, Loading } from "./Feedback";
export function IssueForm({
  projectId,
  initial,
  onSave,
  onCancel,
}: {
  projectId: number;
  initial?: Issue;
  onSave: (input: IssueInput) => Promise<void>;
  onCancel: () => void;
}) {
  const options = useResource(
    useCallback(async () => {
      const [members, sprints] = await Promise.all([
        projectsApi.members(projectId),
        projectsApi.sprints(projectId),
      ]);
      return { members, sprints };
    }, [projectId]),
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending || !options.data) return;
    const form = new FormData(event.currentTarget);
    const nullableId = (name: string) =>
      form.get(name) ? Number(form.get(name)) : null;
    const input: IssueInput = {
      title: String(form.get("title")).trim(),
      description: String(form.get("description") ?? "").trim() || null,
      issue_type: issueSchema.shape.issue_type.parse(form.get("issue_type")),
      priority: issueSchema.shape.priority.parse(form.get("priority")),
      status: issueSchema.shape.status.parse(form.get("status")),
      assignee_id: nullableId("assignee_id"),
      sprint_id: nullableId("sprint_id"),
    };
    setPending(true);
    setError(null);
    try {
      await onSave(input);
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setPending(false);
    }
  }
  return (
    <form className="panel stack" onSubmit={submit}>
      <h2>{initial ? "Edit issue" : "Create issue"}</h2>
      <label>
        Title
        <input
          name="title"
          required
          maxLength={200}
          pattern=".*\S.*"
          defaultValue={initial?.title}
          autoFocus
        />
      </label>
      <label>
        Description
        <textarea
          name="description"
          maxLength={10000}
          rows={5}
          defaultValue={initial?.description ?? ""}
        />
      </label>
      <div className="form-grid three">
        {[
          {
            name: "issue_type",
            text: "Type",
            values: issueTypes,
            value: initial?.issue_type ?? "task",
          },
          {
            name: "priority",
            text: "Priority",
            values: priorities,
            value: initial?.priority ?? "medium",
          },
          {
            name: "status",
            text: "Status",
            values: statuses,
            value: initial?.status ?? "backlog",
          },
        ].map((field) => (
          <label key={field.name}>
            {field.text}
            <select name={field.name} defaultValue={field.value}>
              {field.values.map((value) => (
                <option key={value} value={value}>
                  {label(value)}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {options.loading ? (
        <Loading label="Loading assignment options…" />
      ) : options.error ? (
        <ErrorMessage message={options.error} retry={options.reload} />
      ) : (
        <div className="form-grid">
          <label>
            Assignee
            <select
              name="assignee_id"
              defaultValue={initial?.assignee_id ?? ""}
            >
              <option value="">Unassigned</option>
              {options.data?.members.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {userLabel(member.user_id)} · {member.role}
                </option>
              ))}
            </select>
          </label>
          <label>
            Sprint
            <select name="sprint_id" defaultValue={initial?.sprint_id ?? ""}>
              <option value="">No sprint</option>
              {options.data?.sprints.map((sprint) => (
                <option key={sprint.id} value={sprint.id}>
                  {sprint.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      <ErrorMessage message={error} />
      <div className="actions">
        <button disabled={pending || options.loading || !!options.error}>
          {pending ? "Saving…" : initial ? "Save changes" : "Save issue"}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={pending}
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
