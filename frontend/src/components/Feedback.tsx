export function Loading({ label = "Loading workspace…" }: { label?: string }) {
  return (
    <p className="feedback" role="status">
      {label}
    </p>
  );
}
export function ErrorMessage({
  message,
  retry,
}: {
  message: string | null;
  retry?: () => void;
}) {
  if (!message) return null;
  return (
    <div className="error" role="alert">
      <p>{message}</p>
      {retry && (
        <button className="secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
