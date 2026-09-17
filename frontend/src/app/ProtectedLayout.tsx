/**
 * Protected layout — requires authenticated session.
 *
 * - Redirects to /sign-in if not authenticated.
 * - Renders the sidebar + main content layout when authenticated.
 */

import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { Sidebar } from "@/components/Sidebar";
import { useRealtimeInvalidation } from "@/hooks/useRealtimeInvalidation";

export function ProtectedLayout() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Attach realtime cache invalidations
  useRealtimeInvalidation();

  if (isLoading) {
    return (
      <div className="loading-center" style={{ minHeight: "100vh" }}>
        <div className="spinner" style={{ width: 36, height: 36 }} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/sign-in" state={{ from: location }} replace />;
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
