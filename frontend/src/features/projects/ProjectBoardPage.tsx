import { useState, useRef } from "react";
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
  Modal,
  FormField,
  Input,
  Select,
  Textarea,
} from "@/components/ui";
import { TaskDetailModal } from "@/features/tasks/TaskDetailModal";

const COLUMNS: TaskStatus[] = ["todo", "in_progress", "in_review", "done"];

export function ProjectBoardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [draggedTaskId, setDraggedTaskId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<TaskStatus | null>(null);
  const isDraggingRef = useRef(false);

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

  // Optimistic update for instant visual feedback on drag-and-drop
  const updateStatusMutation = useMutation({
    mutationFn: ({ task, newStatus }: { task: Task; newStatus: TaskStatus }) =>
      tasksApi.update(task.id, {
        version: task.version,
        status: newStatus,
      }),
    onMutate: async ({ task, newStatus }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.tasks.byProject(projectId!),
      });
      const previousTasks = queryClient.getQueryData(
        queryKeys.tasks.byProject(projectId!)
      );

      queryClient.setQueryData(
        queryKeys.tasks.byProject(projectId!),
        (old: { items: Task[]; total: number } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((t) =>
              t.id === task.id ? { ...t, status: newStatus, version: t.version + 1 } : t
            ),
          };
        }
      );

      return { previousTasks };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousTasks) {
        queryClient.setQueryData(
          queryKeys.tasks.byProject(projectId!),
          context.previousTasks
        );
      }
    },
    onSettled: () => {
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

  // Drag & drop handlers
  const handleDragStart = (e: React.DragEvent, taskId: string) => {
    isDraggingRef.current = true;
    setDraggedTaskId(taskId);
    e.dataTransfer.setData("text/plain", taskId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    setDraggedTaskId(null);
    setDragOverColumn(null);
    setTimeout(() => {
      isDraggingRef.current = false;
    }, 80);
  };

  const handleDragOver = (e: React.DragEvent, col: TaskStatus) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragOverColumn !== col) {
      setDragOverColumn(col);
    }
  };

  const handleDragLeave = (e: React.DragEvent, col: TaskStatus) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      if (dragOverColumn === col) {
        setDragOverColumn(null);
      }
    }
  };

  const handleDrop = (e: React.DragEvent, col: TaskStatus) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData("text/plain") || draggedTaskId;
    if (!taskId) return;

    const task = tasks.find((t) => t.id === taskId);
    if (task && task.status !== col) {
      updateStatusMutation.mutate({ task, newStatus: col });
    }

    setDraggedTaskId(null);
    setDragOverColumn(null);
    setTimeout(() => {
      isDraggingRef.current = false;
    }, 80);
  };

  return (
    <div>
      {/* Navigation & Header */}
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <Link
            to={`/workspaces/${project.workspace_id}`}
            className="text-secondary"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "13px" }}
          >
            <ArrowLeft size={14} /> Back
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              className="badge"
              style={{
                backgroundColor: "var(--color-surface-2)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-secondary)",
              }}
            >
              {project.slug.toUpperCase()}
            </span>
            <h1 className="page-title">{project.name}</h1>
          </div>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setIsCreateOpen(true)}
        >
          <Plus size={16} />
          Create Issue
        </button>
      </div>

      <div className="page-content">
        {project.description && (
          <p className="text-secondary mb-4" style={{ fontSize: "14px" }}>
            {project.description}
          </p>
        )}

        {/* Filter Toolbar */}
        <div className="card mb-6" style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "var(--color-text-secondary)" }}>
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
              const isDropTarget = dragOverColumn === col && draggedTaskId !== null;

              return (
                <div
                  key={col}
                  onDragOver={(e) => handleDragOver(e, col)}
                  onDragLeave={(e) => handleDragLeave(e, col)}
                  onDrop={(e) => handleDrop(e, col)}
                  style={{
                    backgroundColor: isDropTarget ? "rgba(109, 107, 244, 0.08)" : "var(--color-surface)",
                    borderRadius: "var(--radius-lg)",
                    border: isDropTarget
                      ? "2px dashed var(--color-brand)"
                      : "1px solid var(--color-border-subtle)",
                    boxShadow: isDropTarget ? "0 0 16px var(--color-brand-glow)" : "none",
                    padding: "16px",
                    minHeight: "480px",
                    display: "flex",
                    flexDirection: "column",
                    transition: "background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease",
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
                    <span style={{ fontWeight: 600, fontSize: "13px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      {TASK_STATUS_LABELS[col]}
                    </span>
                    <span
                      style={{
                        backgroundColor: "var(--color-surface-2)",
                        padding: "2px 8px",
                        borderRadius: "12px",
                        fontSize: "12px",
                        fontWeight: 600,
                        color: "var(--color-text-secondary)",
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
                          color: "var(--color-text-tertiary)",
                          fontSize: "13px",
                          border: "1px dashed var(--color-border-subtle)",
                          borderRadius: "var(--radius-md)",
                        }}
                      >
                        No issues
                      </div>
                    ) : (
                      columnTasks.map((task) => {
                        const isDragging = draggedTaskId === task.id;

                        return (
                          <div
                            key={task.id}
                            className="card card-hover"
                            draggable={true}
                            onDragStart={(e) => handleDragStart(e, task.id)}
                            onDragEnd={handleDragEnd}
                            onClick={(e) => {
                              if (isDraggingRef.current) return;
                              if ((e.target as HTMLElement).tagName === "SELECT") return;
                              setSelectedTaskId(task.id);
                            }}
                            style={{
                              padding: "14px",
                              display: "flex",
                              flexDirection: "column",
                              gap: "10px",
                              cursor: isDragging ? "grabbing" : "grab",
                              opacity: isDragging ? 0.4 : 1,
                              transform: isDragging ? "scale(0.98)" : "none",
                              border: isDragging ? "2px dashed var(--color-brand)" : undefined,
                              transition: "opacity 150ms ease, transform 150ms ease, border-color 150ms ease",
                              userSelect: "none",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                              <span style={{ fontSize: "12px", color: "var(--color-text-secondary)", fontWeight: 500 }}>
                                {project.slug.toUpperCase()}-{task.id.slice(0, 4)}
                              </span>
                              <TaskPriorityBadge priority={task.priority} />
                            </div>

                            <div
                              style={{
                                fontWeight: 600,
                                fontSize: "14px",
                                lineHeight: "1.3",
                                color: "var(--color-text)",
                              }}
                            >
                              {task.title}
                            </div>

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
                                borderTop: "1px solid var(--color-border-subtle)",
                              }}
                            >
                              <Avatar user={task.assignee} size="sm" />
                              <select
                                className="input"
                                style={{ padding: "4px 8px", fontSize: "12px", width: "auto" }}
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
                        );
                      })
                    )}

                    {isDropTarget && (
                      <div
                        style={{
                          padding: "12px",
                          borderRadius: "var(--radius-md)",
                          border: "2px dashed var(--color-brand)",
                          background: "var(--color-brand-muted)",
                          color: "var(--color-brand)",
                          fontSize: "12px",
                          fontWeight: 600,
                          textAlign: "center",
                          animation: "fadeIn 150ms ease",
                        }}
                      >
                        Drop here to set as {TASK_STATUS_LABELS[col]}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Top-Level Create Issue Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New Issue"
        description="Track bugs, features, and tasks across this project."
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="create-issue-form"
              className="btn btn-primary"
              disabled={createTaskMutation.isPending || !taskTitle.trim()}
            >
              {createTaskMutation.isPending ? "Creating..." : "Create Issue"}
            </button>
          </>
        }
      >
        <form
          id="create-issue-form"
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
          <FormField label="Title" htmlFor="taskTitle" required>
            <Input
              id="taskTitle"
              type="text"
              required
              placeholder="Issue summary"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              autoFocus
            />
          </FormField>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <FormField label="Status" htmlFor="taskStatusSelect">
              <Select
                id="taskStatusSelect"
                value={taskStatus}
                onChange={(e) => setTaskStatus(e.target.value as TaskStatus)}
              >
                {COLUMNS.map((st) => (
                  <option key={st} value={st}>
                    {TASK_STATUS_LABELS[st]}
                  </option>
                ))}
              </Select>
            </FormField>

            <FormField label="Priority" htmlFor="taskPrioritySelect">
              <Select
                id="taskPrioritySelect"
                value={taskPriority}
                onChange={(e) => setTaskPriority(e.target.value as TaskPriority)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </Select>
            </FormField>
          </div>

          <FormField
            label="Description"
            htmlFor="taskDesc"
            helperText="Provide context, reproduction steps, or acceptance criteria."
          >
            <Textarea
              id="taskDesc"
              rows={4}
              placeholder="Detailed description of the issue..."
              value={taskDesc}
              onChange={(e) => setTaskDesc(e.target.value)}
            />
          </FormField>
        </form>
      </Modal>

      {/* Top-Level Issue Detail Modal */}
      <TaskDetailModal
        taskId={selectedTaskId}
        isOpen={Boolean(selectedTaskId)}
        onClose={() => setSelectedTaskId(null)}
        projectSlug={project.slug}
      />
    </div>
  );
}
