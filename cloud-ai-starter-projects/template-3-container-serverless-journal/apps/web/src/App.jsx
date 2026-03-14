import { useEffect, useMemo, useState } from "react";

import { handleCallback, isAuthed, login, logout } from "./auth/auth";
import { isLocalMode, missingConfig } from "./config";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import InsightsPanel from "./components/InsightsPanel";
import { useInsights } from "./state/useInsights";
import { useJournal } from "./state/useJournal";

function initials(email, userId) {
  const str = email || userId;
  if (!str) return "?";
  if (str.includes("@")) {
    return str.split("@")[0].slice(0, 2).toUpperCase();
  }
  return str.split(/[\s._@-]+/).map((w) => w[0]).join("").toUpperCase().slice(0, 2) || "?";
}

export default function App() {
  const missing = useMemo(() => missingConfig(), []);
  const [authError, setAuthError] = useState("");
  const [tab, setTab] = useState("journal");
  const app = useJournal();
  const insights = useInsights();

  useEffect(() => {
    (async () => {
      if (window.location.pathname === "/callback") {
        try { await handleCallback(); }
        catch (err) { setAuthError(err.message || "Login callback failed"); return; }
      }
      if (isAuthed()) await app.bootstrap();
    })();
  }, []);

  // ── Missing config ──────────────────────────────────────────────────────────
  if (missing.length) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="auth-logo">◆</div>
          <h1 className="auth-title">Reflect</h1>
          <p className="auth-subtitle">Missing configuration:</p>
          <ul style={{ textAlign: "left", marginTop: "8px" }}>
            {missing.map((m) => <li key={m}><code>{m}</code></li>)}
          </ul>
        </div>
      </div>
    );
  }

  // ── Login screen ─────────────────────────────────────────────────────────────
  if (!isAuthed()) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="auth-logo">◆</div>
          <h1 className="auth-title">Reflect</h1>
          <p className="auth-subtitle">Your AI-powered journal</p>
          {authError && <p className="auth-error">{authError}</p>}
          <button className="btn-primary full-width" onClick={login}>Sign in</button>
        </div>
      </div>
    );
  }

  // ── Main app ────────────────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-logo">◆</span>
          <span className="brand-name">Reflect</span>
          {isLocalMode() && <span className="brand-badge">local</span>}
        </div>

        <nav className="sidebar-nav">
          <button className={`nav-item${tab === "journal" ? " active" : ""}`} onClick={() => setTab("journal")}>
            <span className="nav-icon">📝</span> Journal
          </button>
          <button className={`nav-item${tab === "insights" ? " active" : ""}`} onClick={() => setTab("insights")}>
            <span className="nav-icon">✦</span> Insights
          </button>
        </nav>

        {tab === "journal" && (
          <div className="sidebar-list-area">
            <div className="sidebar-list-header">
              <span className="sidebar-list-title">Entries</span>
              <button className="btn-new" onClick={() => app.setMode("create")}>+ New</button>
            </div>
            {app.error && <div className="sidebar-error">{app.error}</div>}
            <EntryList
              items={app.entries}
              loading={app.loading}
              selectedId={app.selectedId}
              onSelect={app.select}
              onDelete={app.remove}
              nextToken={app.nextToken}
              onMore={app.more}
            />
          </div>
        )}

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <span className="user-avatar">{initials(app.me?.email, app.me?.userId)}</span>
            <span className="user-name">{app.me?.email || app.me?.username || app.me?.userId || "—"}</span>
          </div>
          <button className="btn-logout" onClick={logout}>Sign out</button>
        </div>
      </aside>

      {/* ── Content ── */}
      <main className="content-area">
        {tab === "journal" && (
          <>
            {app.mode === "create" && (
              <EntryForm submitLabel="Create Entry" onSubmit={app.saveCreate} onCancel={() => app.setMode("detail")} />
            )}
            {app.mode === "edit" && (
              <EntryForm initial={app.selected} submitLabel="Save Changes" onSubmit={app.saveEdit} onCancel={() => app.setMode("detail")} />
            )}
            {app.mode === "detail" && (
              <EntryDetail
                entry={app.selected}
                onEdit={() => app.setMode("edit")}
                onRefresh={app.refresh}
                onTriggerAi={app.queueAi}
              />
            )}
          </>
        )}

        {tab === "insights" && <InsightsPanel insights={insights} />}
      </main>
    </div>
  );
}
