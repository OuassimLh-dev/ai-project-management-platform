import { useRef, useState, type FormEvent } from "react";
import type { Sprint, SprintInput } from "../types/api";
import { errorMessage } from "../api/client";
import { ErrorMessage } from "./Feedback";
export function SprintForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Sprint;
  onSave: (input: SprintInput) => Promise<void>;
  onCancel: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current) return;
    const form = new FormData(event.currentTarget);
    const input: SprintInput = {
      name: String(form.get("name") ?? "").trim(),
      goal: String(form.get("goal") ?? "").trim() || null,
      start_date: String(form.get("start_date") ?? ""),
      end_date: String(form.get("end_date") ?? ""),
    };
    if (input.end_date < input.start_date) {
      setError("End date must be on or after start date.");
      return;
    }
    inFlight.current = true;
    setPending(true);
    setError(null);
    try {
      await onSave(input);
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }
  return (
    <form className="panel stack" onSubmit={submit}>
      <h2>{initial ? "Edit sprint" : "Create sprint"}</h2>
      <label>
        Sprint name
        <input
          name="name"
          required
          maxLength={150}
          pattern=".*\S.*"
          defaultValue={initial?.name}
          autoFocus
        />
      </label>
      <label>
        Goal
        <textarea
          name="goal"
          maxLength={5000}
          rows={3}
          defaultValue={initial?.goal ?? ""}
        />
      </label>
      <div className="form-grid">
        <label>
          Start date
          <input
            name="start_date"
            type="date"
            required
            defaultValue={initial?.start_date}
          />
        </label>
        <label>
          End date
          <input
            name="end_date"
            type="date"
            required
            defaultValue={initial?.end_date}
          />
        </label>
      </div>
      <ErrorMessage message={error} />
      <div className="actions">
        <button disabled={pending}>
          {pending
            ? "Saving…"
            : initial
              ? "Save sprint changes"
              : "Save sprint"}
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
