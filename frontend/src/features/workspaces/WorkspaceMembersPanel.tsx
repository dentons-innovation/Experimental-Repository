import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus, UserMinus, Shield, User as UserIcon } from "lucide-react";
import { queryKeys } from "@/api/queryKeys";
import { workspacesApi, connectionsApi } from "@/api/fetchers";
import { getApiErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { LoadingSpinner, ErrorMessage, Modal, Select } from "@/components/ui";
import type { Workspace } from "@/types";

export function WorkspaceMembersPanel({ workspace }: { workspace: Workspace }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showAddMember, setShowAddMember] = useState(false);

  const {
    data: members,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKeys.workspaces.members(workspace.id),
    queryFn: () => workspacesApi.listMembers(workspace.id),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) =>
      workspacesApi.removeMember(workspace.id, userId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaces.members(workspace.id),
      }),
  });

  const changeRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      workspacesApi.updateMemberRole(workspace.id, userId, { role }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaces.members(workspace.id),
      }),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={getApiErrorMessage(error)} />;

  const currentUserMember = members?.find((m) => m.user.id === user?.id);
  const isOwner = currentUserMember?.role === "owner";

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "var(--space-4)",
        }}
      >
        <h2 style={{ fontSize: 18, fontWeight: 600 }}>
          Workspace Members ({members?.length || 0})
        </h2>
        {isOwner && (
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowAddMember(true)}
          >
            <UserPlus size={14} style={{ marginRight: 4 }} /> Add Member
          </button>
        )}
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-3)",
        }}
      >
        {members?.map((member) => (
          <div
            key={member.user.id}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "var(--space-3)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: "var(--color-brand-muted)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--color-brand)",
                  fontWeight: 600,
                }}
              >
                {member.user.full_name[0]?.toUpperCase() || (
                  <UserIcon size={16} />
                )}
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>
                  {member.user.full_name}{" "}
                  {member.user.id === user?.id && "(You)"}
                </div>
                <div
                  style={{ color: "var(--color-text-secondary)", fontSize: 12 }}
                >
                  @{member.user.username}
                </div>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-2)",
              }}
            >
              {isOwner && member.user.id !== user?.id ? (
                <Select
                  value={member.role}
                  onChange={(e) =>
                    changeRoleMutation.mutate({
                      userId: member.user.id,
                      role: e.target.value,
                    })
                  }
                  disabled={changeRoleMutation.isPending}
                >
                  <option value="member">Member</option>
                  <option value="owner">Owner</option>
                </Select>
              ) : (
                <span
                  className="badge badge-secondary"
                  style={{ display: "flex", alignItems: "center", gap: 4 }}
                >
                  {member.role === "owner" && <Shield size={12} />}
                  {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                </span>
              )}

              {isOwner && member.user.id !== user?.id && (
                <button
                  className="btn btn-ghost btn-icon"
                  style={{ color: "var(--color-danger)" }}
                  onClick={() => removeMutation.mutate(member.user.id)}
                  disabled={removeMutation.isPending}
                >
                  <UserMinus size={16} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {showAddMember && (
        <AddMemberModal
          workspaceId={workspace.id}
          existingMemberIds={members?.map((m) => m.user.id) || []}
          onClose={() => setShowAddMember(false)}
        />
      )}
    </div>
  );
}

function AddMemberModal({
  workspaceId,
  existingMemberIds,
  onClose,
}: {
  workspaceId: string;
  existingMemberIds: string[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const { data: connections, isLoading } = useQuery({
    queryKey: queryKeys.connections.list(),
    queryFn: () => connectionsApi.list(),
  });

  const addMutation = useMutation({
    mutationFn: (userId: string) =>
      workspacesApi.addMember(workspaceId, { user_id: userId, role: "member" }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaces.members(workspaceId),
      });
      onClose();
    },
  });

  const activeConnections = connections?.items || [];
  const availableUsers = activeConnections
    .map((c) => (c.user_lo_rel.id === user?.id ? c.user_hi_rel : c.user_lo_rel))
    .filter((u) => !existingMemberIds.includes(u.id));

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Add Member"
      description="Select a connection to add to this workspace."
      footer={
        <button className="btn btn-secondary" onClick={onClose}>
          Close
        </button>
      }
    >
      {isLoading ? (
        <LoadingSpinner />
      ) : availableUsers.length === 0 ? (
        <p
          style={{
            color: "var(--color-text-secondary)",
            textAlign: "center",
            padding: "var(--space-4)",
          }}
        >
          You don't have any available connections to add. Go to Connections to
          find users.
        </p>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          {availableUsers.map((u) => (
            <div
              key={u.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "var(--space-2) var(--space-3)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ fontWeight: 500 }}>{u.full_name}</div>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => addMutation.mutate(u.id)}
                disabled={addMutation.isPending}
              >
                Add
              </button>
            </div>
          ))}
        </div>
      )}
      {addMutation.isError && (
        <div style={{ marginTop: "var(--space-3)" }}>
          <ErrorMessage message={getApiErrorMessage(addMutation.error)} />
        </div>
      )}
    </Modal>
  );
}
