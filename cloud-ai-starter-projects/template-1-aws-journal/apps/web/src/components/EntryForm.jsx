import { useState } from "react";

export default function EntryForm({ initialValue, submitLabel, onSubmit, onCancel }) {
  const [title, setTitle] = useState(initialValue?.title || "");
  const [body, setBody] = useState(initialValue?.body || "");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await onSubmit({ title: title.trim(), body: body.trim() });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="panel form-panel">
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={140} />
      </label>
      <label>
        Body
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={10} required />
      </label>
      <div className="row">
        <button type="submit" disabled={busy}>{busy ? "Saving..." : submitLabel}</button>
        {onCancel ? (
          <button type="button" className="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  );
}
