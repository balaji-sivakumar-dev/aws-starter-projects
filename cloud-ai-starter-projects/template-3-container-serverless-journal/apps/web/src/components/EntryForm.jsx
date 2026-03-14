import { useState } from "react";

export default function EntryForm({ initial, submitLabel, onSubmit, onCancel }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [body, setBody] = useState(initial?.body || "");

  return (
    <div className="card">
      <div className="form-title">{initial ? "Edit Entry" : "New Entry"}</div>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit({ title: title.trim(), body: body.trim() }); }}>
        <label>
          Title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What's on your mind?"
            required
          />
        </label>
        <label>
          Journal Entry
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
