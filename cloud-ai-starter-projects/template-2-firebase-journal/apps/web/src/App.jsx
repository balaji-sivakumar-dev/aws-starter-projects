import { useEffect, useMemo, useState } from "react";

import { missingConfig } from "./config";
import { login, logout, observeAuth, register } from "./auth/firebase";
import AuthPanel from "./components/AuthPanel";
import EntryDetail from "./components/EntryDetail";
import EntryForm from "./components/EntryForm";
import EntryList from "./components/EntryList";
import ProfileCard from "./components/ProfileCard";
import { useJournalApp } from "./state/useJournalApp";

export default function App() {
  const missing = useMemo(() => missingConfig(), []);
  const [authUser, setAuthUser] = useState(null);
  const [authError, setAuthError] = useState("");
  const app = useJournalApp();

  useEffect(() => {
    const unsubscribe = observeAuth(async (user) => {
      setAuthUser(user || null);
      if (user) {
        await app.bootstrap();
      }
    });

    return () => unsubscribe();
  }, []);

  async function onLogin(email, password) {
    setAuthError("");
    try {
      await login(email, password);
    } catch (err) {
      setAuthError(err.message || "Login failed");
    }
  }

  async function onRegister(email, password) {
    setAuthError("");
    try {
      await register(email, password);
    } catch (err) {
      setAuthError(err.message || "Registration failed");
    }
  }

  if (missing.length) {
    return (
      <main className="layout">
        <div className="panel">
          <h1>Firebase Journal Starter</h1>
          <p>Missing configuration:</p>
          <ul>
            {missing.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      </main>
    );
  }

  if (!authUser) {
    return (
      <main className="layout">
        <AuthPanel onLogin={onLogin} onRegister={onRegister} error={authError} />
      </main>
    );
  }

  return (
    <main className="layout">
      <header className="panel row between">
        <h1>Firebase Journal Starter</h1>
        <button className="secondary" onClick={() => app.setMode("create")}>New Entry</button>
      </header>

      {app.error ? <div className="panel error">{app.error}</div> : null}
      {app.loading ? <div className="panel">Loading...</div> : null}

      <section className="grid two">
        <div>
          <ProfileCard me={app.me} authUser={authUser} onLogout={logout} />
          <EntryList
            items={app.entries}
            selectedId={app.selectedId}
            onSelect={app.selectEntry}
            onDelete={app.removeEntry}
            nextToken={app.nextToken}
            onMore={app.loadMore}
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
              onTriggerAi={app.triggerAi}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}
