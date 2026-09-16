import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Layers, Users, Calendar } from "lucide-react";
import { workspacesApi, projectsApi } from "@/api/fetchers";
import { queryKeys } from "@/api/queryKeys";
import {
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Avatar,
  Modal,
  FormField,
  Input,
  Textarea,
} from "@/components/ui";

export function WorkspaceDetailPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const queryClient = useQueryClient();
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");

  const {
    data: workspace,
    isLoading: isWsLoading,
    error: wsError,
  } = useQuery({
    queryKey: queryKeys.workspaces.detail(workspaceId ?? ""),
    queryFn: () => workspacesApi.get(workspaceId!),
    enabled: !!workspaceId,
  });

  const {
    data: projects,
    isLoading: isProjectsLoading,
    error: projectsError,
  } = useQuery({
    queryKey: queryKeys.projects.byWorkspace(workspaceId ?? ""),
    queryFn: () => projectsApi.list(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: members } = useQuery({
    queryKey: queryKeys.workspaces.members(workspaceId ?? ""),
    queryFn: () => workspacesApi.listMembers(workspaceId!),
    enabled: !!workspaceId,
  });

  const createProjectMutation = useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      projectsApi.create(workspaceId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.byWorkspace(workspaceId!),
      });
      setIsCreateProjectOpen(false);
      setNewProjectName("");
      setNewProjectDesc("");
    },
  });

  if (isWsLoading) return <LoadingSpinner fullPage />;
  if (wsError || !workspace) {
    return <ErrorMessage message="Failed to load workspace details" />;
  }

  return (
    <div>
      {/* Workspace Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{workspace.name}</h1>
          {workspace.description && (
            <p className="page-subtitle">{workspace.description}</p>
          )}
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setIsCreateProjectOpen(true)}
        >
          <FolderPlus size={16} />
          New Project
        </button>
      </div>

      <div className="page-content">
        {/* Workspace Meta & Members */}
        <div className="card mb-6" style={{ padding: "16px 20px" }}>
          <div style={{ display: "flex", gap: "24px", alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
              <Calendar size={14} className="text-secondary" />
              <span className="text-secondary">Created:</span>
              <span>{new Date(workspace.created_at).toLocaleDateString()}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
              <Users size={14} className="text-secondary" />
              <span className="text-secondary">Members:</span>
              <div style={{ display: "flex", gap: "4px" }}>
                {members?.map((m) => (
                  <span key={m.id} title={`${m.user.full_name} (${m.role})`}>
                    <Avatar user={m.user} size="sm" />
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Projects Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 style={{ fontSize: "18px", fontWeight: 600 }}>Projects</h2>
            <span className="text-secondary text-sm">
              {projects?.items.length ?? 0} project
              {(projects?.items.length ?? 0) !== 1 ? "s" : ""}
            </span>
          </div>

          {isProjectsLoading ? (
            <LoadingSpinner />
          ) : projectsError ? (
            <ErrorMessage message="Failed to load projects" />
          ) : !projects || projects.items.length === 0 ? (
            <EmptyState
              title="No projects yet"
              description="Create your first project to start organizing tasks and tracking progress."
              action={
                <button
                  className="btn btn-primary"
                  onClick={() => setIsCreateProjectOpen(true)}
                >
                  <FolderPlus size={16} />
                  Create Project
                </button>
              }
            />
          ) : (
            <div className="grid-auto-fill">
              {projects.items.map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="card card-hover"
                  style={{
                    textDecoration: "none",
                    color: "inherit",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    minHeight: "150px",
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "12px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div
                          style={{
                            width: 34,
                            height: 34,
                            borderRadius: "var(--radius-md)",
                            background: "var(--color-brand-muted)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "var(--color-brand)",
                            flexShrink: 0,
                          }}
                        >
                          <Layers size={18} />
                        </div>
                        <h3 style={{ fontSize: "16px", fontWeight: 600 }}>{project.name}</h3>
                      </div>
                      <span
                        className="badge"
                        style={{
                          background: "var(--color-surface-2)",
                          border: "1px solid var(--color-border)",
                          color: "var(--color-text-secondary)",
                        }}
                      >
                        {project.slug}
                      </span>
                    </div>
                    {project.description && (
                      <p
                        className="text-secondary"
                        style={{
                          fontSize: "13px",
                          lineHeight: 1.5,
                          marginBottom: "16px",
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {project.description}
                      </p>
                    )}
                  </div>
                  <div
                    className="flex items-center justify-between"
                    style={{
                      paddingTop: "12px",
                      borderTop: "1px solid var(--color-border-subtle)",
                      fontSize: "12px",
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    <span>Updated {new Date(project.updated_at).toLocaleDateString()}</span>
                    <span className="text-primary text-sm font-semibold">View Board →</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top-Level Create Project Modal */}
      <Modal
        isOpen={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        title="Create New Project"
        description="Projects help you organize issues, backlogs, and boards."
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsCreateProjectOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="create-project-form"
              className="btn btn-primary"
              disabled={createProjectMutation.isPending || !newProjectName.trim()}
            >
              {createProjectMutation.isPending ? "Creating..." : "Create Project"}
            </button>
          </>
        }
      >
        <form
          id="create-project-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!newProjectName.trim()) return;
            createProjectMutation.mutate({
              name: newProjectName.trim(),
              description: newProjectDesc.trim() || undefined,
            });
          }}
        >
          <FormField label="Project Name" htmlFor="projectName" required>
            <Input
              id="projectName"
              type="text"
              required
              placeholder="e.g., Core Engine, Mobile App"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              autoFocus
            />
          </FormField>

          <FormField
            label="Description"
            htmlFor="projectDesc"
            helperText="Briefly outline what this project accomplishes."
          >
            <Textarea
              id="projectDesc"
              rows={3}
              placeholder="What is this project about?"
              value={newProjectDesc}
              onChange={(e) => setNewProjectDesc(e.target.value)}
            />
          </FormField>
        </form>
      </Modal>
    </div>
  );
}
