import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import LoginPage from "../pages/LoginPage.jsx";
import SignupPage from "../pages/SignupPage.jsx";
import DashboardPage from "../pages/DashboardPage.jsx";
import ProtectedRoute from "./ProtectedRoute.jsx";

function HomeRedirect() {
  const { loading, isAuthenticated } = useAuth();
  if (loading) return <main className="auth-shell"><p>Loading Cosmow...</p></main>;
  return <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />;
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}