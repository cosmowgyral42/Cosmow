import { supabase } from "./supabase.js";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

const BACKEND_ORIGIN = (
  import.meta.env.VITE_BACKEND_ORIGIN || "http://localhost:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, { status, requestId, retryAfter, detail } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
    this.retryAfter = retryAfter;
    this.detail = detail;
  }
}

async function readResponseBody(response) {
  const text = await response.text();

  if (!text) return null;

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }

  return text;
}

function getErrorMessage(payload) {
  if (typeof payload === "string") {
    return payload || "API request failed.";
  }

  if (payload && typeof payload === "object") {
    const detail = payload.detail ?? payload.message;

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
      return detail
        .map((item) => item.msg || item.message || "Invalid request.")
        .join("; ");
    }
  }

  return "API request failed.";
}

async function request(url, options = {}) {
  const headers = new Headers(options.headers || {});

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (options.body) {
    const isFormData =
      typeof FormData !== "undefined" &&
      options.body instanceof FormData;

    if (!isFormData && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const payload = response.status === 204
    ? null
    : await readResponseBody(response);

  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload), {
      status: response.status,
      requestId: response.headers.get("x-request-id"),
      retryAfter: response.headers.get("retry-after"),
      detail: payload,
    });
  }

  return payload;
}

const inFlightGetRequests = new Map();

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});

  if (supabase) {
    const { data, error } = await supabase.auth.getSession();

    if (error) {
      throw new Error("Unable to read the current authentication session.");
    }

    const accessToken = data.session?.access_token;

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  const url = `${API_BASE_URL}/${path.replace(/^\/+/, "")}`;
  const method = (options.method || "GET").toUpperCase();

  if (method !== "GET") {
    return request(url, { ...options, headers });
  }

  const requestKey = `${url}::${headers.get("Authorization") || ""}`;
  const existingRequest = inFlightGetRequests.get(requestKey);

  if (existingRequest) {
    return existingRequest;
  }

  const pendingRequest = request(url, { ...options, headers })
    .finally(() => {
      inFlightGetRequests.delete(requestKey);
    });

  inFlightGetRequests.set(requestKey, pendingRequest);
  return pendingRequest;
}
export async function checkBackendHealth() {
  return request(`${BACKEND_ORIGIN}/health/live`);
}
