export default function ProfileCard({ me, onLogout }) {
  return (
    <div className="panel">
      <div className="row between">
        <h2>Profile</h2>
        <button className="secondary" onClick={onLogout}>Logout</button>
      </div>
      <p><strong>User ID:</strong> {me?.userId || "-"}</p>
    </div>
  );
}
