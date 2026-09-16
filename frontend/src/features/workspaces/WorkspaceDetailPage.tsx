import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Layers, Users, Calendar } from "lucide-react";
import { workspacesApi, projectsApi } from "@/api/fetchers";
import { queryKeys } from "@/api/queryKeys";
import { LoadingSpinner, ErrorMessage, EmptyState, Avatar } from "@/components/ui";

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
    <div className="page-container">
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
            <div style={{ display: "flex", gap: "-6px" }}>
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
          <div className="grid grid-cols-3">
            {projects.items.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="card card-interactive"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                  <Layers size={18} className="text-primary" />
                  <h3 style={{ fontSize: "16px", fontWeight: 600 }}>{project.name}</h3>
                </div>
                {project.description && (
                  <p className="text-secondary truncate" style={{ fontSize: "13px", marginBottom: "16px" }}>
                    {project.description}
                  </p>
                )}
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Updated {new Date(project.updated_at).toLocaleDateString()}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {isCreateProjectOpen && (
        <div className="modal-backdrop" onClick={() => setIsCreateProjectOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "16px" }}>
              Create New Project
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!newProjectName.trim()) return;
                createProjectMutation.mutate({
                  name: newProjectName.trim(),
                  description: newProjectDesc.trim() || undefined,
                });
              }}
            >
              <div style={{ marginBottom: "16px" }}>
                <label className="label" htmlFor="projectName">
                  Project Name
                </label>
                <input
                  id="projectName"
                  className="input"
                  type="text"
                  required
                  placeholder="e.g., Core Engine, Mobile App"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  autoFocus
                />
              </div>
              <div style={{ marginBottom: "20px" }}>
                <label className="label" htmlFor="projectDesc">
                  Description (optional)
                </label>
                <textarea
                  id="projectDesc"
                  className="input"
                  rows={3}
                  placeholder="What is this project about?"
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsCreateProjectOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={createProjectMutation.isPending || !newProjectName.trim()}
                >
                  {createProjectMutation.isPending ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
