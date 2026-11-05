import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import useDocuments from "../hooks/useDocuments.js";
import UploadZone from "../features/documents/UploadZone.jsx";
import DocumentList from "../features/documents/DocumentList.jsx";
import "../features/documents/documents.css";

export default function DocumentsPage() {
  const { logout } = useAuth();
  const {
    documents,
    uploading,
    error,
    setError,
    upload,
    embed,
  } = useDocuments();

  async function handleUpload(file) {
    try {
      await upload(file);
    } catch {
      // The hook exposes the API error to the page.
    }
  }

  async function handleEmbed(documentId) {
    try {
      await embed(documentId);
    } catch {
      // The hook exposes the API error to the page.
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
          <p>Upload documents and prepare them for AI-powered search.</p>
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
              style={{
                float: "right",
                border: 0,
                background: "transparent",
                cursor: "pointer",
              }}
            >
              ×
            </button>
          </div>
        )}

        <h2 className="cos-section-heading">
          Your documents ({documents.length})
        </h2>

        <DocumentList documents={documents} onEmbed={handleEmbed} />
      </div>
    </main>
  );
}


