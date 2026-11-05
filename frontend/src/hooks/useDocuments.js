import { useCallback, useState } from "react";
import {
  uploadDocument as uploadDocumentRequest,
  embedDocument as embedDocumentRequest,
} from "../features/documents/documentService.js";

const MAX_FILE_SIZE = 1024 * 1024;
const ALLOWED_EXTENSIONS = [".txt", ".md"];

export default function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const upload = useCallback(async (file) => {
    setError("");

    if (!file) return;

    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf("."));

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setError("Only .txt and .md files are supported.");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError("File size must not exceed 1 MB.");
      return;
    }

    setUploading(true);

    try {
      const result = await uploadDocumentRequest(file);

      setDocuments((current) => [
        {
          ...result,
          indexing: false,
          indexed: false,
          chunksEmbedded: 0,
        },
        ...current,
      ]);

      return result;
    } catch (err) {
      setError(err.message || "Document upload failed.");
      throw err;
    } finally {
      setUploading(false);
    }
  }, []);

  const embed = useCallback(async (documentId) => {
    setError("");

    setDocuments((current) =>
      current.map((doc) =>
        doc.id === documentId ? { ...doc, indexing: true } : doc
      )
    );

    try {
      const result = await embedDocumentRequest(documentId);

      setDocuments((current) =>
        current.map((doc) =>
          doc.id === documentId
            ? {
                ...doc,
                indexing: false,
                indexed: true,
                chunksEmbedded: result.chunks_embedded ?? 0,
                status: result.status ?? doc.status,
              }
            : doc
        )
      );

      return result;
    } catch (err) {
      setDocuments((current) =>
        current.map((doc) =>
          doc.id === documentId ? { ...doc, indexing: false } : doc
        )
      );

      setError(err.message || "Document indexing failed.");
      throw err;
    }
  }, []);

  return { documents, uploading, error, setError, upload, embed };
}
