import { useEffect, useMemo, useState } from "react";

import { getIdTokenClaims, handleCallback, isAuthed, login, logout, userEmail } from "./auth/auth";
import { isLocalMode, missingConfig } from "./config";
import Dashboard from "./components/Dashboard";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import AdminPanel from "./components/AdminPanel";
import AskJournal from "./components/AskJournal";
import InsightsPanel from "./components/InsightsPanel";
import { useInsights } from "./state/useInsights";
import { useJournal } from "./state/useJournal";

function initials(str) {
  if (!str) return "?";
  if (str.includes("@")) {
    return str.split("@")[0].slice(0, 2).toUpperCase();
  }
  return str.split(/[\s._@-]+/).map((w) => w[0]).join("").toUpperCase().slice(0, 2) || "?";
}

export default function App() {
  const missing = useMemo(() => missingConfig(), []);
  const [authError, setAuthError] = useState("");
  const [tab, setTab] = useState("home");
  const app = useJournal();
  const insights = useInsights();

  // id_token carries email + given_name; access token does not
  const idClaims = getIdTokenClaims();
  const email = idClaims?.email || app.me?.email || null;
  const givenName = idClaims?.given_name || null;
  const displayName = email || app.me?.username || "User";
  const isAdmin = app.me?.isAdmin ?? false;

  useEffect(() => {
    (async () => {
      if (window.location.pathname === "/callback") {
        try { await handleCallback(); }
        catch (err) { setAuthError(err.message || "Login callback failed"); return; }
      }
      if (isAuthed()) await app.bootstrap();
    })();
  }, []);

  // ── Missing config ────────────────────────────────────────────────────────
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

  // ── Login screen ──────────────────────────────────────────────────────────
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

  // ── Main app ──────────────────────────────────────────────────────────────
  return (
    <div className="app">

      {/* ── Top navigation bar ── */}
      <header className="topnav">
        <div className="topnav-brand">
          <span className="brand-logo">◆</span>
          <span className="brand-name">Reflect</span>
          {isLocalMode() && <span className="brand-badge">local</span>}
        </div>

        <nav className="topnav-nav">
          <button
            className={`nav-item${tab === "home" ? " active" : ""}`}
            onClick={() => setTab("home")}
          >
            <span className="nav-icon">🏠</span> Home
          </button>
          <button
            className={`nav-item${tab === "journal" ? " active" : ""}`}
            onClick={() => setTab("journal")}
          >
            <span className="nav-icon">📝</span> Journal
          </button>
          <button
            className={`nav-item${tab === "insights" ? " active" : ""}`}
            onClick={() => setTab("insights")}
          >
            <span className="nav-icon">✦</span> Insights
          </button>
          <button
            className={`nav-item${tab === "ask" ? " active" : ""}`}
            onClick={() => setTab("ask")}
          >
            <span className="nav-icon">💬</span> Ask
          </button>
          {isAdmin && (
            <button
              className={`nav-item${tab === "admin" ? " active" : ""}`}
              onClick={() => setTab("admin")}
            >
              <span className="nav-icon">⚙</span> Admin
            </button>
          )}
        </nav>

        <div className="topnav-user">
          <span className="user-avatar">{initials(email || app.me?.userId)}</span>
          <span className="user-name">{displayName}</span>
          <button className="btn-logout" onClick={logout}>Sign out</button>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="content-area">

        {tab === "home" && (
          <div className="page-view">
            <Dashboard
              me={{ ...app.me, email, givenName }}
              entries={app.entries}
              summaries={insights.summaries}
              onLoadInsights={insights.load}
              onNewEntry={() => { setTab("journal"); app.setMode("create"); }}
              onViewJournal={(entryId) => {
                setTab("journal");
                if (entryId) app.select(entryId);
              }}
              onViewInsights={() => setTab("insights")}
            />
          </div>
        )}

        {tab === "journal" && (
          <div className="journal-layout">
            <aside className="journal-panel">
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
            </aside>

            <div className="journal-detail">
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
            </div>
          </div>
        )}

        {tab === "insights" && (
          <div className="page-view">
            <InsightsPanel insights={insights} />
          </div>
        )}

        {tab === "ask" && (
          <div className="page-view">
            <AskJournal />
          </div>
        )}

        {tab === "admin" && (
          <div className="page-view">
            <AdminPanel />
          </div>
        )}

      </main>
    </div>
  );
}
