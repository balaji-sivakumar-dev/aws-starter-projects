export default function EntryDetail({ entry, onEdit, onTriggerAi, onRefresh }) {
  if (!entry) {
    return (
      <div className="panel">
        <h2>Entry Detail</h2>
        <p>Select an entry to view details.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="row between">
        <h2>{entry.title}</h2>
        <div className="row">
          <button className="secondary" onClick={onRefresh}>Refresh</button>
          <button className="secondary" onClick={onEdit}>Edit</button>
          <button onClick={onTriggerAi}>Trigger AI</button>
        </div>
      </div>
      <p className="status-line">AI Status: <strong>{entry.aiStatus}</strong></p>
      <p>{entry.body}</p>
      <h3>Summary</h3>
      <p>{entry.summary || "Not generated yet."}</p>
      <h3>Tags</h3>
      <p>{entry.tags && entry.tags.length ? entry.tags.join(", ") : "No tags"}</p>
      {entry.aiError ? (
        <>
          <h3>AI Error</h3>
          <p>{entry.aiError}</p>
        </>
      ) : null}
    </div>
  );
}
