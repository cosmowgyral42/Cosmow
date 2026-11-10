import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import useDocuments from "../hooks/useDocuments.js";
import UploadZone from "../features/documents/UploadZone.jsx";
import DocumentList from "../features/documents/DocumentList.jsx";
import "../features/documents/documents.css";
import "../pages/dashboard.css";

export default function DocumentsPage() {
  const { logout } = useAuth();

  const {
    documents,
    loading,
    uploading,
    deletingId,
    error,
    loadError,
    refresh,
    setError,
    upload,
    embed,
    remove,
  } = useDocuments();

  async function handleUpload(file) {
    try {
      await upload(file);
    } catch {
      // The hook exposes the API error.
    }
  }

  async function handleEmbed(documentId) {
    try {
      await embed(documentId);
    } catch {
      // The hook exposes the API error.
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

  return (
    <main className="documents-page">
      <header className="documents-header">
        <div>
          <Link className="cos-back-link" to="/dashboard">
            ← Dashboard
          </Link>
          <h1>Your knowledge base</h1>
          <p>
            Upload a document and let Cosmow cook it. Then ask questions
            about its contents.
          </p>
        </div>

        <button
          className="cos-button cos-button-secondary"
          type="button"
          onClick={logout}
        >
          Sign out
        </button>
      </header>

      <div className="documents-content">
        <UploadZone onUpload={handleUpload} uploading={uploading} />

        {error && (
          <div className="cos-error" role="alert">
            {error}
            <button
              type="button"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        <h2 className="cos-section-heading">
          Your documents ({documents.length})
        </h2>

        {loading ? (
          <p role="status">Loading your documents...</p>
        ) : loadError ? (
          <div className="cos-error" role="alert">
            <p>{loadError}</p>
            <button
              className="cos-button cos-button-secondary"
              type="button"
              onClick={() => refresh().catch(() => {})}
            >
              Try again
            </button>
          </div>
        ) : (
          <DocumentList
            documents={documents}
            onEmbed={handleEmbed}
            onDelete={handleDelete}
            deletingId={deletingId}
          />
        )}
      </div>
    </main>
  );
}
