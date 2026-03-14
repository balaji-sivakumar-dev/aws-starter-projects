import { useEffect } from "react";

const MONTH = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${MONTH[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

const MOOD_EMOJI = {
  positive: "😊",
  reflective: "🤔",
  challenging: "💪",
  mixed: "🌤️",
  neutral: "😐",
};

/**
 * Derive a friendly first name for the greeting.
 *
 * Priority:
 *  1. given_name from Cognito id_token (only if the user pool exposes it)
 *  2. Local-part of email split at first separator, then capitalised
 *       "john.doe@company.com"  →  "John"
 *       "jsmith@gmail.com"      →  "Jsmith"
 *  3. null  →  greeting stays generic ("Welcome back!")
 */
function deriveName(me) {
  if (me?.givenName) return me.givenName;
  if (!me?.email) return null;
  const local = me.email.split("@")[0];              // "john.doe"
  const part  = local.split(/[._\-+]/)[0] || local;  // "john"
  return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase(); // "John"
}

export default function Dashboard({ me, entries, summaries, onNewEntry, onViewJournal, onViewInsights, onLoadInsights }) {
  useEffect(() => {
    onLoadInsights?.();
  }, []);

  const enrichedCount = entries.filter((e) => e.aiStatus === "COMPLETE").length;
  const recentEntries = entries.slice(0, 3);
  const latestSummary = summaries?.[0] || null;
  const firstName = deriveName(me);

  return (
    <div className="dashboard">

      {/* ── Hero ── */}
      <div className="dashboard-hero">
        <h1 className="dashboard-greeting">
          Welcome back{firstName ? `, ${firstName}` : ""}! 👋
        </h1>
        <p className="dashboard-subtitle">
          Reflect is your private AI-powered journal — write freely, discover patterns, and gain deeper insights over time.
        </p>
      </div>

      {/* ── Stats ── */}
      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-value">{entries.length}{entries.length >= 20 ? "+" : ""}</div>
          <div className="stat-label">Journal Entries</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{enrichedCount}</div>
          <div className="stat-label">AI Enriched</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{summaries.length}</div>
          <div className="stat-label">Insights Generated</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-value--date">{fmtDate(entries[0]?.createdAt)}</div>
          <div className="stat-label">Latest Entry</div>
        </div>
      </div>

      {/* ── Main grid ── */}
      <div className="dashboard-grid">

        {/* Recent entries */}
        <section className="dashboard-section">
          <div className="dashboard-section-header">
            <h2>Recent Entries</h2>
            <button className="btn-link" onClick={() => onViewJournal()}>View all →</button>
          </div>

          {recentEntries.length === 0 ? (
            <div className="dashboard-empty">
              <p>No entries yet — start your journal today.</p>
              <button className="btn-primary btn-sm" style={{ marginTop: "12px" }} onClick={onNewEntry}>
                Write your first entry
              </button>
            </div>
          ) : (
            <div className="dashboard-entry-list">
              {recentEntries.map((e) => (
                <div
                  key={e.entryId}
                  className="dashboard-entry-card"
                  onClick={() => onViewJournal(e.entryId)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(ev) => ev.key === "Enter" && onViewJournal(e.entryId)}
                >
                  <div className="dash-entry-header">
                    <span className="dash-entry-title">{e.title}</span>
                    {e.aiStatus === "COMPLETE" && <span className="dash-badge-ai">✦ AI</span>}
                  </div>
                  <div className="dash-entry-date">{fmtDate(e.createdAt)}</div>
                  {e.summary && <div className="dash-entry-summary">{e.summary}</div>}
                </div>
              ))}
            </div>
          )}

          <button className="btn-primary btn-sm" style={{ marginTop: "12px" }} onClick={onNewEntry}>
            + New Entry
          </button>
        </section>

        {/* Latest insight */}
        <section className="dashboard-section">
          <div className="dashboard-section-header">
            <h2>Latest Insight</h2>
            <button className="btn-link" onClick={onViewInsights}>View all →</button>
          </div>

          {!latestSummary ? (
            <div className="dashboard-empty">
              <p>No insights yet. Generate a weekly or monthly summary from your entries.</p>
              <button className="btn-primary btn-sm" style={{ marginTop: "12px" }} onClick={onViewInsights}>
                Generate insight
              </button>
            </div>
          ) : (
            <div className="dashboard-insight-card">
              <div className="dash-insight-period">
                <span className="dash-insight-emoji">{MOOD_EMOJI[latestSummary.mood] || "✦"}</span>
                {latestSummary.periodLabel}
              </div>

              {latestSummary.mood && (
                <div className="dash-insight-mood">
                  Mood: <strong>{latestSummary.mood}</strong>
                </div>
              )}

              {latestSummary.aiStatus === "COMPLETE" && latestSummary.narrative ? (
                <>
                  <p className="dash-insight-narrative">{latestSummary.narrative}</p>
                  {latestSummary.themes?.length > 0 && (
                    <div className="dash-insight-themes">
                      {latestSummary.themes.map((t) => (
                        <span key={t} className="tag">{t}</span>
                      ))}
                    </div>
                  )}
                  {latestSummary.reflection && (
                    <p className="dash-insight-reflection">"{latestSummary.reflection}"</p>
                  )}
                </>
              ) : (
                <p className="dash-insight-pending">
                  {latestSummary.aiStatus === "QUEUED" || latestSummary.aiStatus === "PROCESSING"
                    ? "⏳ AI analysis in progress…"
                    : "Click Regenerate in Insights to run AI analysis."}
                </p>
              )}

              <div className="dash-insight-meta">
                {latestSummary.entryCount} entries · {fmtDate(latestSummary.createdAt)}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* ── About ── */}
      <section className="dashboard-about">
        <h2>What can Reflect do?</h2>
        <div className="about-grid">
          <div className="about-card">
            <div className="about-icon">📝</div>
            <h3>Private Journal</h3>
            <p>Write daily entries about work, life, and ideas. Everything is stored securely and belongs only to you.</p>
          </div>
          <div className="about-card">
            <div className="about-icon">✦</div>
            <h3>AI Enrichment</h3>
            <p>Each entry can be automatically summarised and tagged by AI, making it easy to search and spot recurring themes.</p>
          </div>
          <div className="about-card">
            <div className="about-icon">📊</div>
            <h3>Period Insights</h3>
            <p>Generate weekly, monthly, or yearly summaries with mood analysis, highlights, and personal reflections powered by AI.</p>
          </div>
        </div>
      </section>

    </div>
  );
}
