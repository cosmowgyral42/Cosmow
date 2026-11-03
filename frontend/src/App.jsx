import { useEffect, useState } from "react";
import { checkBackendHealth } from "./lib/apiClient.js";
import { isSupabaseConfigured } from "./lib/supabase.js";

export default function App() {
  const [backend, setBackend] = useState("checking");
  const [error, setError] = useState("");

  async function verifyBackend() {
    setBackend("checking");
    setError("");

    try {
      await checkBackendHealth();
      setBackend("online");
    } catch (err) {
      setBackend("offline");
      setError(err.message || "Could not reach the backend.");
    }
  }

  useEffect(() => {
    verifyBackend();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="COSMOW home">
          <span className="brand-mark">C</span>
          <span>COSMOW</span>
        </a>
        <span className="version">EARLY ACCESS · 0.1.0</span>
      </header>

      <section className="hero">
        <p className="eyebrow">YOUR KNOWLEDGE WORKSPACE</p>
        <h1>Think clearly.<br /><span>Build intelligently.</span></h1>
        <p className="subtitle">
          Your personal AI workspace for understanding and exploring your
          documents.
        </p>

        <section className="status-panel" aria-live="polite">
          <div className="status-row">
            <span>Backend API</span>
            <span className={`status status-${backend}`}>
              <span className="status-dot" />
              {backend === "checking"
                ? "Checking"
                : backend === "online"
                  ? "Connected"
                  : "Unavailable"}
            </span>
          </div>

          <div className="status-row">
            <span>Supabase configuration</span>
            <span className={`status ${isSupabaseConfigured ? "status-online" : "status-offline"}`}>
              <span className="status-dot" />
              {isSupabaseConfigured ? "Configured" : "Setup required"}
            </span>
          </div>

          {error && <p className="error-message">{error}</p>}

          <button className="retry-button" onClick={verifyBackend}>
            Check backend again
          </button>
        </section>

        <p className="foundation-note">
          Frontend foundation initialized. Authentication and document
          workflows are the next implementation steps.
        </p>
      </section>
    </main>
  );
}
