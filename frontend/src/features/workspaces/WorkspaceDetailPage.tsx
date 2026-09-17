import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FolderPlus,
  Layers,
  Users,
  Calendar,
  Edit2,
  Trash2,
} from "lucide-react";
import { workspacesApi, projectsApi } from "@/api/fetchers";
import { queryKeys } from "@/api/queryKeys";
import type { Project } from "@/types";
import {
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Modal,
  FormField,
  Input,
  Textarea,
} from "@/components/ui";
import { useWebSocket } from "@/contexts/WebSocketContext";
import { WorkspaceMembersPanel } from "./WorkspaceMembersPanel";

function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!error) return fallback;
  const axiosErr = error as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return axiosErr.response?.data?.detail || axiosErr.message || fallback;
}

export function WorkspaceDetailPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { joinChannel, leaveChannel } = useWebSocket();

  useEffect(() => {
    if (workspaceId) {
      joinChannel(`workspace:${workspaceId}`);
      return () => {
        leaveChannel(`workspace:${workspaceId}`);
      };
    }
  }, [workspaceId, joinChannel, leaveChannel]);

  // Create project state
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");

  // Edit workspace state
  const [isEditWsOpen, setIsEditWsOpen] = useState(false);
  const [editWsName, setEditWsName] = useState("");
  const [editWsDesc, setEditWsDesc] = useState("");
  const [isDeleteWsOpen, setIsDeleteWsOpen] = useState(false);

  // Edit / Delete selected project state
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [isEditProjectOpen, setIsEditProjectOpen] = useState(false);
  const [editProjName, setEditProjName] = useState("");
  const [editProjDesc, setEditProjDesc] = useState("");
  const [isDeleteProjectOpen, setIsDeleteProjectOpen] = useState(false);

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

  const editWorkspaceMutation = useMutation({
    mutationFn: (payload: { name: string; description?: string | null }) =>
      workspacesApi.update(workspaceId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaces.detail(workspaceId!),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaces.list(),
      });
      setIsEditWsOpen(false);
    },
  });

  const deleteWorkspaceMutation = useMutation({
    mutationFn: () => workspacesApi.delete(workspaceId!),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaces.all(),
      });
      navigate("/workspaces");
    },
  });

  const editProjectMutation = useMutation({
    mutationFn: (payload: { name: string; description?: string | null }) =>
      projectsApi.update(selectedProject!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.byWorkspace(workspaceId!),
      });
      setIsEditProjectOpen(false);
      setSelectedProject(null);
    },
  });

  const deleteProjectMutation = useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.byWorkspace(workspaceId!),
      });
      setIsDeleteProjectOpen(false);
      setSelectedProject(null);
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
          <div
            style={{
              fontSize: "12px",
              color: "var(--color-text-secondary)",
              marginTop: "2px",
              fontWeight: 500,
            }}
          >
            /{workspace.slug}
          </div>
          {workspace.description && (
            <p className="page-subtitle" style={{ marginTop: "4px" }}>
              {workspace.description}
            </p>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              setEditWsName(workspace.name);
              setEditWsDesc(workspace.description || "");
              setIsEditWsOpen(true);
            }}
          >
            <Edit2 size={13} /> Edit
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ color: "var(--color-danger)" }}
            onClick={() => setIsDeleteWsOpen(true)}
          >
            <Trash2 size={13} /> Delete
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsCreateProjectOpen(true)}
          >
            <FolderPlus size={16} />
            New Project
          </button>
        </div>
      </div>

      <div className="page-content">
        {/* Workspace Meta & Members */}
        <div className="card mb-6" style={{ padding: "16px 20px" }}>
          <div
            style={{
              display: "flex",
              gap: "24px",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "13px",
              }}
            >
              <Calendar size={14} className="text-secondary" />
              <span className="text-secondary">Created:</span>
              <span>{new Date(workspace.created_at).toLocaleDateString()}</span>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "13px",
              }}
            >
              <Users size={14} className="text-secondary" />
              <span className="text-secondary">Members:</span>
              <span>{members?.length || 0}</span>
            </div>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "var(--space-6)",
            marginBottom: "var(--space-6)",
          }}
        >
          <WorkspaceMembersPanel workspace={workspace} />
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
                  type="button"
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
                <div
                  key={project.id}
                  className="card card-hover"
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    minHeight: "160px",
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        justifyContent: "space-between",
                        marginBottom: "12px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: "12px",
                        }}
                      >
                        <div
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: "var(--radius-md)",
                            background: "var(--color-brand-muted)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "var(--color-brand)",
                            flexShrink: 0,
                            marginTop: "2px",
                          }}
                        >
                          <Layers size={18} />
                        </div>
                        <div>
                          <h3
                            style={{
                              fontSize: "16px",
                              fontWeight: 600,
                              lineHeight: 1.3,
                            }}
                          >
                            <Link
                              to={`/projects/${project.id}`}
                              style={{
                                textDecoration: "none",
                                color: "inherit",
                              }}
                              className="project-title-link"
                            >
                              {project.name}
                            </Link>
                          </h3>
                          <div
                            style={{
                              fontSize: "12px",
                              color: "var(--color-text-secondary)",
                              marginTop: "2px",
                              fontWeight: 500,
                            }}
                          >
                            {project.slug}
                          </div>
                        </div>
                      </div>

                      {/* Card Edit/Delete Actions */}
                      <div style={{ display: "flex", gap: "4px" }}>
                        <button
                          type="button"
                          className="btn btn-ghost btn-icon"
                          style={{ width: "28px", height: "28px" }}
                          title="Edit Project"
                          aria-label={`Edit project ${project.name}`}
                          onClick={() => {
                            setSelectedProject(project);
                            setEditProjName(project.name);
                            setEditProjDesc(project.description || "");
                            setIsEditProjectOpen(true);
                          }}
                        >
                          <Edit2 size={13} />
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost btn-icon"
                          style={{
                            width: "28px",
                            height: "28px",
                            color: "var(--color-danger)",
                          }}
                          title="Delete Project"
                          aria-label={`Delete project ${project.name}`}
                          onClick={() => {
                            setSelectedProject(project);
                            setIsDeleteProjectOpen(true);
                          }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
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
                    <span>
                      Updated{" "}
                      {new Date(project.updated_at).toLocaleDateString()}
                    </span>
                    <Link
                      to={`/projects/${project.id}`}
                      className="text-primary text-sm font-semibold"
                      style={{ textDecoration: "none" }}
                    >
                      View Board →
                    </Link>
                  </div>
                </div>
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
              disabled={
                createProjectMutation.isPending || !newProjectName.trim()
              }
            >
              {createProjectMutation.isPending
                ? "Creating..."
                : "Create Project"}
            </button>
          </>
        }
      >
        {createProjectMutation.isError && (
          <div className="mb-4">
            <ErrorMessage
              message={getApiErrorMessage(
                createProjectMutation.error,
                "Failed to create project. Please check your inputs.",
              )}
            />
          </div>
        )}
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

      {/* Edit Workspace Modal */}
      <Modal
        isOpen={isEditWsOpen}
        onClose={() => setIsEditWsOpen(false)}
        title="Edit Workspace"
        description="Update the workspace name and purpose."
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsEditWsOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="edit-workspace-form"
              className="btn btn-primary"
              disabled={editWorkspaceMutation.isPending || !editWsName.trim()}
            >
              {editWorkspaceMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          </>
        }
      >
        {editWorkspaceMutation.isError && (
          <div className="mb-4">
            <ErrorMessage
              message={getApiErrorMessage(
                editWorkspaceMutation.error,
                "Failed to update workspace. Please try again.",
              )}
            />
          </div>
        )}
        <form
          id="edit-workspace-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!editWsName.trim()) return;
            editWorkspaceMutation.mutate({
              name: editWsName.trim(),
              description: editWsDesc.trim() || null,
            });
          }}
        >
          <FormField label="Workspace Name" htmlFor="editWsName" required>
            <Input
              id="editWsName"
              value={editWsName}
              onChange={(e) => setEditWsName(e.target.value)}
              required
              autoFocus
            />
          </FormField>
          <FormField label="Description" htmlFor="editWsDesc">
            <Textarea
              id="editWsDesc"
              rows={3}
              value={editWsDesc}
              onChange={(e) => setEditWsDesc(e.target.value)}
            />
          </FormField>
        </form>
      </Modal>

      {/* Delete Workspace Modal */}
      <Modal
        isOpen={isDeleteWsOpen}
        onClose={() => setIsDeleteWsOpen(false)}
        title="Delete Workspace"
        description="Are you sure you want to delete this workspace?"
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsDeleteWsOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{
                backgroundColor: "var(--color-danger)",
                borderColor: "var(--color-danger)",
              }}
              disabled={deleteWorkspaceMutation.isPending}
              onClick={() => deleteWorkspaceMutation.mutate()}
            >
              {deleteWorkspaceMutation.isPending
                ? "Deleting..."
                : "Yes, Delete Workspace"}
            </button>
          </>
        }
      >
        {deleteWorkspaceMutation.isError && (
          <div className="mb-4">
            <ErrorMessage
              message={getApiErrorMessage(
                deleteWorkspaceMutation.error,
                "Failed to delete workspace. Please try again.",
              )}
            />
          </div>
        )}
        <p
          style={{
            fontSize: "14px",
            color: "var(--color-text-secondary)",
            lineHeight: 1.5,
          }}
        >
          Workspace <strong>{workspace.name}</strong> will be permanently
          removed along with all its projects, tasks, and member associations.
          This action cannot be undone.
        </p>
      </Modal>

      {/* Edit Project Modal */}
      {selectedProject && (
        <Modal
          isOpen={isEditProjectOpen}
          onClose={() => {
            setIsEditProjectOpen(false);
            setSelectedProject(null);
          }}
          title="Edit Project"
          description="Update project name and description."
          footer={
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setIsEditProjectOpen(false);
                  setSelectedProject(null);
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                form="edit-proj-modal-form"
                className="btn btn-primary"
                disabled={editProjectMutation.isPending || !editProjName.trim()}
              >
                {editProjectMutation.isPending ? "Saving..." : "Save Changes"}
              </button>
            </>
          }
        >
          {editProjectMutation.isError && (
            <div className="mb-4">
              <ErrorMessage
                message={getApiErrorMessage(
                  editProjectMutation.error,
                  "Failed to update project. Please try again.",
                )}
              />
            </div>
          )}
          <form
            id="edit-proj-modal-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (!editProjName.trim()) return;
              editProjectMutation.mutate({
                name: editProjName.trim(),
                description: editProjDesc.trim() || null,
              });
            }}
          >
            <FormField label="Project Name" htmlFor="editProjName" required>
              <Input
                id="editProjName"
                value={editProjName}
                onChange={(e) => setEditProjName(e.target.value)}
                required
                autoFocus
              />
            </FormField>
            <FormField label="Description" htmlFor="editProjDesc">
              <Textarea
                id="editProjDesc"
                rows={3}
                value={editProjDesc}
                onChange={(e) => setEditProjDesc(e.target.value)}
              />
            </FormField>
          </form>
        </Modal>
      )}

      {/* Delete Project Modal */}
      {selectedProject && (
        <Modal
          isOpen={isDeleteProjectOpen}
          onClose={() => {
            setIsDeleteProjectOpen(false);
            setSelectedProject(null);
          }}
          title="Delete Project"
          description={`Are you sure you want to delete "${selectedProject.name}"?`}
          footer={
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setIsDeleteProjectOpen(false);
                  setSelectedProject(null);
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                style={{
                  backgroundColor: "var(--color-danger)",
                  borderColor: "var(--color-danger)",
                }}
                disabled={deleteProjectMutation.isPending}
                onClick={() => deleteProjectMutation.mutate(selectedProject.id)}
              >
                {deleteProjectMutation.isPending
                  ? "Deleting..."
                  : "Yes, Delete Project"}
              </button>
            </>
          }
        >
          {deleteProjectMutation.isError && (
            <div className="mb-4">
              <ErrorMessage
                message={getApiErrorMessage(
                  deleteProjectMutation.error,
                  "Failed to delete project. Please try again.",
                )}
              />
            </div>
          )}
          <p
            style={{
              fontSize: "14px",
              color: "var(--color-text-secondary)",
              lineHeight: 1.5,
            }}
          >
            Project <strong>{selectedProject.name}</strong> will be permanently
            deleted along with all its issues and comments.
          </p>
        </Modal>
      )}
    </div>
  );
}
