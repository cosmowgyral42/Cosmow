import { useRef } from "react";

export default function UploadZone({ onUpload, uploading }) {
  const inputRef = useRef(null);

  function handleFiles(files) {
    const file = files?.[0];
    if (file) onUpload(file);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section
      className="cos-upload-zone"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        handleFiles(event.dataTransfer.files);
      }}
    >
      <div className="cos-upload-icon">↑</div>
      <h2>Upload your knowledge</h2>
      <p>Drop a document here or choose a file from your device.</p>
      <p className="cos-muted">TXT or Markdown · Maximum 1 MB</p>

      <input
        ref={inputRef}
        type="file"
        accept=".txt,.md,text/plain,text/markdown"
        hidden
        onChange={(event) => handleFiles(event.target.files)}
      />

      <button
        className="cos-button"
        type="button"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? "Uploading..." : "Choose a file"}
      </button>
    </section>
  );
}
