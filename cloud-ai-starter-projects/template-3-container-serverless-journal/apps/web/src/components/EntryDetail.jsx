function aiStatusClass(status) {
  if (status === "DONE") return "done";
  if (status === "PROCESSING") return "processing";
  if (status === "ERROR") return "error";
  if (status === "SKIPPED") return "skipped";
  return "pending";
}

export default function EntryDetail({ entry, onEdit, onRefresh, onTriggerAi }) {
  if (!entry) {
    return (
      <div className="entry-detail-empty">
        <div className="entry-detail-empty-icon">📝</div>
        <div className="entry-detail-empty-text">Select an entry to read it</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="entry-header">
        <h1 className="entry-title">{entry.title}</h1>
        <div className="entry-actions">
          <button className="btn-ghost" onClick={onRefresh}>↻ Refresh</button>
          <button className="btn-secondary" onClick={onEdit}>Edit</button>
          <button className="btn-ai" onClick={onTriggerAi}>✦ AI Enrich</button>
        </div>
      </div>

      <p className="entry-body">{entry.body}</p>

      <div className="entry-ai-section">
        <div className="section-label">AI Analysis</div>
        <div className="ai-status-row">
          <span className={`ai-badge ${aiStatusClass(entry.aiStatus)}`}>
            {entry.aiStatus || "PENDING"}
          </span>
          {!["DONE", "PROCESSING"].includes(entry.aiStatus) && (
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Click "AI Enrich" to analyse this entry
            </span>
          )}
        </div>

        {entry.aiError && <div className="ai-error-msg">Error: {entry.aiError}</div>}

        {entry.summary && (
          <>
            <div className="section-label" style={{ marginTop: "14px" }}>Summary</div>
            <div className="ai-summary">{entry.summary}</div>
          </>
        )}

        {entry.tags?.length > 0 && (
          <>
            <div className="section-label" style={{ marginTop: "14px" }}>Tags</div>
            <div className="tag-list">
              {entry.tags.map((t) => <span key={t} className="tag">{t}</span>)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
