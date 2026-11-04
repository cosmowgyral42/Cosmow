import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";

export default function ProtectedRoute() {
  const { loading, isAuthenticated, authError, logout } = useAuth();

  if (loading) {
    return <main className="auth-shell"><p>Restoring your session...</p></main>;
  }

  if (!isAuthenticated) {
    if (authError) {
      return (
        <main className="auth-shell">
          <section className="auth-card">
            <h1>Account verification failed</h1>
            <p className="form-error">{authError}</p>
            <button className="primary-button" onClick={() => logout()}>
              Sign out
            </button>
          </section>
        </main>
      );
    }
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}