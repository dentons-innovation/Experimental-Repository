import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus, UserMinus, Shield, User as UserIcon } from "lucide-react";
import { queryKeys } from "@/api/queryKeys";
import { projectsApi, workspacesApi } from "@/api/fetchers";
import { getApiErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { LoadingSpinner, ErrorMessage, Modal, Select } from "@/components/ui";
import type { Project } from "@/types";

export function ProjectMembersPanel({ project }: { project: Project }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showAddMember, setShowAddMember] = useState(false);

  const {
    data: members,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKeys.projects.members(project.id),
    queryFn: () => projectsApi.listMembers(project.id),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) =>
      projectsApi.removeMember(project.id, userId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.members(project.id),
      }),
  });

  const changeRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      fetch(`/api/v1/projects/${project.id}/members/${userId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("pf_auth_token")}`,
        },
        body: JSON.stringify({ role }),
      }).then((res) => {
        if (!res.ok) throw new Error("Failed to change role");
        return res.json();
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.members(project.id),
      }),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={getApiErrorMessage(error)} />;

  const currentUserMember = members?.find((m) => m.user.id === user?.id);
  const isAdmin = currentUserMember?.role === "admin";

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
          Project Members ({members?.length || 0})
        </h2>
        {isAdmin && (
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
              {isAdmin && member.user.id !== user?.id ? (
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
                  <option value="admin">Admin</option>
                </Select>
              ) : (
                <span
                  className="badge badge-secondary"
                  style={{ display: "flex", alignItems: "center", gap: 4 }}
                >
                  {member.role === "admin" && <Shield size={12} />}
                  {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                </span>
              )}

              {isAdmin && member.user.id !== user?.id && (
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
          project={project}
          existingMemberIds={members?.map((m) => m.user.id) || []}
          onClose={() => setShowAddMember(false)}
        />
      )}
    </div>
  );
}

function AddMemberModal({
  project,
  existingMemberIds,
  onClose,
}: {
  project: Project;
  existingMemberIds: string[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();

  // For a project, we can only add users who are already in the workspace
  const { data: workspaceMembers, isLoading } = useQuery({
    queryKey: queryKeys.workspaces.members(project.workspace_id),
    queryFn: () => workspacesApi.listMembers(project.workspace_id),
  });

  const addMutation = useMutation({
    mutationFn: (userId: string) =>
      projectsApi.addMember(project.id, { user_id: userId, role: "member" }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.members(project.id),
      });
      onClose();
    },
  });

  const availableUsers =
    workspaceMembers
      ?.map((m) => m.user)
      .filter((u) => !existingMemberIds.includes(u.id)) || [];

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Add Member"
      description="Select a workspace member to add to this project."
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
          All workspace members are already in this project.
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
