export default function IndexingStatus({ document }) {
  if (document.indexing) {
    return <span className="cos-status pending">Cooking your document...</span>;
  }

  if (document.indexed) {
    return <span className="cos-status success">Meal created</span>;
  }

  return <span className="cos-status">Uploaded · Ready to cook</span>;
}
