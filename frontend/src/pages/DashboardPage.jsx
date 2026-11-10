import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import useDocuments from "../hooks/useDocuments.js";
import "./dashboard.css";

function formatDate(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleDateString();
}

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const {
    documents,
    loading,
    deletingId,
    loadError,
    refresh,
    remove,
  } = useDocuments();

  const navigate = useNavigate();
  const [logoutError, setLogoutError] = useState("");
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    setBusy(true);
    setLogoutError("");

    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setLogoutError(err.message || "Unable to sign out.");
      setBusy(false);
    }
  }

  async function handleDelete(documentId) {
    const confirmed = window.confirm(
      "Permanently delete this document and its cooked content?"
    );

    if (!confirmed) return;

    try {
      await remove(documentId);
    } catch {
      // The hook exposes the API error.
    }
  }

  const indexedCount = documents.filter(
    (doc) => doc.status === "indexed"
  ).length;

  const waitingCount = documents.filter(
    (doc) => doc.status === "uploaded"
  ).length;

  const recentDocuments = documents.slice(0, 5);

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <span className="auth-brand">COSMOW</span>

        <div className="dashboard-account">
          <span>{user?.email}</span>
          <div className="dashboard-profile-menu">
            <button
              className="secondary-button"
              type="button"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              My account ?
            </button>

            {menuOpen && (
              <div className="dashboard-dropdown">
                <span>{user?.email}</span>
                <button type="button" onClick={() => navigate("/documents")}>
                  My documents
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={handleLogout}
                >
                  {busy ? "Signing out..." : "Sign out"}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <section className="dashboard-content">
        <p className="auth-eyebrow">YOUR WORKSPACE</p>
        <h1>Welcome back, {user?.email?.split("@")[0] || "Explorer"}.</h1>
        <p>Your knowledge garden, ready to grow. ??</p>

        <section className="dashboard-stats" aria-label="Document statistics">
          <article className="dashboard-stat-card">
            <span>Total documents</span>
            <strong>{loading ? "—" : documents.length}</strong>
          </article>
          <article className="dashboard-stat-card">
            <span>Cooked</span>
            <strong>{loading ? "—" : indexedCount}</strong>
          </article>
          <article className="dashboard-stat-card">
            <span>Waiting to cook</span>
            <strong>{loading ? "—" : waitingCount}</strong>
          </article>
        </section>

        <section className="dashboard-main-card">
          <div className="dashboard-section-heading">
            <div>
              <h2>Recent documents</h2>
              <p>Your latest additions to Cosmow.</p>
            </div>
            <button
              className="secondary-button"
              onClick={() => navigate("/documents")}
            >
              View all
            </button>
          </div>

          {loading && (
            <p className="dashboard-message" role="status">
              Loading your knowledge garden...
            </p>
          )}

          {!loading && loadError && (
            <div className="dashboard-message" role="alert">
              <p>{loadError}</p>
              <button className="secondary-button" onClick={refresh}>
                Try again
              </button>
            </div>
          )}

          {!loading && !loadError && documents.length === 0 && (
            <div className="dashboard-empty">
              <span className="dashboard-empty-icon">??</span>
              <h3>Your garden is waiting.</h3>
              <p>Upload your first document to start building your knowledge base.</p>
              <button
                className="primary-button"
                onClick={() => navigate("/documents")}
              >
                Upload a document
              </button>
            </div>
          )}

          {!loading && !loadError && recentDocuments.length > 0 && (
            <div className="dashboard-document-list">
              {recentDocuments.map((doc) => (
                <article className="dashboard-document-row" key={doc.id}>
                  <div className="dashboard-document-info">
                    <strong>{doc.original_filename || doc.title}</strong>
                    <span>{formatDate(doc.created_at)}</span>
                  </div>

                  <div className="dashboard-row-actions">
                    <span className={`dashboard-status ${doc.status}`}>
                      {doc.status === "indexed"
                        ? "Cooked"
                        : "Waiting to cook"}
                    </span>

                    <button
                      className="cos-delete-button"
                      type="button"
                      disabled={deletingId === doc.id}
                      onClick={() => handleDelete(doc.id)}
                    >
                      {deletingId === doc.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="dashboard-profile-card">
          <div>
            <h2>Your account</h2>
            <p>{user?.email}</p>
          </div>
          <span className={user?.is_active ? "account-active" : "account-inactive"}>
            {user?.is_active ? "Active account" : "Inactive account"}
          </span>
        </section>

        <section className="dashboard-quick-action">
          <div>
            <h2>Ready to add more knowledge?</h2>
            <p>Keep your ideas, notes and documents together.</p>
          </div>
          <button
            className="primary-button"
            onClick={() => navigate("/documents")}
          >
            Open documents
          </button>
        </section>

        {logoutError && (
          <p className="form-error" role="alert">{logoutError}</p>
        )}
      </section>
    </main>
  );
}

