export default function ProfileCard({ me, authUser, onLogout }) {
  return (
    <div className="panel">
      <div className="row between">
        <h2>Profile</h2>
        <button className="secondary" onClick={onLogout}>Logout</button>
      </div>
      <p><strong>User ID:</strong> {me?.userId || authUser?.uid || "-"}</p>
      <p><strong>Email:</strong> {me?.email || authUser?.email || "-"}</p>
    </div>
  );
}
