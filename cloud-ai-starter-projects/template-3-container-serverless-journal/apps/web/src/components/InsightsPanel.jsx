import { useEffect, useState } from "react";

const PERIODS = ["weekly", "monthly", "yearly"];
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

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
    <div className="card">
      <div className="section-title">Generate Summary</div>
      <form onSubmit={handleSubmit}>
        <label>
          Period
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            {PERIODS.map((p) => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
          </select>
        </label>
        <div className="form-row">
          <label>
            Year
            <input type="number" value={year} min={2000} max={2100} onChange={(e) => setYear(e.target.value)} />
          </label>
          {period === "monthly" && (
            <label>
              Month
              <select value={month} onChange={(e) => setMonth(e.target.value)}>
                {MONTHS.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
              </select>
            </label>
          )}
          {period === "weekly" && (
            <label>
              ISO Week
              <input type="number" value={week} min={1} max={53} onChange={(e) => setWeek(e.target.value)} />
            </label>
          )}
        </div>
        <button type="submit" className="btn-ai" disabled={loading} style={{ width: "100%", marginTop: "4px" }}>
          {loading ? "Generating…" : "✦ Generate AI Summary"}
        </button>
      </form>
    </div>
  );
}

function SummaryList({ summaries, selectedId, onSelect, onDelete, loading }) {
  if (!summaries.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">✦</div>
        <div className="empty-state-text">No summaries yet.<br />Generate one above.</div>
      </div>
    );
  }
  return (
    <div className="card">
      <div className="section-title">Summaries</div>
      <ul className="summary-list">
        {summaries.map((s) => (
          <li key={s.summaryId} className={`summary-item${s.summaryId === selectedId ? " selected" : ""}`} onClick={() => onSelect(s)}>
            <div>
              <div className="summary-item-label">{s.periodLabel}</div>
              <div className="summary-item-meta">{s.period} · {s.aiStatus}</div>
            </div>
            <button
              className="btn-ghost"
              style={{ fontSize: "0.75rem", padding: "3px 8px", color: "var(--red)", borderColor: "var(--red-light)" }}
              disabled={loading}
              onClick={(e) => { e.stopPropagation(); onDelete(s.summaryId); }}
            >
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
    return (
      <div className="empty-state" style={{ marginTop: "40px" }}>
        <div className="empty-state-icon">📊</div>
        <div className="empty-state-text">Select a summary to view its insights</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="insight-card-header">
        <h2 className="insight-period-title">{summary.periodLabel}</h2>
        <button className="btn-ai" disabled={loading} onClick={() => onRegenerate(summary.summaryId)}>
          {loading ? "…" : "↻ Regenerate"}
        </button>
      </div>

      <div className="insight-meta-row">
        <span>📅 {summary.startDate} → {summary.endDate}</span>
        <span>📝 {summary.entryCount} entries</span>
        <span>Status: {summary.aiStatus}</span>
      </div>

      {summary.aiStatus === "ERROR" && (
        <div className="error-text" style={{ marginBottom: "14px" }}>AI error: {summary.aiError}</div>
      )}

      {summary.mood && (
        <div className="insight-mood">🌡 Mood: {summary.mood}</div>
      )}

      {summary.narrative && (
        <div className="insight-section">
          <div className="insight-section-label">Narrative</div>
          <div className="insight-narrative">{summary.narrative}</div>
        </div>
      )}

      {summary.themes?.length > 0 && (
        <div className="insight-section">
          <div className="insight-section-label">Themes</div>
          <div className="insight-themes">
            {summary.themes.map((t, i) => <span key={i} className="insight-theme">{t}</span>)}
          </div>
        </div>
      )}

      {summary.highlights?.length > 0 && (
        <div className="insight-section">
          <div className="insight-section-label">Highlights</div>
          <ul className="insight-highlights">
            {summary.highlights.map((h, i) => <li key={i}>{h}</li>)}
          </ul>
        </div>
      )}

      {summary.reflection && (
        <div className="insight-section">
          <div className="insight-section-label">Reflection</div>
          <div className="insight-reflection">{summary.reflection}</div>
        </div>
      )}
    </div>
  );
}

export default function InsightsPanel({ insights }) {
  const { loading, error, summaries, selected, load, select, generate, remove, regenerate } = insights;
  useEffect(() => { load(); }, [load]);

  return (
    <div className="insights-layout">
      <div>
        <GenerateForm onGenerate={generate} loading={loading} />
        {error && <div className="error-text" style={{ marginBottom: "12px" }}>{error}</div>}
        <SummaryList summaries={summaries} selectedId={selected?.summaryId} onSelect={select} onDelete={remove} loading={loading} />
      </div>
      <SummaryDetail summary={selected} onRegenerate={regenerate} loading={loading} />
    </div>
  );
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function getISOWeek(d) {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
}
