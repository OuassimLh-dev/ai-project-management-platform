import { useState, type FormEvent } from "react";
import { errorMessage } from "../api/client";
import { ErrorMessage } from "./Feedback";
import type { ProjectInput } from "../types/api";
export function WorkspaceForm({
  project = false,
  onSave,
  onCancel,
}: {
  project?: boolean;
  onSave: (value: ProjectInput) => Promise<void>;
  onCancel: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      await onSave({
        name: String(form.get("name")).trim(),
        description: String(form.get("description") ?? "").trim() || null,
        key: String(form.get("key") ?? "")
          .trim()
          .toUpperCase(),
      });
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setPending(false);
    }
  }
  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Create {project ? "project" : "team"}</h2>
      <label>
        Name
        <input
          name="name"
          required
          maxLength={150}
          pattern=".*\S.*"
          autoFocus
        />
      </label>
      {project && (
        <label>
          Project key
          <input
            name="key"
            required
            maxLength={20}
            pattern="[A-Za-z][A-Za-z0-9]*"
            placeholder="e.g. APP"
          />
          <small>Letters and numbers, starting with a letter.</small>
        </label>
      )}
      <label>
        Description
        <textarea name="description" maxLength={5000} rows={3} />
      </label>
      <ErrorMessage message={error} />
      <div className="actions">
        <button disabled={pending}>
          {pending ? "Creating…" : project ? "Save project" : "Save team"}
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
