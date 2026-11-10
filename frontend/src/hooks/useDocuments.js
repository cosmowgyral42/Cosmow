import { useCallback, useEffect, useRef, useState } from "react";
import {
  listDocuments,
  uploadDocument as uploadDocumentRequest,
  embedDocument as embedDocumentRequest,
  deleteDocument as deleteDocumentRequest,
} from "../features/documents/documentService.js";

const MAX_FILE_SIZE = 1024 * 1024;
const ALLOWED_EXTENSIONS = [".txt", ".md"];

export default function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");

  const initialLoadStarted = useRef(false);
  const refreshInFlight = useRef(null);

  const refresh = useCallback(() => {
    // Reuse an in-flight list request instead of sending duplicates.
    if (refreshInFlight.current) {
      return refreshInFlight.current;
    }

    setLoading(true);
    setLoadError("");

    const request = listDocuments()
      .then((result) => {
        if (!Array.isArray(result)) {
          throw new Error("The server returned an unexpected document list.");
        }
        setDocuments(result);
        return result;
      })
      .catch((err) => {
        // Preserve the last successfully loaded documents on failure.
        setLoadError(err.message || "Unable to load your documents.");
        throw err;
      })
      .finally(() => {
        setLoading(false);
        refreshInFlight.current = null;
      });

    refreshInFlight.current = request;
    return request;
  }, []);

  useEffect(() => {
    // React Strict Mode replays effects in development. This ref prevents
    // the replay from starting a second initial fetch for this hook instance.
    if (initialLoadStarted.current) return;
    initialLoadStarted.current = true;

    refresh().catch(() => {
      // The hook exposes loadError to the page.
    });
  }, [refresh]);

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
        result,
        ...current.filter((doc) => doc.id !== result.id),
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

    try {
      const result = await embedDocumentRequest(documentId);
      setDocuments((current) =>
        current.map((doc) =>
          doc.id === documentId
            ? { ...doc, status: result.status ?? "indexed" }
            : doc
        )
      );
      return result;
    } catch (err) {
      setError(err.message || "Cooking failed. Please try again.");
      throw err;
    }
  }, []);

  const remove = useCallback(async (documentId) => {
    if (deletingId !== null) return;

    setError("");
    setDeletingId(documentId);

    try {
      await deleteDocumentRequest(documentId);
      setDocuments((current) =>
        current.filter((doc) => doc.id !== documentId)
      );
    } catch (err) {
      setError(err.message || "Unable to delete this document.");
      throw err;
    } finally {
      setDeletingId(null);
    }
  }, [deletingId]);

  return {
    documents,
    loading,
    uploading,
    deletingId,
    error,
    loadError,
    setError,
    upload,
    embed,
    remove,
    refresh,
  };
}
