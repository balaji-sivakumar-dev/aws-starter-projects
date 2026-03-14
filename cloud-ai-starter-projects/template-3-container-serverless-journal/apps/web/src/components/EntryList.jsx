function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch { return iso.slice(0, 10); }
}

function aiClass(status) {
  if (status === "DONE") return "ai-done";
  if (status === "PROCESSING") return "ai-processing";
  if (status === "ERROR") return "ai-error";
  return "ai-none";
}

export default function EntryList({ items, loading, selectedId, onSelect, onDelete, nextToken, onMore }) {
  if (loading && !items.length) {
    return <div className="entry-list-empty">Loading…</div>;
  }
  if (!items.length) {
    return <div className="entry-list-empty">No entries yet.<br />Click "+ New" to write your first entry.</div>;
  }
  return (
    <div className="entry-list-scroll">
      {items.map((item) => (
        <div key={item.entryId} className={`entry-item${item.entryId === selectedId ? " selected" : ""}`}>
          <button className="entry-item-btn" onClick={() => onSelect(item.entryId)}>
            <span className="entry-item-title">{item.title}</span>
            <span className="entry-item-meta">
              <span className="entry-item-date">{formatDate(item.createdAt)}</span>
              {item.aiStatus && item.aiStatus !== "PENDING" && (
                <span className={`entry-item-ai ${aiClass(item.aiStatus)}`}>{item.aiStatus}</span>
              )}
            </span>
          </button>
          <button className="entry-item-delete" title="Delete entry" onClick={() => onDelete(item.entryId)}>✕</button>
        </div>
      ))}
      {nextToken && (
        <button className="btn-load-more" onClick={onMore}>Load more…</button>
      )}
    </div>
  );
}
