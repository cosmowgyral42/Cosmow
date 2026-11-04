import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleLogout() {
    setBusy(true);
    setError("");
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err.message || "Unable to sign out.");
      setBusy(false);
    }
  }

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <span className="auth-brand">COSMOW</span>
        <button className="secondary-button" onClick={handleLogout} disabled={busy}>
          {busy ? "Signing out..." : "Sign out"}
        </button>
      </header>
      <section className="dashboard-content">
        <p className="auth-eyebrow">YOUR WORKSPACE</p>
        <h1>Welcome to Cosmow.</h1>
        <p>You are authenticated and your backend identity has been verified.</p>
        <div className="profile-panel">
          <span>Account email</span>
          <strong>{user.email}</strong>
          <span>Application user ID</span>
          <strong>{user.id}</strong>
          <span>Timezone</span>
          <strong>{user.timezone}</strong>
          <span>Account status</span>
          <strong>{user.is_active ? "Active" : "Inactive"}</strong>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <p className="dashboard-note">
          Authentication is connected. Document and RAG workflows are separate implementation steps.
        </p>
      </section>
    </main>
  );
}