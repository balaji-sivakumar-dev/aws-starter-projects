import { useEffect, useMemo, useState, useCallback } from "react";

import { getIdTokenClaims, handleCallback, isAuthed, login, logout, userEmail } from "./auth/auth";
import { isLocalMode, missingConfig } from "./config";
import Dashboard from "./components/Dashboard";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import AdminPanel from "./components/AdminPanel";
import AskJournal from "./components/AskJournal";
import ImportCSV from "./components/ImportCSV";
import InsightsPanel from "./components/InsightsPanel";
import ProviderSelector from "./components/ProviderSelector";
import { useInsights } from "./state/useInsights";
import { useJournal } from "./state/useJournal";
import { useProvider } from "./state/useProvider";

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
  const [menuOpen, setMenuOpen] = useState(false);
  const [journalView, setJournalView] = useState("list"); // "list" or "detail" — mobile only
  const provider = useProvider();
  const app = useJournal(provider.selected);
  const insights = useInsights(provider.selected);

  const switchTab = useCallback((t) => {
    setTab(t);
    setMenuOpen(false);
  }, []);

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

  // When selecting a journal entry on mobile, switch to detail view
  const handleSelectEntry = (entryId) => {
    app.select(entryId);
    setJournalView("detail");
  };

  // ── Main app ──────────────────────────────────────────────────────────────
  return (
    <div className="app">

      {/* ── Top navigation bar ── */}
      <header className="topnav">
        <div className="topnav-brand">
          <button className="hamburger" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">
            <span className={`hamburger-line${menuOpen ? " open" : ""}`} />
            <span className={`hamburger-line${menuOpen ? " open" : ""}`} />
            <span className={`hamburger-line${menuOpen ? " open" : ""}`} />
          </button>
          <span className="brand-logo">◆</span>
          <span className="brand-name">Reflect</span>
          {isLocalMode() && <span className="brand-badge">local</span>}
        </div>

        <nav className={`topnav-nav${menuOpen ? " mobile-open" : ""}`}>
          <button className={`nav-item${tab === "home" ? " active" : ""}`} onClick={() => switchTab("home")}>
            <span className="nav-icon">🏠</span> Home
          </button>
          <button className={`nav-item${tab === "journal" ? " active" : ""}`} onClick={() => switchTab("journal")}>
            <span className="nav-icon">📝</span> Journal
          </button>
          <button className={`nav-item${tab === "insights" ? " active" : ""}`} onClick={() => switchTab("insights")}>
            <span className="nav-icon">✦</span> Insights
          </button>
          <button className={`nav-item${tab === "ask" ? " active" : ""}`} onClick={() => switchTab("ask")}>
            <span className="nav-icon">💬</span> Ask
          </button>
          {isAdmin && (
            <button className={`nav-item${tab === "admin" ? " active" : ""}`} onClick={() => switchTab("admin")}>
              <span className="nav-icon">⚙</span> Admin
            </button>
          )}
          {/* Mobile-only: provider selector inside the menu */}
          {provider.providers.length >= 1 && (
            <div className="mobile-menu-provider">
              <ProviderSelector
                providers={provider.providers}
                selected={provider.selected}
                onSelect={provider.select}
              />
            </div>
          )}
          {/* Mobile-only: show user info + sign out inside the menu */}
          <div className="mobile-menu-user">
            <span className="user-avatar">{initials(email || app.me?.userId)}</span>
            <span className="user-name">{displayName}</span>
            <button className="btn-logout" onClick={logout}>Sign out</button>
          </div>
        </nav>

        {/* Provider selector — desktop topnav */}
        {provider.providers.length >= 1 && (
          <div className="topnav-provider desktop-only">
            <ProviderSelector
              providers={provider.providers}
              selected={provider.selected}
              onSelect={provider.select}
            />
          </div>
        )}

        <div className="topnav-user desktop-only">
          <span className="user-avatar">{initials(email || app.me?.userId)}</span>
          <span className="user-name">{displayName}</span>
          <button className="btn-logout" onClick={logout}>Sign out</button>
        </div>
      </header>

      {/* Mobile menu overlay */}
      {menuOpen && <div className="menu-overlay" onClick={() => setMenuOpen(false)} />}

      {/* ── Content ── */}
      <main className="content-area">

        {tab === "home" && (
          <div className="page-view">
            <Dashboard
              me={{ ...app.me, email, givenName }}
              entries={app.entries}
              summaries={insights.summaries}
              onLoadInsights={insights.load}
              onNewEntry={() => { switchTab("journal"); app.setMode("create"); setJournalView("detail"); }}
              onViewJournal={(entryId) => {
                switchTab("journal");
                if (entryId) { app.select(entryId); setJournalView("detail"); }
              }}
              onViewInsights={() => switchTab("insights")}
            />
          </div>
        )}

        {tab === "journal" && (
          <div className="journal-layout">
            <aside className={`journal-panel${journalView === "detail" ? " mobile-hidden" : ""}`}>
              <div className="sidebar-list-header">
                <span className="sidebar-list-title">Entries</span>
                <button className="btn-ghost btn-import" title="Import CSV" onClick={() => { app.setMode("import"); setJournalView("detail"); }}>⬆ CSV</button>
                <button className="btn-new" onClick={() => { app.setMode("create"); setJournalView("detail"); }}>+ New</button>
              </div>
              {app.error && <div className="sidebar-error">{app.error}</div>}
              <EntryList
                items={app.entries}
                loading={app.loading}
                selectedId={app.selectedId}
                onSelect={handleSelectEntry}
                onDelete={app.remove}
                nextToken={app.nextToken}
                onMore={app.more}
                totalCount={app.totalCount}
                checkedIds={app.checkedIds}
                onToggleCheck={app.toggleCheck}
                onCheckAll={app.checkAll}
                onClearChecked={app.clearChecked}
                onDeleteMany={app.removeMany}
              />
            </aside>

            <div className={`journal-detail${journalView === "list" ? " mobile-hidden" : ""}`}>
              {/* Mobile back button */}
              <button className="mobile-back-btn" onClick={() => setJournalView("list")}>
                ← Entries
              </button>
              {app.mode === "import" && (
                <ImportCSV
                  onDone={async (count) => {
                    await app.bootstrap();
                    app.setMode("detail");
                    setJournalView("list");
                  }}
                  onCancel={() => { app.setMode("detail"); setJournalView("list"); }}
                />
              )}
              {app.mode === "create" && (
                <EntryForm submitLabel="Create Entry" onSubmit={app.saveCreate} onCancel={() => { app.setMode("detail"); setJournalView("list"); }} />
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
            <AskJournal providerName={provider.selected} />
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
