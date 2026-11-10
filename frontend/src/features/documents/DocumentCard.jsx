import IndexingStatus from "./IndexingStatus.jsx";

export default function DocumentCard({
  document,
  onEmbed,
  onDelete,
  deleting,
}) {
  return (
    <article className="cos-document-card">
      <div className="cos-document-icon">▤</div>

      <div className="cos-document-info">
        <h3>{document.title || document.original_filename}</h3>
        <p>
          {document.original_filename}
          {document.file_size_bytes != null
            ? ` · ${(document.file_size_bytes / 1024).toFixed(1)} KB`
            : ""}
        </p>
        <IndexingStatus document={document} />
      </div>

      <div className="cos-document-actions">
        <button
          className="cos-button cos-button-secondary"
          type="button"
          disabled={document.indexing || document.status === "indexed"}
          onClick={() => onEmbed(document.id)}
        >
          {document.indexing
            ? "Cooking..."
            : document.status === "indexed"
              ? "Cooked"
              : "Start Cooking"}
        </button>

        <button
          className="cos-delete-button"
          type="button"
          disabled={deleting}
          onClick={() => onDelete(document.id)}
          aria-label={`Delete ${document.original_filename}`}
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </article>
  );
}
