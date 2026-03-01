import { useEffect, useMemo, useState } from "react";

import { handleCallback, isAuthed, login, logout } from "./auth/auth";
import { missingConfig } from "./config";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import ProfileCard from "./components/ProfileCard";
import { useJournal } from "./state/useJournal";

export default function App() {
  const missing = useMemo(() => missingConfig(), []);
  const [authError, setAuthError] = useState("");
  const app = useJournal();

  useEffect(() => {
    (async () => {
      if (window.location.pathname === "/callback") {
        try {
          await handleCallback();
        } catch (err) {
          setAuthError(err.message || "Login callback failed");
        }
      }
      if (isAuthed()) {
        await app.bootstrap();
      }
    })();
  }, []);

  if (missing.length) {
    return (
      <main className="layout">
        <div className="panel">
          <h1>Template 3 Journal</h1>
          <p>Missing configuration:</p>
          <ul>{missing.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      </main>
    );
  }

  if (!isAuthed()) {
    return (
      <main className="layout">
        <div className="panel">
          <h1>Template 3 Journal</h1>
          <p>Sign in with Cognito Hosted UI.</p>
          {authError ? <p className="error">{authError}</p> : null}
          <button onClick={login}>Login</button>
        </div>
      </main>
    );
  }

  return (
    <main className="layout">
      <header className="panel row between">
        <h1>Template 3 Journal</h1>
        <button className="secondary" onClick={() => app.setMode("create")}>New Entry</button>
      </header>

      {app.error ? <div className="panel error">{app.error}</div> : null}
      {app.loading ? <div className="panel">Loading...</div> : null}

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
          {app.mode === "create" ? (
            <EntryForm submitLabel="Create" onSubmit={app.saveCreate} onCancel={() => app.setMode("detail")} />
          ) : null}

          {app.mode === "edit" ? (
            <EntryForm initial={app.selected} submitLabel="Save" onSubmit={app.saveEdit} onCancel={() => app.setMode("detail")} />
          ) : null}

          {app.mode === "detail" ? (
            <EntryDetail
              entry={app.selected}
              onEdit={() => app.setMode("edit")}
              onRefresh={app.refresh}
              onTriggerAi={app.queueAi}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}
