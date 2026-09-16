import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, ArrowLeft, Filter } from "lucide-react";
import { projectsApi, tasksApi } from "@/api/fetchers";
import { queryKeys } from "@/api/queryKeys";
import type { Task, TaskPriority, TaskStatus } from "@/types";
import { TASK_STATUS_LABELS } from "@/types";
import {
  LoadingSpinner,
  ErrorMessage,
  TaskPriorityBadge,
  LabelChip,
  Avatar,
} from "@/components/ui";

const COLUMNS: TaskStatus[] = ["todo", "in_progress", "in_review", "done"];

export function ProjectBoardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDesc, setTaskDesc] = useState("");
  const [taskPriority, setTaskPriority] = useState<TaskPriority>("medium");
  const [taskStatus, setTaskStatus] = useState<TaskStatus>("todo");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const {
    data: project,
    isLoading: isProjectLoading,
    error: projectError,
  } = useQuery({
    queryKey: queryKeys.projects.detail(projectId ?? ""),
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const {
    data: tasksData,
    isLoading: isTasksLoading,
    error: tasksError,
  } = useQuery({
    queryKey: queryKeys.tasks.byProject(projectId ?? ""),
    queryFn: () => tasksApi.list(projectId!),
    enabled: !!projectId,
  });

  const createTaskMutation = useMutation({
    mutationFn: (payload: {
      title: string;
      description?: string;
      priority: TaskPriority;
      status: TaskStatus;
    }) => tasksApi.create(projectId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.byProject(projectId!),
      });
      setIsCreateOpen(false);
      setTaskTitle("");
      setTaskDesc("");
      setTaskPriority("medium");
      setTaskStatus("todo");
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ task, newStatus }: { task: Task; newStatus: TaskStatus }) =>
      tasksApi.update(task.id, {
        version: task.version,
        status: newStatus,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.byProject(projectId!),
      });
    },
  });

  if (isProjectLoading) return <LoadingSpinner fullPage />;
  if (projectError || !project) {
    return <ErrorMessage message="Failed to load project" />;
  }

  const tasks = tasksData?.items ?? [];

  return (
    <div className="page-container">
      {/* Navigation breadcrumb & Header */}
      <div style={{ marginBottom: "12px" }}>
        <Link
          to={`/workspaces/${project.workspace_id}`}
          className="text-secondary"
          style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "13px" }}
        >
          <ArrowLeft size={14} /> Back to Workspace
        </Link>
      </div>

      <div className="page-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span className="badge" style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-color)" }}>
              {project.slug.toUpperCase()}
            </span>
            <h1 className="page-title">{project.name}</h1>
          </div>
          {project.description && (
            <p className="page-subtitle">{project.description}</p>
          )}
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            className="btn btn-primary"
            onClick={() => setIsCreateOpen(true)}
          >
            <Plus size={16} />
            Create Issue
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="card mb-6" style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "var(--text-secondary)" }}>
          <Filter size={14} />
          <span>Status:</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            className={`btn btn-sm ${statusFilter === "all" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setStatusFilter("all")}
          >
            All
          </button>
          {COLUMNS.map((col) => (
            <button
              key={col}
              className={`btn btn-sm ${statusFilter === col ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setStatusFilter(col)}
            >
              {TASK_STATUS_LABELS[col]}
            </button>
          ))}
        </div>
      </div>

      {/* Board Columns */}
      {isTasksLoading ? (
        <LoadingSpinner />
      ) : tasksError ? (
        <ErrorMessage message="Failed to load tasks" />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, minmax(280px, 1fr))",
            gap: "16px",
            alignItems: "start",
            overflowX: "auto",
            paddingBottom: "16px",
          }}
        >
          {COLUMNS.filter((col) => statusFilter === "all" || statusFilter === col).map((col) => {
            const columnTasks = tasks.filter((t) => t.status === col);
            return (
              <div
                key={col}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  borderRadius: "var(--radius-lg)",
                  border: "1px solid var(--border-subtle)",
                  padding: "16px",
                  minHeight: "450px",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                {/* Column header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "12px",
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    {TASK_STATUS_LABELS[col]}
                  </span>
                  <span
                    style={{
                      backgroundColor: "var(--bg-card)",
                      padding: "2px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {columnTasks.length}
                  </span>
                </div>

                {/* Task card list */}
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", flex: 1 }}>
                  {columnTasks.length === 0 ? (
                    <div
                      style={{
                        padding: "24px 12px",
                        textAlign: "center",
                        color: "var(--text-muted)",
                        fontSize: "13px",
                        border: "1px dashed var(--border-subtle)",
                        borderRadius: "var(--radius-md)",
                      }}
                    >
                      No issues
                    </div>
                  ) : (
                    columnTasks.map((task) => (
                      <div
                        key={task.id}
                        className="card card-interactive"
                        style={{ padding: "14px", display: "flex", flexDirection: "column", gap: "10px" }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500 }}>
                            {project.slug.toUpperCase()}-{task.id.slice(0, 4)}
                          </span>
                          <TaskPriorityBadge priority={task.priority} />
                        </div>

                        <Link
                          to={`/tasks/${task.id}`}
                          style={{
                            textDecoration: "none",
                            color: "inherit",
                            fontWeight: 600,
                            fontSize: "14px",
                            lineHeight: "1.3",
                          }}
                        >
                          {task.title}
                        </Link>

                        {task.labels && task.labels.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                            {task.labels.map((l) => (
                              <LabelChip key={l.id} name={l.name} color={l.color} />
                            ))}
                          </div>
                        )}

                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginTop: "4px",
                            paddingTop: "8px",
                            borderTop: "1px solid var(--border-subtle)",
                          }}
                        >
                          <Avatar user={task.assignee} size="sm" />
                          <select
                            className="input"
                            style={{ padding: "3px 6px", fontSize: "12px", width: "auto" }}
                            value={task.status}
                            onChange={(e) =>
                              updateStatusMutation.mutate({
                                task,
                                newStatus: e.target.value as TaskStatus,
                              })
                            }
                          >
                            {COLUMNS.map((st) => (
                              <option key={st} value={st}>
                                {TASK_STATUS_LABELS[st]}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Issue Modal */}
      {isCreateOpen && (
        <div className="modal-backdrop" onClick={() => setIsCreateOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "16px" }}>
              Create New Issue
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!taskTitle.trim()) return;
                createTaskMutation.mutate({
                  title: taskTitle.trim(),
                  description: taskDesc.trim() || undefined,
                  priority: taskPriority,
                  status: taskStatus,
                });
              }}
            >
              <div style={{ marginBottom: "14px" }}>
                <label className="label" htmlFor="taskTitle">
                  Title
                </label>
                <input
                  id="taskTitle"
                  className="input"
                  type="text"
                  required
                  placeholder="Issue summary"
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  autoFocus
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
                <div>
                  <label className="label" htmlFor="taskStatusSelect">
                    Status
                  </label>
                  <select
                    id="taskStatusSelect"
                    className="input"
                    value={taskStatus}
                    onChange={(e) => setTaskStatus(e.target.value as TaskStatus)}
                  >
                    {COLUMNS.map((st) => (
                      <option key={st} value={st}>
                        {TASK_STATUS_LABELS[st]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="taskPrioritySelect">
                    Priority
                  </label>
                  <select
                    id="taskPrioritySelect"
                    className="input"
                    value={taskPriority}
                    onChange={(e) => setTaskPriority(e.target.value as TaskPriority)}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              <div style={{ marginBottom: "20px" }}>
                <label className="label" htmlFor="taskDesc">
                  Description
                </label>
                <textarea
                  id="taskDesc"
                  className="input"
                  rows={4}
                  placeholder="Detailed description of the task, steps, or acceptance criteria"
                  value={taskDesc}
                  onChange={(e) => setTaskDesc(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsCreateOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={createTaskMutation.isPending || !taskTitle.trim()}
                >
                  {createTaskMutation.isPending ? "Creating..." : "Create Issue"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
