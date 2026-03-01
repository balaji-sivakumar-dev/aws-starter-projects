import { useState } from "react";

export default function AuthPanel({ onLogin, onRegister, error }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn) {
    setBusy(true);
    try {
      await fn(email.trim(), password);
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h1>Firebase Journal Starter</h1>
      <label>
        Email
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
      </label>
      <label>
        Password
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" minLength={6} required />
      </label>
      <div className="row">
        <button disabled={busy} onClick={() => run(onLogin)}>{busy ? "Working..." : "Login"}</button>
        <button className="secondary" disabled={busy} onClick={() => run(onRegister)}>Register</button>
      </div>
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
