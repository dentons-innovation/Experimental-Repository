/**
 * Application sidebar navigation.
 */

import { useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { gsap } from "gsap";
import { LayoutGrid, FolderOpen, LogOut, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { workspacesApi } from "@/api/fetchers";
import { useAuth } from "@/features/auth/AuthContext";
import { Avatar } from "@/components/ui";

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const sidebarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sidebarRef.current) {
      gsap.fromTo(
        sidebarRef.current,
        { x: -20, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.4, ease: "power2.out" },
      );
    }
  }, []);

  const { data: workspaces } = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => workspacesApi.list({ page: 1, page_size: 10 }),
    enabled: !!user,
  });

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  const handleLogout = () => {
    logout();
    navigate("/sign-in", { replace: true });
  };

  return (
    <aside className="sidebar" ref={sidebarRef}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">P</div>
        <span>ProjectFlow</span>
      </div>

      {/* Main navigation */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Navigation</div>
        <nav className="sidebar-nav">
          <Link
            to="/workspaces"
            className={`sidebar-nav-item ${isActive("/workspaces") ? "active" : ""}`}
          >
            <LayoutGrid size={16} />
            Workspaces
          </Link>
          <Link
            to="/connections"
            className={`sidebar-nav-item ${isActive("/connections") ? "active" : ""}`}
          >
            <Users size={16} />
            Connections
          </Link>
        </nav>
      </div>

      {/* Workspaces */}
      {workspaces && workspaces.items.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Your Workspaces</div>
          <nav className="sidebar-nav">
            {workspaces.items.map((ws) => (
              <Link
                key={ws.id}
                to={`/workspaces/${ws.id}`}
                className={`sidebar-nav-item ${
                  location.pathname.includes(ws.id) ? "active" : ""
                }`}
              >
                <FolderOpen size={16} />
                <span className="truncate">{ws.name}</span>
              </Link>
            ))}
          </nav>
        </div>
      )}

      {/* Footer / User Profile */}
      <div className="sidebar-section" style={{ marginTop: "auto" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 6px",
            background: "var(--color-surface-2)",
            borderRadius: 8,
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <Avatar user={user} size="sm" />
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div
              className="truncate"
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text)",
              }}
            >
              {user?.full_name || user?.username || "User"}
            </div>
            <div className="truncate text-secondary" style={{ fontSize: 11 }}>
              {user?.email}
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            title="Sign out"
            style={{
              background: "none",
              border: "none",
              padding: 6,
              color: "var(--color-text-secondary)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 6,
              transition: "color 0.15s ease, background 0.15s ease",
            }}
            onMouseOver={(e) => {
              (e.currentTarget as HTMLElement).style.color =
                "var(--color-danger)";
              (e.currentTarget as HTMLElement).style.background =
                "rgba(239, 68, 68, 0.1)";
            }}
            onMouseOut={(e) => {
              (e.currentTarget as HTMLElement).style.color =
                "var(--color-text-secondary)";
              (e.currentTarget as HTMLElement).style.background = "none";
            }}
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
