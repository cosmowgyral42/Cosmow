import { apiRequest } from "../../lib/apiClient.js";

export async function listDocuments() {
  return apiRequest("documents/");
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest("documents/upload", {
    method: "POST",
    body: formData,
  });
}

export async function embedDocument(documentId) {
  return apiRequest(`documents/${documentId}/embed`, {
    method: "POST",
  });
}

export async function deleteDocument(documentId) {
  return apiRequest(`documents/${documentId}`, {
    method: "DELETE",
  });
}

