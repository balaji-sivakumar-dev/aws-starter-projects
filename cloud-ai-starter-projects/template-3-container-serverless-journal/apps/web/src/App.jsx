import { useEffect, useMemo, useState } from "react";

import { handleCallback, isAuthed, login, logout } from "./auth/auth";
import { isLocalMode, missingConfig } from "./config";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import InsightsPanel from "./components/InsightsPanel";
import { useInsights } from "./state/useInsights";
import { useJournal } from "./state/useJournal";

export default function App() {
  const missing = useMemo(() => missingConfig(), []);
  const [authError, setAuthError] = useState("");
  const [tab, setTab] = useState("journal");
  const app = useJournal();
  const insights = useInsights();

  useEffect(() => {
    (async () => {
      if (window.location.pathname === "/callback") {
        try {
          await handleCallback();
        } catch (err) {
          setAuthError(err.message || "Login callback failed");
          return;
        }
      }
      if (isAuthed()) {
        await app.bootstrap();
      }
    })();
  }, []);

  // ── Missing config ──────────────────────────────────────────────────────────
  if (missing.length) {
    return (
      <>
        <header className="navbar">
          <span className="navbar-brand">Template 3 Journal</span>
        </header>
        <main className="layout">
          <div className="panel">
            <p>Missing required configuration:</p>
            <ul>{missing.map((m) => <li key={m}><code>{m}</code></li>)}</ul>
            {isLocalMode() && (
              <p>Running in <strong>local mode</strong>. Set <code>VITE_API_BASE_URL</code> to the API address.</p>
            )}
          </div>
        </main>
      </>
    );
  }

  // ── Login screen (Cognito mode only) ────────────────────────────────────────
  if (!isAuthed()) {
    return (
      <>
        <header className="navbar">
          <span className="navbar-brand">Template 3 Journal</span>
        </header>
        <main className="layout">
          <div className="panel">
            <p>Sign in with your Cognito account to continue.</p>
            {authError ? <p className="error">{authError}</p> : null}
            <button onClick={login}>Login</button>
          </div>
        </main>
      </>
    );
  }

  // ── Main app ────────────────────────────────────────────────────────────────
  return (
    <>
      <header className="navbar">
        <span className="navbar-brand">
          Template 3 Journal
          {isLocalMode() && <span className="navbar-mode-badge">local</span>}
        </span>

        <nav className="tabs">
          <button className={tab === "journal" ? "tab active" : "tab"} onClick={() => setTab("journal")}>
            Journal
          </button>
          <button className={tab === "insights" ? "tab active" : "tab"} onClick={() => setTab("insights")}>
            Insights
          </button>
        </nav>

        <div className="navbar-actions">
          {tab === "journal" && (
            <button className="secondary sm" onClick={() => app.setMode("create")}>
              New Entry
            </button>
          )}
          {app.me?.userId && (
            <span className="navbar-user">{app.me.userId}</span>
          )}
          <button className="secondary sm" onClick={logout}>Logout</button>
        </div>
      </header>

      <main className="layout">
        {app.error ? <div className="panel error">{app.error}</div> : null}
        {app.loading ? <div className="panel">Loading…</div> : null}

        {tab === "journal" && (
          <section className="grid two">
            <EntryList
              items={app.entries}
              selectedId={app.selectedId}
              onSelect={app.select}
              onDelete={app.remove}
              nextToken={app.nextToken}
              onMore={app.more}
            />

            <div>
              {app.mode === "create" && (
                <EntryForm submitLabel="Create" onSubmit={app.saveCreate} onCancel={() => app.setMode("detail")} />
              )}
              {app.mode === "edit" && (
                <EntryForm initial={app.selected} submitLabel="Save" onSubmit={app.saveEdit} onCancel={() => app.setMode("detail")} />
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
          </section>
        )}

        {tab === "insights" && <InsightsPanel insights={insights} />}
      </main>
    </>
  );
}
