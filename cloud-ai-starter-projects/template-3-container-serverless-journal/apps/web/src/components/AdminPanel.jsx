import { useEffect, useState } from "react";
import { getMetrics, getAuditLogs, listUsers, adminRagStatus } from "../api/admin";

export default function AdminPanel() {
  const [metrics, setMetrics] = useState(null);
  const [users, setUsers] = useState([]);
  const [audit, setAudit] = useState(null);
  const [ragInfo, setRagInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Audit filters
  const [auditDate, setAuditDate] = useState("");
  const [auditUserId, setAuditUserId] = useState("");

  const [metricsDays, setMetricsDays] = useState(7);

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [m, u, a, r] = await Promise.all([
        getMetrics(metricsDays).catch(() => null),
        listUsers().catch(() => null),
        getAuditLogs("", "", 200).catch(() => null),
        adminRagStatus().catch(() => null),
      ]);
      setMetrics(m);
      setUsers(u?.users || []);
      setAudit(a);
      setRagInfo(r);
    } catch (err) {
      setError(err.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }

  async function refreshMetrics(days) {
    try { setMetrics(await getMetrics(days)); } catch {}
  }

  async function refreshAudit(date, userId) {
    try { setAudit(await getAuditLogs(date, userId, 200)); } catch {}
  }

  if (loading) {
    return (
      <div className="admin-container">
        <h2>Admin Dashboard</h2>
        <p className="admin-loading">Loading admin data…</p>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <h2>Admin Dashboard</h2>
      {error && <p className="admin-error">{error}</p>}

      {/* Metrics */}
      <div className="admin-section">
        <div className="admin-section-header">
          <h3>Usage Metrics</h3>
          <div className="admin-section-controls">
            <select
              value={metricsDays}
              onChange={(e) => {
                const d = Number(e.target.value);
                setMetricsDays(d);
                refreshMetrics(d);
              }}
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </select>
          </div>
        </div>
        {metrics && (
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-value">{metrics.activeUsers || 0}</div>
              <div className="metric-label">Active Users</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.totalAiCalls || 0}</div>
              <div className="metric-label">AI Calls</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.totalRagQueries || 0}</div>
              <div className="metric-label">RAG Queries</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.totalUserActions || 0}</div>
              <div className="metric-label">User Actions</div>
            </div>
          </div>
        )}
        {metrics?.aiCallsByProvider && Object.keys(metrics.aiCallsByProvider).length > 0 && (
          <div className="metrics-breakdown">
            <h4>AI Calls by Provider</h4>
            <div className="breakdown-list">
              {Object.entries(metrics.aiCallsByProvider).map(([k, v]) => (
                <div key={k} className="breakdown-item">
                  <span className="breakdown-key">{k}</span>
                  <span className="breakdown-val">{v}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Users */}
      <div className="admin-section">
        <h3>Users ({users.length})</h3>
        {users.length > 0 ? (
          <div className="admin-user-list">
            {users.map((u) => (
              <div
                key={u.userId}
                className={`admin-user-item${auditUserId === u.userId ? " selected" : ""}`}
                onClick={() => {
                  const next = auditUserId === u.userId ? "" : u.userId;
                  setAuditUserId(next);
                  refreshAudit(auditDate, next);
                }}
                title="Click to filter audit log by this user"
              >
                <div className="admin-user-primary">
                  <span className="admin-user-email">{u.email || "—"}</span>
                  {u.username && <span className="admin-user-name">{u.username}</span>}
                </div>
                <span className="admin-user-uuid" title={u.userId}>{u.userId}</span>
                {u.lastSeen && (
                  <span className="admin-user-last-seen">last seen {u.lastSeen.slice(0, 10)}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="admin-note">No users found in audit log yet.</p>
        )}
      </div>

      {/* RAG Status */}
      <div className="admin-section">
        <h3>RAG Index</h3>
        {ragInfo ? (
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-value">{ragInfo.totalVectors || 0}</div>
              <div className="metric-label">Total Vectors</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{ragInfo.totalUsers || 0}</div>
              <div className="metric-label">Users Indexed</div>
            </div>
          </div>
        ) : (
          <p className="admin-note">RAG status unavailable</p>
        )}
      </div>

      {/* Audit Logs */}
      <div className="admin-section">
        <div className="admin-section-header">
          <h3>
            Audit Log
            {auditUserId && users.find((u) => u.userId === auditUserId) && (
              <span className="audit-user-filter-badge">
                {users.find((u) => u.userId === auditUserId)?.email || auditUserId.slice(0, 8)}
              </span>
            )}
          </h3>
          <div className="admin-section-controls">
            {auditUserId && (
              <button
                className="btn-ghost"
                onClick={() => { setAuditUserId(""); refreshAudit(auditDate, ""); }}
              >
                ✕ Clear filter
              </button>
            )}
            <select
              value={auditUserId}
              onChange={(e) => {
                setAuditUserId(e.target.value);
                refreshAudit(auditDate, e.target.value);
              }}
            >
              <option value="">All users</option>
              {users.map((u) => (
                <option key={u.userId} value={u.userId}>
                  {u.email || u.username || u.userId.slice(0, 12)}
                </option>
              ))}
            </select>
            <input
              type="date"
              value={auditDate}
              onChange={(e) => {
                setAuditDate(e.target.value);
                refreshAudit(e.target.value, auditUserId);
              }}
            />
          </div>
        </div>

        {audit?.items?.length > 0 ? (
          <div className="audit-table">
            <div className="audit-row audit-header">
              <span>Time</span>
              <span>Event</span>
              <span>User</span>
              <span>Details</span>
            </div>
            {audit.items.map((item, i) => {
              const displayUser = item.email || item.username || item.userId?.slice(0, 8) || "—";
              return (
                <div key={i} className="audit-row">
                  <span className="audit-time">
                    {item.timestamp ? item.timestamp.slice(0, 19).replace("T", " ") : "—"}
                  </span>
                  <span className={`audit-event audit-event-${item.eventType?.toLowerCase()}`}>
                    {item.eventType}
                  </span>
                  <span className="audit-user" title={item.userId}>
                    {displayUser}
                  </span>
                  <span className="audit-details">
                    {formatDetails(item.details)}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="admin-note">
            No audit events{auditDate ? ` for ${auditDate}` : ""}{auditUserId ? " for selected user" : ""}.
          </p>
        )}
      </div>
    </div>
  );
}

function formatDetails(details) {
  if (!details || typeof details !== "object") return "";
  const parts = [];
  if (details.provider) parts.push(details.provider);
  if (details.query) parts.push(`"${String(details.query).slice(0, 50)}"`);
  if (details.entryId) parts.push(details.entryId.slice(0, 8));
  if (details.count != null) parts.push(`${details.count} entries`);
  if (details.embedded != null) parts.push(`${details.embedded}/${details.total} embedded`);
  if (details.deleted != null) parts.push(`${details.deleted} deleted`);
  return parts.join(" · ") || "—";
}
