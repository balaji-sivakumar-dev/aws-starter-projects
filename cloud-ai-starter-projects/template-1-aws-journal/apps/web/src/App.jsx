import { useEffect, useMemo, useState } from "react";

import { validateConfig } from "./config";
import { handleAuthCallback, isAuthenticated } from "./auth/auth";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import ProfileCard from "./components/ProfileCard";
import { useJournalApp } from "./state/useJournalApp";

export default function App() {
  const app = useJournalApp();
  const [callbackError, setCallbackError] = useState("");

  const missingConfig = useMemo(() => validateConfig(), []);

  useEffect(() => {
    async function init() {
      if (window.location.pathname === "/callback") {
        try {
          await handleAuthCallback();
          app.setAuthReady(isAuthenticated());
        } catch (err) {
          setCallbackError(err.message || "Login callback failed");
        }
      }

      if (isAuthenticated()) {
        await app.loadInitial();
      }
    }

    init();
  }, []);

  if (missingConfig.length > 0) {
    return (
      <main className="layout">
        <div className="panel">
          <h1>Journal Starter</h1>
          <p>Missing config values:</p>
          <ul>
            {missingConfig.map((key) => <li key={key}>{key}</li>)}
          </ul>
          <p>Use `.env.example` to configure the app.</p>
        </div>
      </main>
    );
  }

  if (!isAuthenticated()) {
    return (
      <main className="layout">
        <div className="panel">
          <h1>Journal Starter</h1>
          <p>Sign in with Cognito Hosted UI to access entries.</p>
          {callbackError ? <p className="error">{callbackError}</p> : null}
          <button onClick={app.loginWithHostedUi}>Login</button>
        </div>
      </main>
    );
  }

  return (
    <main className="layout">
      <header className="panel row between">
        <h1>Journal Starter</h1>
        <div className="row">
          <button className="secondary" onClick={() => app.setMode("create")}>New Entry</button>
        </div>
      </header>

      {app.error ? <div className="panel error">{app.error}</div> : null}
      {app.loading ? <div className="panel">Loading...</div> : null}

      <section className="grid two">
        <div>
          <ProfileCard me={app.me} idProfile={app.idProfile} onLogout={app.logout} />
          <EntryList
            items={app.entries}
            selectedId={app.selectedEntryId}
            onSelect={app.selectEntry}
            onDelete={app.removeEntry}
            nextToken={app.nextToken}
            onLoadMore={app.loadMore}
          />
        </div>

        <div>
          {app.mode === "create" ? (
            <EntryForm
              submitLabel="Create"
              onSubmit={app.saveCreate}
              onCancel={() => app.setMode("detail")}
            />
          ) : null}

          {app.mode === "edit" ? (
            <EntryForm
              initialValue={app.selectedEntry}
              submitLabel="Save"
              onSubmit={app.saveEdit}
              onCancel={() => app.setMode("detail")}
            />
          ) : null}

          {app.mode === "detail" ? (
            <EntryDetail
              entry={app.selectedEntry}
              onEdit={() => app.setMode("edit")}
              onTriggerAi={app.triggerAi}
              onRefresh={app.refreshSelected}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}
