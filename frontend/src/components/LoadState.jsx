/** What a page shows before its data arrives, or when it couldn't get it. */
export default function LoadState({ error, label = "Loading…", onRetry }) {
  if (error) {
    return (
      <div className="load-error" role="alert">
        <b>Couldn't load this</b>: {error}.{" "}
        {onRetry && <button className="more" onClick={onRetry}>Try again</button>}
      </div>
    );
  }
  return <p className="empty"><span className="spinner" aria-hidden="true"></span>{label}</p>;
}
