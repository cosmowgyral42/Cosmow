import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";

export default function SignupPage() {
  const { register, loading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!loading && isAuthenticated) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setConfirmation("");

    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    setSubmitting(true);
    try {
      const data = await register(email, password);

      if (data.session) {
        navigate("/dashboard", { replace: true });
      } else {
        setConfirmation(
          "Account created. Check your email for the confirmation link, then sign in."
        );
      }
    } catch (err) {
      setError(err.message || "Unable to create your account.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <Link className="auth-brand" to="/">COSMOW</Link>
        <p className="auth-eyebrow">GET STARTED</p>
        <h1>Create your account</h1>
        <p className="auth-description">Build your personal AI knowledge workspace.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="signup-email">Email</label>
          <input id="signup-email" type="email" autoComplete="email"
            value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com" required />

          <label htmlFor="signup-password">Password</label>
          <input id="signup-password" type="password"
            autoComplete="new-password" minLength={8} value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters" required />

          {error && <p className="form-error" role="alert">{error}</p>}
          {confirmation && <p className="form-success" role="status">{confirmation}</p>}

          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="auth-switch">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}