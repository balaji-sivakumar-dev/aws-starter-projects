import { useRef, useState } from "react";
import { bulkImportItems } from "../api/entries";

// ── CSV parser ────────────────────────────────────────────────────────────────
// Handles quoted fields, commas/newlines inside quotes, and optional BOM.
function parseCSV(text) {
  // Strip BOM
  const src = text.replace(/^\uFEFF/, "");
  const rows = [];
  let field = "";
  let row = [];
  let inQuote = false;

  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    const next = src[i + 1];

    if (inQuote) {
      if (ch === '"' && next === '"') { field += '"'; i++; }       // escaped quote
      else if (ch === '"') { inQuote = false; }                    // end of quoted field
      else { field += ch; }
    } else {
      if (ch === '"') { inQuote = true; }
      else if (ch === ',') { row.push(field); field = ""; }
      else if (ch === '\n' || (ch === '\r' && next === '\n')) {
        row.push(field); field = "";
        rows.push(row); row = [];
        if (ch === '\r') i++;
      } else if (ch === '\r') {
        row.push(field); field = "";
        rows.push(row); row = [];
      } else {
        field += ch;
      }
    }
  }
  // last field / row
  if (field || row.length) { row.push(field); rows.push(row); }

  if (rows.length < 2) return { headers: [], records: [] };

  const headers = rows[0].map((h) => h.trim().toLowerCase());
  const records = rows
    .slice(1)
    .filter((r) => r.some((f) => f.trim()))   // skip blank lines
    .map((r) => {
      const obj = {};
      headers.forEach((h, i) => { obj[h] = (r[i] || "").trim(); });
      return obj;
    });

  return { headers, records };
}

// Map parsed record → entry payload
function toEntry(rec) {
  return {
    title: rec.title || rec["entry title"] || "",
    body: rec.body || rec.content || rec.text || rec.entry || "",
    entryDate: rec.entrydate || rec["entry date"] || rec.date || "",
  };
}

function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function ImportCSV({ onDone, onCancel }) {
  const [parsed, setParsed] = useState(null);   // { headers, entries: [{title,body,entryDate}] }
  const [fileName, setFileName] = useState("");
  const [parseError, setParseError] = useState("");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);   // { imported, failed, errors }
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef();

  function handleFile(file) {
    if (!file) return;
    setFileName(file.name);
    setParseError("");
    setResult(null);
    setParsed(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const { headers, records } = parseCSV(e.target.result);
        if (!headers.includes("title") && !headers.includes("entry title")) {
          setParseError(`Missing required column "title". Found columns: ${headers.join(", ") || "(none)"}`);
          return;
        }
        if (!headers.some((h) => ["body", "content", "text", "entry"].includes(h))) {
          setParseError(`Missing required column "body" (or "content"/"text"). Found columns: ${headers.join(", ")}`);
          return;
        }
        const entries = records.map(toEntry).filter((e) => e.title && e.body);
        const skipped = records.length - entries.length;
        setParsed({ headers, entries, skipped });
      } catch (err) {
        setParseError("Failed to parse CSV: " + err.message);
      }
    };
    reader.readAsText(file);
  }

  async function handleImport() {
    if (!parsed?.entries?.length) return;
    setImporting(true);
    setResult(null);
    try {
      const res = await bulkImportItems(parsed.entries);
      setResult(res);
      if (res.imported > 0) {
        setTimeout(() => onDone && onDone(res.imported), 1500);
      }
    } catch (err) {
      setResult({ imported: 0, failed: parsed.entries.length, errors: [{ title: "—", error: err.message }] });
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="import-container card">
      <div className="import-header">
        <h2 className="import-title">Import Items</h2>
        <button className="btn-ghost" onClick={onCancel}>✕ Cancel</button>
      </div>

      {/* Format guide */}
      <div className="import-guide">
        <p>Upload a <strong>.csv</strong> file with the following columns:</p>
        <div className="import-columns">
          <span className="import-col required">title <em>(required)</em></span>
          <span className="import-col required">body <em>(required)</em></span>
          <span className="import-col optional">entryDate <em>YYYY-MM-DD, optional</em></span>
        </div>
        <p className="import-guide-note">
          First row must be the header. Fields with commas should be quoted.<br />
          Also accepts: <code>content</code> or <code>text</code> instead of <code>body</code>; <code>date</code> instead of <code>entryDate</code>.
        </p>
        <details className="import-example-toggle">
          <summary>Show example CSV</summary>
          <pre className="import-example">{`title,body,entryDate
"Morning reflections","Woke up early and felt calm today.","${todayLocal()}"
"Weekend hike","The trail was steep but the view made it worthwhile.",`}</pre>
        </details>
      </div>

      {/* Drop zone */}
      {!result && (
        <div
          className={`import-dropzone${dragOver ? " drag-over" : ""}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => handleFile(e.target.files[0])}
          />
          <div className="import-dropzone-icon">📂</div>
          {fileName
            ? <p className="import-dropzone-filename">{fileName}</p>
            : <p>Drop a CSV file here or <span className="import-dropzone-link">click to browse</span></p>
          }
        </div>
      )}

      {parseError && <p className="import-error">{parseError}</p>}

      {/* Preview */}
      {parsed && !result && (
        <div className="import-preview">
          <div className="import-preview-header">
            <span className="import-preview-count">
              {parsed.entries.length} entries ready to import
              {parsed.skipped > 0 && ` · ${parsed.skipped} rows skipped (missing title or body)`}
            </span>
          </div>
          <div className="import-preview-table">
            <div className="import-preview-row import-preview-th">
              <span>Title</span>
              <span>Date</span>
              <span>Body preview</span>
            </div>
            {parsed.entries.slice(0, 10).map((e, i) => (
              <div key={i} className="import-preview-row">
                <span className="import-preview-title">{e.title}</span>
                <span className="import-preview-date">{e.entryDate || "today"}</span>
                <span className="import-preview-body">{e.body.slice(0, 80)}{e.body.length > 80 ? "…" : ""}</span>
              </div>
            ))}
            {parsed.entries.length > 10 && (
              <div className="import-preview-more">…and {parsed.entries.length - 10} more</div>
            )}
          </div>
          <div className="import-actions">
            <button
              className="btn-primary"
              onClick={handleImport}
              disabled={importing}
            >
              {importing ? "Importing…" : `Import ${parsed.entries.length} entries`}
            </button>
            <button className="btn-ghost" onClick={() => { setParsed(null); setFileName(""); }}>
              Choose different file
            </button>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="import-result">
          {result.imported > 0 && (
            <div className="import-result-success">
              ✅ {result.imported} {result.imported === 1 ? "entry" : "entries"} imported successfully
            </div>
          )}
          {result.failed > 0 && (
            <div className="import-result-errors">
              ⚠️ {result.failed} {result.failed === 1 ? "entry" : "entries"} failed:
              <ul>
                {result.errors?.map((e, i) => (
                  <li key={i}><strong>{e.title || "?"}</strong>: {e.error}</li>
                ))}
              </ul>
            </div>
          )}
          {result.imported > 0 && (
            <p className="import-result-note">Redirecting to items…</p>
          )}
          {result.imported === 0 && (
            <button className="btn-secondary" onClick={() => setResult(null)}>Try again</button>
          )}
        </div>
      )}
    </div>
  );
}
