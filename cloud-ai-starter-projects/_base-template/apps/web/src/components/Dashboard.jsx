import { useEffect } from "react";

const MONTH = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function fmtDate(iso) {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return `${MONTH[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

const MOOD_EMOJI = {
  positive: "\ud83d\ude0a",
  reflective: "\ud83e\udd14",
  challenging: "\ud83d\udcaa",
  mixed: "\ud83c\udf24\ufe0f",
  neutral: "\ud83d\ude10",
};

function deriveName(me) {
  if (me?.givenName) return me.givenName;
  if (!me?.email) return null;
  const local = me.email.split("@")[0];
  const part  = local.split(/[._\-+]/)[0] || local;
  return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
}

export default function Dashboard({ me, entries, summaries, onNewEntry, onViewItems, onViewInsights, onViewAsk, onLoadInsights }) {
  useEffect(() => {
    onLoadInsights?.();
  }, []);

  const enrichedCount = entries.filter((e) => e.aiStatus === "COMPLETE").length;
  const recentItems = entries.slice(0, 3);
  const latestSummary = summaries?.[0] || null;
  const firstName = deriveName(me);

  return (
    <div className="dashboard">

      {/* -- Hero -- */}
      <div className="dashboard-hero">
        <h1 className="dashboard-greeting">
          Welcome back{firstName ? `, ${firstName}` : ""}!
        </h1>
        <p className="dashboard-subtitle">
          Your personal workspace with AI-powered features.
        </p>
      </div>

      {/* -- Stats -- */}
      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-value">{entries.length}{entries.length >= 20 ? "+" : ""}</div>
          <div className="stat-label">Items</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{enrichedCount}</div>
          <div className="stat-label">AI Enriched</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{summaries.length}</div>
          <div className="stat-label">Insights</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-value--date">{fmtDate(entries[0]?.createdAt)}</div>
          <div className="stat-label">Latest</div>
        </div>
      </div>

      {/* -- Main grid -- */}
      <div className="dashboard-grid">

        {/* Recent items */}
        <section className="dashboard-section">
          <div className="dashboard-section-header">
            <h2>Recent Items</h2>
            <button className="btn-link" onClick={() => onViewItems()}>View all &rarr;</button>
          </div>

          {recentItems.length === 0 ? (
            <div className="dashboard-empty">
              <p>No items yet. Create your first one.</p>
              <button className="btn-primary btn-sm" style={{ marginTop: "12px" }} onClick={onNewEntry}>
                Create first item
              </button>
            </div>
          ) : (
            <div className="dashboard-entry-list">
              {recentItems.map((e) => (
                <div
                  key={e.entryId || e.itemId}
                  className="dashboard-entry-card"
                  onClick={() => onViewItems(e.entryId || e.itemId)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(ev) => ev.key === "Enter" && onViewItems(e.entryId || e.itemId)}
                >
                  <div className="dash-entry-header">
                    <span className="dash-entry-title">{e.title}</span>
                    {e.aiStatus === "COMPLETE" && <span className="dash-badge-ai">AI</span>}
                  </div>
                  <div className="dash-entry-date">{fmtDate(e.createdAt)}</div>
                  {e.summary && <div className="dash-entry-summary">{e.summary}</div>}
                </div>
              ))}
            </div>
          )}

          <button className="btn-primary btn-sm" style={{ marginTop: "12px" }} onClick={onNewEntry}>
            + New Item
          </button>
        </section>

        {/* Latest insight */}
        <section className="dashboard-section">
          <div className="dashboard-section-header">
            <h2>Latest Insight</h2>
            <button className="btn-link" onClick={onViewInsights}>View all &rarr;</button>
          </div>

          {!latestSummary ? (
            <div className="dashboard-empty">
              <p>No insights yet. Generate a weekly or monthly summary from your items.</p>
              <button className="btn-primary btn-sm" style={{ marginTop: "12px" }} onClick={onViewInsights}>
                Generate insight
              </button>
            </div>
          ) : (
            <div className="dashboard-insight-card">
              <div className="dash-insight-period">
                <span className="dash-insight-emoji">{MOOD_EMOJI[latestSummary.mood] || "*"}</span>
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
                    ? "AI analysis in progress..."
                    : "Click Regenerate in Insights to run AI analysis."}
                </p>
              )}

              <div className="dash-insight-meta">
                {latestSummary.entryCount} items &middot; {fmtDate(latestSummary.createdAt)}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* -- About -- */}
      <section className="dashboard-about">
        <h2>What can {{APP_TITLE}} do?</h2>
        <div className="about-grid">
          <div className="about-card">
            <div className="about-icon">*</div>
            <h3>Manage Items</h3>
            <p>Create, edit, and organise items. Everything is stored securely in DynamoDB.</p>
          </div>
          <div className="about-card">
            <div className="about-icon">*</div>
            <h3>AI Enrichment</h3>
            <p>Each item can be automatically summarised and tagged by AI, making it easy to search and spot patterns.</p>
          </div>
          <div className="about-card">
            <div className="about-icon">*</div>
            <h3>Period Insights</h3>
            <p>Generate weekly, monthly, or yearly summaries with analysis, highlights, and reflections powered by AI.</p>
          </div>
          <div className="about-card about-card--cta" role="button" tabIndex={0}
               onClick={onViewAsk}
               onKeyDown={(e) => e.key === "Enter" && onViewAsk?.()}>
            <div className="about-icon">*</div>
            <h3>Ask</h3>
            <p>Chat with your data using AI. Ask questions and get answers grounded in your items.</p>
            {onViewAsk && <span className="about-card-link">Try Ask &rarr;</span>}
          </div>
        </div>
      </section>

    </div>
  );
}
