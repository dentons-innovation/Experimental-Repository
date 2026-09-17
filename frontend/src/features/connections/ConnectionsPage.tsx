import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UserPlus,
  Check,
  X,
  Trash2,
  Search,
  User as UserIcon,
} from "lucide-react";
import { queryKeys } from "@/api/queryKeys";
import { connectionsApi } from "@/api/fetchers";
import { getApiErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import {
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Input,
} from "@/components/ui";
import type { User } from "@/types";

export function ConnectionsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<
    "connections" | "requests" | "find"
  >("connections");
  const [searchQuery, setSearchQuery] = useState("");

  const {
    data: connectionsData,
    isLoading: isConnLoading,
    error: connError,
  } = useQuery({
    queryKey: queryKeys.connections.list(),
    queryFn: () => connectionsApi.list(),
  });

  const { data: incomingData, isLoading: isIncomingLoading } = useQuery({
    queryKey: queryKeys.connections.pendingIncoming(),
    queryFn: () => connectionsApi.listPendingIncoming(),
  });

  const { data: outgoingData, isLoading: isOutgoingLoading } = useQuery({
    queryKey: queryKeys.connections.pendingOutgoing(),
    queryFn: () => connectionsApi.listPendingOutgoing(),
  });

  const { data: searchResults, isLoading: isSearchLoading } = useQuery({
    queryKey: queryKeys.connections.search(searchQuery),
    queryFn: () => connectionsApi.searchUsers(searchQuery),
    enabled: searchQuery.length > 1 && activeTab === "find",
  });

  const acceptMutation = useMutation({
    mutationFn: connectionsApi.accept,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.connections.all() }),
  });

  const rejectMutation = useMutation({
    mutationFn: connectionsApi.reject,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.connections.all() }),
  });

  const removeMutation = useMutation({
    mutationFn: connectionsApi.remove,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.connections.all() }),
  });

  const sendRequestMutation = useMutation({
    mutationFn: connectionsApi.sendRequest,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.connections.all() }),
  });

  const isLoading = isConnLoading || isIncomingLoading || isOutgoingLoading;
  const error = connError;

  if (isLoading) return <LoadingSpinner fullPage />;
  if (error) return <ErrorMessage message={getApiErrorMessage(error)} />;

  const activeConnections = connectionsData?.items || [];
  const pendingIncoming = incomingData?.items || [];
  const pendingOutgoing = outgoingData?.items || [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Connections</h1>
          <p className="page-subtitle">
            Manage your network and connect with colleagues.
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <button
            className={`btn ${activeTab === "connections" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("connections")}
          >
            My Connections ({activeConnections.length})
          </button>
          <button
            className={`btn ${activeTab === "requests" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("requests")}
          >
            Requests (
            {pendingIncoming.length > 0 ? (
              <span style={{ color: "var(--color-warning)" }}>
                {pendingIncoming.length}
              </span>
            ) : (
              0
            )}
            )
          </button>
          <button
            className={`btn ${activeTab === "find" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setActiveTab("find")}
          >
            Find Users
          </button>
        </div>
      </div>

      <div className="page-content">
        {activeTab === "connections" && (
          <div className="card">
            <h2
              style={{
                fontSize: 18,
                fontWeight: 600,
                marginBottom: "var(--space-4)",
              }}
            >
              Active Connections
            </h2>
            {activeConnections.length === 0 ? (
              <EmptyState
                title="No active connections"
                description="Find users to start building your network."
                action={
                  <button
                    className="btn btn-primary"
                    onClick={() => setActiveTab("find")}
                  >
                    Find Users
                  </button>
                }
              />
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-3)",
                }}
              >
                {activeConnections.map((conn) => {
                  const otherUser =
                    conn.user_lo_rel.id === user?.id
                      ? conn.user_hi_rel
                      : conn.user_lo_rel;
                  return (
                    <div
                      key={conn.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "var(--space-3)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                      }}
                    >
                      <UserInfo user={otherUser} />
                      <button
                        className="btn btn-ghost"
                        style={{ color: "var(--color-danger)" }}
                        onClick={() => removeMutation.mutate(conn.id)}
                        disabled={removeMutation.isPending}
                      >
                        <Trash2 size={16} style={{ marginRight: 4 }} /> Remove
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === "requests" && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-6)",
            }}
          >
            <div className="card">
              <h2
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  marginBottom: "var(--space-4)",
                }}
              >
                Incoming Requests
              </h2>
              {pendingIncoming.length === 0 ? (
                <p style={{ color: "var(--color-text-secondary)" }}>
                  No pending incoming requests.
                </p>
              ) : (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--space-3)",
                  }}
                >
                  {pendingIncoming.map((conn) => {
                    const otherUser =
                      conn.user_lo_rel.id === user?.id
                        ? conn.user_hi_rel
                        : conn.user_lo_rel;
                    return (
                      <div
                        key={conn.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "var(--space-3)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-md)",
                        }}
                      >
                        <UserInfo user={otherUser} />
                        <div style={{ display: "flex", gap: "var(--space-2)" }}>
                          <button
                            className="btn btn-primary"
                            onClick={() => acceptMutation.mutate(conn.id)}
                            disabled={acceptMutation.isPending}
                          >
                            <Check size={16} style={{ marginRight: 4 }} />{" "}
                            Accept
                          </button>
                          <button
                            className="btn btn-secondary"
                            onClick={() => rejectMutation.mutate(conn.id)}
                            disabled={rejectMutation.isPending}
                          >
                            <X size={16} style={{ marginRight: 4 }} /> Reject
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="card">
              <h2
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  marginBottom: "var(--space-4)",
                }}
              >
                Outgoing Requests
              </h2>
              {pendingOutgoing.length === 0 ? (
                <p style={{ color: "var(--color-text-secondary)" }}>
                  No pending outgoing requests.
                </p>
              ) : (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--space-3)",
                  }}
                >
                  {pendingOutgoing.map((conn) => {
                    const otherUser =
                      conn.user_lo_rel.id === user?.id
                        ? conn.user_hi_rel
                        : conn.user_lo_rel;
                    return (
                      <div
                        key={conn.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "var(--space-3)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-md)",
                        }}
                      >
                        <UserInfo user={otherUser} />
                        <button
                          className="btn btn-ghost"
                          style={{ color: "var(--color-danger)" }}
                          onClick={() => removeMutation.mutate(conn.id)}
                          disabled={removeMutation.isPending}
                        >
                          <X size={16} style={{ marginRight: 4 }} /> Cancel
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "find" && (
          <div className="card">
            <h2
              style={{
                fontSize: 18,
                fontWeight: 600,
                marginBottom: "var(--space-4)",
              }}
            >
              Find Users
            </h2>
            <div
              style={{
                display: "flex",
                gap: "var(--space-2)",
                marginBottom: "var(--space-6)",
              }}
            >
              <Input
                placeholder="Search by name, email, or username..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
              <button className="btn btn-secondary" disabled>
                <Search size={16} />
              </button>
            </div>

            {isSearchLoading ? (
              <LoadingSpinner />
            ) : searchResults?.items && searchResults.items.length > 0 ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-3)",
                }}
              >
                {searchResults.items
                  .filter((u) => u.id !== user?.id)
                  .map((foundUser) => {
                    const isConnected = activeConnections.some(
                      (c) =>
                        c.user_lo_rel.id === foundUser.id ||
                        c.user_hi_rel.id === foundUser.id,
                    );
                    const isPendingIncoming = pendingIncoming.some(
                      (c) =>
                        c.user_lo_rel.id === foundUser.id ||
                        c.user_hi_rel.id === foundUser.id,
                    );
                    const isPendingOutgoing = pendingOutgoing.some(
                      (c) =>
                        c.user_lo_rel.id === foundUser.id ||
                        c.user_hi_rel.id === foundUser.id,
                    );

                    return (
                      <div
                        key={foundUser.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "var(--space-3)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-md)",
                        }}
                      >
                        <UserInfo user={foundUser} />
                        <div>
                          {isConnected ? (
                            <span
                              style={{
                                color: "var(--color-text-secondary)",
                                fontSize: 13,
                                fontWeight: 500,
                              }}
                            >
                              Connected
                            </span>
                          ) : isPendingOutgoing ? (
                            <span
                              style={{
                                color: "var(--color-text-secondary)",
                                fontSize: 13,
                                fontWeight: 500,
                              }}
                            >
                              Request Sent
                            </span>
                          ) : isPendingIncoming ? (
                            <span
                              style={{
                                color: "var(--color-warning)",
                                fontSize: 13,
                                fontWeight: 500,
                              }}
                            >
                              Action Required
                            </span>
                          ) : (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() =>
                                sendRequestMutation.mutate(foundUser.id)
                              }
                              disabled={sendRequestMutation.isPending}
                            >
                              <UserPlus size={14} style={{ marginRight: 4 }} />{" "}
                              Connect
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : searchQuery.length > 1 ? (
              <EmptyState
                title="No users found"
                description={`Could not find any users matching "${searchQuery}"`}
              />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

function UserInfo({ user }: { user: User }) {
  return (
    <div
      style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: "var(--color-brand-muted)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--color-brand)",
          fontWeight: 600,
        }}
      >
        {user.full_name[0]?.toUpperCase() || <UserIcon size={20} />}
      </div>
      <div>
        <div style={{ fontWeight: 600, fontSize: 15 }}>{user.full_name}</div>
        <div style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
          @{user.username}
        </div>
      </div>
    </div>
  );
}
