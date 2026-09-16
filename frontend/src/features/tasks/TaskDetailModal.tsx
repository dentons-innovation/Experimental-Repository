import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink,
  MessageSquare,
  History,
  Send,
  User as UserIcon,
  Tag,
} from "lucide-react";
import { tasksApi, commentsApi } from "@/api/fetchers";
import { queryKeys } from "@/api/queryKeys";
import type { TaskPriority, TaskStatus } from "@/types";
import { TASK_STATUS_LABELS, TASK_PRIORITY_LABELS } from "@/types";
import {
  Modal,
  LoadingSpinner,
  ErrorMessage,
  TaskStatusBadge,
  TaskPriorityBadge,
  LabelChip,
  Avatar,
  Select,
} from "@/components/ui";

const ALL_STATUSES: TaskStatus[] = ["todo", "in_progress", "in_review", "done"];
const ALL_PRIORITIES: TaskPriority[] = ["low", "medium", "high", "critical"];

interface TaskDetailModalProps {
  taskId: string | null;
  isOpen: boolean;
  onClose: () => void;
  projectSlug?: string;
}

export function TaskDetailModal({
  taskId,
  isOpen,
  onClose,
  projectSlug,
}: TaskDetailModalProps) {
  const queryClient = useQueryClient();
  const [commentText, setCommentText] = useState("");
  const [occError, setOccError] = useState<string | null>(null);

  const {
    data: task,
    isLoading: isTaskLoading,
    error: taskError,
  } = useQuery({
    queryKey: queryKeys.tasks.detail(taskId ?? ""),
    queryFn: () => tasksApi.get(taskId!),
    enabled: !!taskId && isOpen,
  });

  const {
    data: commentsData,
    isLoading: isCommentsLoading,
  } = useQuery({
    queryKey: queryKeys.comments.byTask(taskId ?? ""),
    queryFn: () => commentsApi.list(taskId!),
    enabled: !!taskId && isOpen,
  });

  const { data: activityData } = useQuery({
    queryKey: queryKeys.tasks.activity(taskId ?? ""),
    queryFn: () => tasksApi.getActivity(taskId!),
    enabled: !!taskId && isOpen,
  });

  const updateTaskMutation = useMutation({
    mutationFn: (payload: { status?: TaskStatus; priority?: TaskPriority }) => {
      setOccError(null);
      return tasksApi.update(taskId!, {
        version: task!.version,
        ...payload,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.detail(taskId!),
      });
      if (task?.project_id) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.tasks.byProject(task.project_id),
        });
      }
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.activity(taskId!),
      });
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosErr.response?.status === 409) {
        setOccError(
          "Conflict: This task was modified concurrently by another update. Please re-open to refresh."
        );
      } else {
        setOccError("Failed to update task. Please try again.");
      }
    },
  });

  const addCommentMutation = useMutation({
    mutationFn: (text: string) => commentsApi.create(taskId!, text),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.comments.byTask(taskId!),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.activity(taskId!),
      });
      setCommentText("");
    },
  });

  if (!isOpen || !taskId) return null;

  const comments = commentsData?.items ?? [];
  const activities = activityData?.items ?? [];
  const slugPrefix = projectSlug ? `${projectSlug.toUpperCase()}-` : "ISSUE-";

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth={720}
      title={
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontSize: "12px",
              color: "var(--color-brand)",
              fontWeight: 700,
              background: "var(--color-brand-muted)",
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {slugPrefix}{taskId.slice(0, 4)}
          </span>
          <span>{task?.title ?? "Issue Details"}</span>
        </div>
      }
      footer={
        <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
          <Link
            to={`/tasks/${taskId}`}
            className="text-secondary text-sm flex items-center gap-1"
            style={{ textDecoration: "none" }}
            onClick={onClose}
          >
            <ExternalLink size={13} /> Open as standalone page
          </Link>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      }
    >
      {isTaskLoading ? (
        <div style={{ padding: "40px 0" }}>
          <LoadingSpinner />
        </div>
      ) : taskError || !task ? (
        <ErrorMessage message="Failed to load task details" />
      ) : (
        <div>
          {occError && (
            <div className="error-state mb-4" style={{ padding: "10px 14px" }}>
              {occError}
            </div>
          )}

          {/* Controls Bar: Status, Priority, Badges */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
              padding: "16px",
              background: "var(--color-surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              marginBottom: "20px",
            }}
          >
            <div>
              <label className="input-label" htmlFor="modalTaskStatus">
                Status
              </label>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Select
                  id="modalTaskStatus"
                  value={task.status}
                  disabled={updateTaskMutation.isPending}
                  onChange={(e) =>
                    updateTaskMutation.mutate({
                      status: e.target.value as TaskStatus,
                    })
                  }
                >
                  {ALL_STATUSES.map((st) => (
                    <option key={st} value={st}>
                      {TASK_STATUS_LABELS[st]}
                    </option>
                  ))}
                </Select>
                <TaskStatusBadge status={task.status} />
              </div>
            </div>

            <div>
              <label className="input-label" htmlFor="modalTaskPriority">
                Priority
              </label>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Select
                  id="modalTaskPriority"
                  value={task.priority}
                  disabled={updateTaskMutation.isPending}
                  onChange={(e) =>
                    updateTaskMutation.mutate({
                      priority: e.target.value as TaskPriority,
                    })
                  }
                >
                  {ALL_PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {TASK_PRIORITY_LABELS[p]}
                    </option>
                  ))}
                </Select>
                <TaskPriorityBadge priority={task.priority} />
              </div>
            </div>
          </div>

          {/* Description */}
          <div style={{ marginBottom: "20px" }}>
            <span className="input-label">Description</span>
            <div
              style={{
                backgroundColor: "var(--color-surface-2)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "14px 16px",
                fontSize: "14px",
                lineHeight: "1.6",
                color: task.description ? "var(--color-text)" : "var(--color-text-tertiary)",
                minHeight: "70px",
                whiteSpace: "pre-wrap",
              }}
            >
              {task.description || "No description provided."}
            </div>
          </div>

          {/* Meta Attributes: Assignee, Reporter, Labels */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "24px",
              paddingBottom: "16px",
              borderBottom: "1px solid var(--color-border)",
              marginBottom: "20px",
            }}
          >
            <div>
              <span className="input-label flex items-center gap-1">
                <UserIcon size={12} /> Assignee
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
                <Avatar user={task.assignee} size="sm" />
                <span style={{ fontSize: "13px" }}>
                  {task.assignee?.full_name ?? "Unassigned"}
                </span>
              </div>
            </div>

            <div>
              <span className="input-label flex items-center gap-1">
                <UserIcon size={12} /> Reporter
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
                <Avatar user={task.creator} size="sm" />
                <span style={{ fontSize: "13px" }}>
                  {task.creator?.full_name ?? "Unknown"}
                </span>
              </div>
            </div>

            {task.labels && task.labels.length > 0 && (
              <div style={{ flex: 1 }}>
                <span className="input-label flex items-center gap-1">
                  <Tag size={12} /> Labels
                </span>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
                  {task.labels.map((l) => (
                    <LabelChip key={l.id} name={l.name} color={l.color} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Comments Section */}
          <div style={{ marginBottom: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <MessageSquare size={16} className="text-secondary" />
              <h3 style={{ fontSize: "14px", fontWeight: 600 }}>
                Comments ({comments.length})
              </h3>
            </div>

            {/* Comment Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!commentText.trim()) return;
                addCommentMutation.mutate(commentText.trim());
              }}
              style={{ marginBottom: "16px" }}
            >
              <textarea
                className="input textarea"
                rows={2}
                placeholder="Write a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                style={{ minHeight: "65px" }}
              />
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={addCommentMutation.isPending || !commentText.trim()}
                >
                  <Send size={13} />
                  {addCommentMutation.isPending ? "Posting..." : "Comment"}
                </button>
              </div>
            </form>

            {/* Comments List */}
            {isCommentsLoading ? (
              <LoadingSpinner />
            ) : comments.length === 0 ? (
              <p className="text-secondary" style={{ fontSize: "13px" }}>
                No comments yet.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {comments.map((c) => (
                  <div
                    key={c.id}
                    style={{
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--color-surface-2)",
                      border: "1px solid var(--color-border-subtle)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <Avatar user={c.author} size="sm" />
                      <span style={{ fontWeight: 600, fontSize: "13px" }}>{c.author.full_name}</span>
                      <span className="text-secondary" style={{ fontSize: "11px", marginLeft: "auto" }}>
                        {new Date(c.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div style={{ fontSize: "13px", lineHeight: "1.5", whiteSpace: "pre-wrap" }}>
                      {c.body}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Activity Stream */}
          {activities.length > 0 && (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                <History size={15} className="text-secondary" />
                <h4 style={{ fontSize: "13px", fontWeight: 600 }}>Activity</h4>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {activities.slice(0, 5).map((act) => (
                  <div
                    key={act.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      fontSize: "12px",
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    <span style={{ fontWeight: 500, color: "var(--color-text)" }}>
                      {act.actor?.full_name ?? "System"}
                    </span>
                    <span>{act.action}</span>
                    <span style={{ marginLeft: "auto", color: "var(--color-text-tertiary)", fontSize: "11px" }}>
                      {new Date(act.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
