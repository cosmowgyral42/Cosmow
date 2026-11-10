import DocumentCard from "./DocumentCard.jsx";

export default function DocumentList({
  documents,
  onEmbed,
  onDelete,
  deletingId,
}) {
  if (!documents.length) {
    return (
      <div className="cos-empty-state">
        <h3>No documents uploaded yet</h3>
        <p>Your uploaded documents will appear here.</p>
      </div>
    );
  }

  return (
    <div className="cos-document-list">
      {documents.map((document) => (
        <DocumentCard
          key={document.id}
          document={document}
          onEmbed={onEmbed}
          onDelete={onDelete}
          deleting={deletingId === document.id}
        />
      ))}
    </div>
  );
}
