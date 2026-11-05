import IndexingStatus from "./IndexingStatus.jsx";

export default function DocumentCard({ document, onEmbed }) {
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

      <button
        className="cos-button cos-button-secondary"
        type="button"
        disabled={document.indexing || document.indexed}
        onClick={() => onEmbed(document.id)}
      >
        {document.indexing
          ? "Indexing..."
          : document.indexed
            ? "Indexed"
            : "Index document"}
      </button>
    </article>
  );
}
