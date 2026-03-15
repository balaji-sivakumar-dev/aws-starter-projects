import { useEffect, useState } from "react";
import { getMetrics, getAuditLogs, listUsers, adminRagStatus } from "../api/admin";

export default function AdminPanel() {
  const [metrics, setMetrics] = useState(null);
  const [users, setUsers] = useState(null);
  const [audit, setAudit] = useState(null);
  const [ragInfo, setRagInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [auditDate, setAuditDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [metricsDays, setMetricsDays] = useState(7);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [m, u, a, r] = await Promise.all([
        getMetrics(metricsDays).catch(() => null),
        listUsers().catch(() => null),
        getAuditLogs(auditDate).catch(() => null),
        adminRagStatus().catch(() => null),
      ]);
      setMetrics(m);
      setUsers(u);
      setAudit(a);
      setRagInfo(r);
    } catch (err) {
      setError(err.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }

  async function refreshMetrics() {
    try {
      const m = await getMetrics(metricsDays);
      setMetrics(m);
    } catch {}
  }

  async function refreshAudit() {
    try {
      const a = await getAuditLogs(auditDate);
      setAudit(a);
    } catch {}
  }

  if (loading) {
    return (
      <div className="admin-container">
        <h2>Admin Dashboard</h2>
        <p className="admin-loading">Loading admin data...</p>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <h2>Admin Dashboard</h2>
      {error && <p className="admin-error">{error}</p>}

      {/* Metrics cards */}
      <div className="admin-section">
        <div className="admin-section-header">
          <h3>Usage Metrics</h3>
          <div className="admin-section-controls">
            <select
              value={metricsDays}
              onChange={(e) => {
                setMetricsDays(Number(e.target.value));
                setTimeout(refreshMetrics, 0);
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
            <div className="metric-card">
              <div className="metric-value">
                ${(metrics.estimatedCost || 0).toFixed(4)}
              </div>
              <div className="metric-label">Est. AI Cost</div>
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
        <h3>Users ({users?.totalUsers || 0})</h3>
        {users?.users?.length > 0 && (
          <div className="admin-user-list">
            {users.users.map((uid) => (
              <div key={uid} className="admin-user-item">
                <span className="admin-user-id">{uid}</span>
              </div>
            ))}
          </div>
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
          <p className="admin-note">RAG not configured (VECTOR_STORE not set)</p>
        )}
      </div>

      {/* Audit Logs */}
      <div className="admin-section">
        <div className="admin-section-header">
          <h3>Audit Log</h3>
          <div className="admin-section-controls">
            <input
              type="date"
              value={auditDate}
              onChange={(e) => {
                setAuditDate(e.target.value);
                setTimeout(refreshAudit, 0);
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
            {audit.items.map((item, i) => (
              <div key={i} className="audit-row">
                <span className="audit-time">
                  {item.timestamp?.slice(11, 19) || "—"}
                </span>
                <span className={`audit-event audit-event-${item.eventType}`}>
                  {item.eventType}
                </span>
                <span className="audit-user">
                  {item.userId?.slice(0, 8) || "—"}
                </span>
                <span className="audit-details">
                  {formatDetails(item.details)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="admin-note">No audit events for {auditDate}</p>
        )}
      </div>
    </div>
  );
}

function formatDetails(details) {
  if (!details || typeof details !== "object") return "";
  const parts = [];
  if (details.action) parts.push(details.action);
  if (details.provider) parts.push(details.provider);
  if (details.model) parts.push(details.model);
  if (details.taskType) parts.push(details.taskType);
  if (details.query) parts.push(`"${details.query.slice(0, 40)}..."`);
  if (details.resourceId) parts.push(details.resourceId.slice(0, 12));
  if (details.inputTokens) parts.push(`${details.inputTokens}→${details.outputTokens} tokens`);
  if (details.latencyMs) parts.push(`${details.latencyMs}ms`);
  return parts.join(" | ");
}
