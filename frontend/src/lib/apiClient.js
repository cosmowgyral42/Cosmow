import { supabase } from "./supabase.js";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

const BACKEND_ORIGIN = (
  import.meta.env.VITE_BACKEND_ORIGIN || "http://localhost:8000"
).replace(/\/+$/, "");

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  let accessToken = null;

  if (supabase) {
    const { data, error } = await supabase.auth.getSession();

    if (error) {
      throw new Error("Unable to read the current authentication session.");
    }

    accessToken = data.session?.access_token ?? null;
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(
    `${API_BASE_URL}/${path.replace(/^\/+/, "")}`,
    { ...options, headers }
  );

  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null
        ? payload.detail || "API request failed."
        : payload || "API request failed.";

    throw new Error(message);
  }

  return payload;
}

export async function checkBackendHealth() {
  const response = await fetch(`${BACKEND_ORIGIN}/health/live`);

  if (!response.ok) {
    throw new Error(`Backend health check failed (${response.status}).`);
  }

  return response.json();
}
