export default function EntryList({ items, selectedId, onSelect, onDelete, nextToken, onLoadMore }) {
  return (
    <div className="panel">
      <div className="row between">
        <h2>Entries</h2>
      </div>
      {items.length === 0 ? <p>No entries yet.</p> : null}
      <ul className="entry-list">
        {items.map((item) => (
          <li key={item.entryId} className={selectedId === item.entryId ? "selected" : ""}>
            <button className="link" onClick={() => onSelect(item.entryId)}>
              <strong>{item.title}</strong>
              <span>{item.createdAt}</span>
              <span className="status">{item.aiStatus}</span>
            </button>
            <button className="danger" onClick={() => onDelete(item.entryId)}>Delete</button>
          </li>
        ))}
      </ul>
      {nextToken ? (
        <button className="secondary" onClick={onLoadMore}>Load more</button>
      ) : null}
    </div>
  );
}
