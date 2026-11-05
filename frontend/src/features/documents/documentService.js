import { apiRequest } from "../../lib/apiClient.js";

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
