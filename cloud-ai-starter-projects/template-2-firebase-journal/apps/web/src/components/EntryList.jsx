export default function EntryList({ items, selectedId, onSelect, onDelete, nextToken, onMore }) {
  return (
    <div className="panel">
      <h2>Entries</h2>
      <ul className="entry-list">
        {items.map((item) => (
          <li key={item.entryId} className={item.entryId === selectedId ? "selected" : ""}>
            <button className="link" onClick={() => onSelect(item.entryId)}>
              <strong>{item.title}</strong>
              <span>{item.createdAt}</span>
              <span>{item.aiStatus}</span>
            </button>
            <button className="danger" onClick={() => onDelete(item.entryId)}>Delete</button>
          </li>
        ))}
      </ul>
      {nextToken ? <button className="secondary" onClick={onMore}>Load more</button> : null}
    </div>
  );
}
