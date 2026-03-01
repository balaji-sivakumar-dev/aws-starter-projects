export default function EntryDetail({ entry, onEdit, onRefresh, onTriggerAi }) {
  if (!entry) {
    return <div className="panel"><h2>Entry</h2><p>Select an entry.</p></div>;
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
      <p><strong>AI Status:</strong> {entry.aiStatus}</p>
      <p>{entry.body}</p>
      <h3>Summary</h3>
      <p>{entry.summary || "Not generated"}</p>
      <h3>Tags</h3>
      <p>{(entry.tags || []).length ? entry.tags.join(", ") : "No tags"}</p>
      {entry.aiError ? <p className="error">{entry.aiError}</p> : null}
    </div>
  );
}
