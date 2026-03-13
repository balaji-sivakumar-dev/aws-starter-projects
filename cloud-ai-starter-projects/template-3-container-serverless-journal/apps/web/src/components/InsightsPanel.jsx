import { useEffect, useState } from "react";

const PERIODS = ["weekly", "monthly", "yearly"];

function GenerateForm({ onGenerate, loading }) {
  const now = new Date();
  const [period, setPeriod] = useState("monthly");
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [week, setWeek] = useState(getISOWeek(now));

  function handleSubmit(e) {
    e.preventDefault();
    const payload = { period, year: Number(year) };
    if (period === "weekly") payload.week = Number(week);
    if (period === "monthly") payload.month = Number(month);
    onGenerate(payload);
  }

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h3>Generate Summary</h3>
      <label>
        Period
        <select value={period} onChange={(e) => setPeriod(e.target.value)}>
          {PERIODS.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </label>
      <label>
        Year
        <input type="number" value={year} min={2000} max={2100} onChange={(e) => setYear(e.target.value)} />
      </label>
      {period === "monthly" && (
        <label>
          Month (1–12)
          <input type="number" value={month} min={1} max={12} onChange={(e) => setMonth(e.target.value)} />
        </label>
      )}
      {period === "weekly" && (
        <label>
          ISO Week
          <input type="number" value={week} min={1} max={53} onChange={(e) => setWeek(e.target.value)} />
        </label>
      )}
      <button type="submit" disabled={loading}>
        {loading ? "Generating…" : "Generate"}
      </button>
    </form>
  );
}

function SummaryList({ summaries, selectedId, onSelect, onDelete, loading }) {
  if (!summaries.length) {
    return <div className="panel"><p>No summaries yet. Generate one above.</p></div>;
  }
  return (
    <div className="panel">
      <h3>Summaries</h3>
      <ul className="entry-list">
        {summaries.map((s) => (
          <li key={s.summaryId} className={s.summaryId === selectedId ? "selected" : ""}>
            <button className="link" onClick={() => onSelect(s)}>
              <strong>{s.periodLabel}</strong>
              <span className="meta">{s.period} · {s.aiStatus}</span>
            </button>
            <button className="danger" disabled={loading} onClick={() => onDelete(s.summaryId)}>
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SummaryDetail({ summary, onRegenerate, loading }) {
  if (!summary) {
    return <div className="panel"><p>Select a summary to view details.</p></div>;
  }

  return (
    <div className="panel">
      <div className="row between">
        <h2>{summary.periodLabel}</h2>
        <button className="secondary" disabled={loading} onClick={() => onRegenerate(summary.summaryId)}>
          {loading ? "Regenerating…" : "Regenerate"}
        </button>
      </div>

      <p><strong>Period:</strong> {summary.period} · <strong>Status:</strong> {summary.aiStatus}</p>
      <p><strong>Entries analysed:</strong> {summary.entryCount}</p>
      <p><strong>Date range:</strong> {summary.startDate} → {summary.endDate}</p>

      {summary.aiStatus === "ERROR" && (
        <p className="error">AI error: {summary.aiError}</p>
      )}

      {summary.narrative && (
        <>
          <h3>Narrative</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{summary.narrative}</p>
        </>
      )}

      {summary.mood && (
        <p><strong>Overall mood:</strong> {summary.mood}</p>
      )}

      {summary.themes?.length > 0 && (
        <>
          <h3>Themes</h3>
          <p className="tags">{summary.themes.join(" · ")}</p>
        </>
      )}

      {summary.highlights?.length > 0 && (
        <>
          <h3>Highlights</h3>
          <ul>
            {summary.highlights.map((h, i) => <li key={i}>{h}</li>)}
          </ul>
        </>
      )}

      {summary.reflection && (
        <>
          <h3>Reflection</h3>
          <p><em>{summary.reflection}</em></p>
        </>
      )}
    </div>
  );
}

export default function InsightsPanel({ insights }) {
  const { loading, error, summaries, selected, load, select, generate, remove, regenerate } = insights;

  useEffect(() => { load(); }, [load]);

  return (
    <section className="grid two">
      <div>
        <GenerateForm onGenerate={generate} loading={loading} />
        <SummaryList
          summaries={summaries}
          selectedId={selected?.summaryId}
          onSelect={select}
          onDelete={remove}
          loading={loading}
        />
      </div>
      <div>
        {error && <div className="panel error">{error}</div>}
        <SummaryDetail summary={selected} onRegenerate={regenerate} loading={loading} />
      </div>
    </section>
  );
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function getISOWeek(d) {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
}
