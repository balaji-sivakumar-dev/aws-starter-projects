import { useState, useEffect } from "react";

function aiStatusClass(status) {
  if (status === "DONE" || status === "COMPLETE") return "done";
  if (status === "PROCESSING") return "processing";
  if (status === "ERROR" || status === "FAILED") return "error";
  if (status === "SKIPPED") return "skipped";
  return "pending";
}

export default function EntryDetail({ entry, onEdit, onRefresh, onTriggerAi }) {
  const [errorDismissed, setErrorDismissed] = useState(false);
  useEffect(() => { setErrorDismissed(false); }, [entry?.entryId]);
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

        {entry.aiError && !errorDismissed && (
          <div className="ai-error-msg" style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
            <span style={{ flex: 1 }}>{entry.aiError}</span>
            <button
              onClick={() => setErrorDismissed(true)}
              style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1rem", lineHeight: 1, padding: "0 2px", color: "inherit", opacity: 0.7 }}
              title="Dismiss"
            >✕</button>
          </div>
        )}

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
