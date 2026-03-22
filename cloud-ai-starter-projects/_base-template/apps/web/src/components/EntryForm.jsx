import { useState } from "react";

function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function EntryForm({ initial, submitLabel, onSubmit, onCancel }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [body, setBody] = useState(initial?.body || "");
  const [entryDate, setEntryDate] = useState(initial?.entryDate || todayLocal());

  return (
    <div className="card">
      <div className="form-title">{initial ? "Edit Entry" : "New Entry"}</div>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit({ title: title.trim(), body: body.trim(), entryDate }); }}>
        <label>
          Title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What's on your mind?"
            required
          />
        </label>
        <label className="entry-date-label">
          Entry Date
          <input
            type="date"
            className="entry-date-input"
            value={entryDate}
            max={todayLocal()}
            onChange={(e) => setEntryDate(e.target.value)}
          />
        </label>
        <label>
          Item
          <textarea
            rows={14}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your thoughts here…"
            required
          />
        </label>
        <div className="form-actions">
          <button type="submit" className="btn-primary">{submitLabel}</button>
          <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
