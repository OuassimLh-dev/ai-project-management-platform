import { useCallback, useState, type FormEvent } from "react";
import { issuesApi } from "../api/issues";
import { errorMessage } from "../api/client";
import { useResource } from "../hooks/useResource";
import { dateLabel, userLabel } from "../utils/format";
import { EmptyState, ErrorMessage, Loading } from "./Feedback";
export function Comments({ issueId }: { issueId: number }) {
  const comments = useResource(
    useCallback(() => issuesApi.comments(issueId), [issueId]),
  );
  const [body, setBody] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || !body.trim()) return;
    setPending(true);
    setError(null);
    try {
      const comment = await issuesApi.addComment(issueId, body.trim());
      comments.setData((current) => [...(current ?? []), comment]);
      setBody("");
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="panel">
      <h2>Conversation</h2>
      {comments.loading ? (
        <Loading label="Loading comments…" />
      ) : comments.error ? (
        <ErrorMessage message={comments.error} retry={comments.reload} />
      ) : !comments.data?.length ? (
        <EmptyState
          title="Start the conversation"
          detail="Share context, questions, or a progress update."
        />
      ) : (
        <ol className="comments">
          {comments.data.map((comment) => (
            <li key={comment.id}>
              <div className="section-heading">
                <strong>{userLabel(comment.author_id)}</strong>
                <time dateTime={comment.created_at}>
                  {dateLabel(comment.created_at)}
                </time>
              </div>
              <p className="prose">{comment.body}</p>
            </li>
          ))}
        </ol>
      )}
      <form onSubmit={submit} className="stack">
        <label>
          Add a comment
          <textarea
            required
            maxLength={10000}
            rows={3}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder="Keep your team in the loop…"
          />
        </label>
        <ErrorMessage message={error} />
        <div>
          <button
            disabled={
              pending || !body.trim() || comments.loading || !!comments.error
            }
          >
            {pending ? "Posting…" : "Post comment"}
          </button>
        </div>
      </form>
    </section>
  );
}
