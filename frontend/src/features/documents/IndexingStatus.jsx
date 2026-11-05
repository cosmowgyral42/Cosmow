export default function IndexingStatus({ document }) {
  if (document.indexing) {
    return <span className="cos-status pending">Indexing...</span>;
  }

  if (document.indexed) {
    return (
      <span className="cos-status success">
        Indexed · {document.chunksEmbedded} chunks
      </span>
    );
  }

  return <span className="cos-status">Uploaded · Awaiting indexing</span>;
}
