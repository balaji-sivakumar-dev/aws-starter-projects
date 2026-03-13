import { useEffect, useMemo, useState } from "react";

import { handleCallback, isAuthed, login, logout } from "./auth/auth";
import { isLocalMode, missingConfig } from "./config";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import InsightsPanel from "./components/InsightsPanel";
import ProfileCard from "./components/ProfileCard";
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
      // Handle Cognito callback redirect (no-op in local mode)
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
      <main className="layout">
        <div className="panel">
          <h1>Template 3 Journal</h1>
          <p>Missing required configuration:</p>
          <ul>{missing.map((m) => <li key={m}><code>{m}</code></li>)}</ul>
          {isLocalMode() && (
            <p>Running in <strong>local mode</strong>. Set <code>VITE_API_BASE_URL</code> to the API address.</p>
          )}
        </div>
      </main>
    );
  }

  // ── Login screen (Cognito mode only) ────────────────────────────────────────
  if (!isAuthed()) {
    return (
      <main className="layout">
        <div className="panel">
          <h1>Template 3 Journal</h1>
          <p>Sign in with your Cognito account to continue.</p>
          {authError ? <p className="error">{authError}</p> : null}
          <button onClick={login}>Login</button>
        </div>
      </main>
    );
  }

  // ── Main app ────────────────────────────────────────────────────────────────
  return (
    <main className="layout">
      <header className="panel row between">
        <h1>
          Template 3 Journal
          {isLocalMode() && <span style={{ fontSize: "0.7em", marginLeft: "0.75rem", color: "#888" }}>local</span>}
        </h1>
        <div className="row">
          {tab === "journal" && (
            <button className="secondary" onClick={() => app.setMode("create")}>
              New Entry
            </button>
          )}
          <nav className="tabs">
            <button className={tab === "journal" ? "tab active" : "tab"} onClick={() => setTab("journal")}>
              Journal
            </button>
            <button className={tab === "insights" ? "tab active" : "tab"} onClick={() => setTab("insights")}>
              Insights
            </button>
          </nav>
        </div>
      </header>

      {app.error ? <div className="panel error">{app.error}</div> : null}
      {app.loading ? <div className="panel">Loading…</div> : null}

      {tab === "journal" && (
        <section className="grid two">
          <div>
            <ProfileCard me={app.me} onLogout={logout} />
            <EntryList
              items={app.entries}
              selectedId={app.selectedId}
              onSelect={app.select}
              onDelete={app.remove}
              nextToken={app.nextToken}
              onMore={app.more}
            />
          </div>

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
  );
}
