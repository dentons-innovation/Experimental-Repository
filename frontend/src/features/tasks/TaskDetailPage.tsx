import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, MessageSquare, History, Send } from "lucide-react";
import { tasksApi, commentsApi, workspacesApi } from "@/api/fetchers";
import { queryKeys } from "@/api/queryKeys";
import type { TaskPriority, TaskStatus } from "@/types";
import { TASK_STATUS_LABELS, TASK_PRIORITY_LABELS } from "@/types";
import {
  LoadingSpinner,
  ErrorMessage,
  LabelChip,
  Avatar,
} from "@/components/ui";

const ALL_STATUSES: TaskStatus[] = ["todo", "in_progress", "in_review", "done"];
const ALL_PRIORITIES: TaskPriority[] = ["low", "medium", "high", "critical"];

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
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
    enabled: !!taskId,
  });

  const { data: commentsData, isLoading: isCommentsLoading } = useQuery({
    queryKey: queryKeys.comments.byTask(taskId ?? ""),
    queryFn: () => commentsApi.list(taskId!),
    enabled: !!taskId,
  });

  const { data: activityData, isLoading: isActivityLoading } = useQuery({
    queryKey: queryKeys.tasks.activity(taskId ?? ""),
    queryFn: () => tasksApi.getActivity(taskId!),
    enabled: !!taskId,
  });

  const { data: members } = useQuery({
    queryKey: queryKeys.workspaces.members(task?.workspace_id ?? ""),
    queryFn: () => workspacesApi.listMembers(task!.workspace_id),
    enabled: !!task?.workspace_id,
  });

  const updateTaskMutation = useMutation({
    mutationFn: (payload: {
      status?: TaskStatus;
      priority?: TaskPriority;
      title?: string;
      description?: string;
      assignee_id?: string | null;
    }) => {
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
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.activity(taskId!),
      });
    },
    onError: (err: unknown) => {
      const axiosErr = err as {
        response?: { status?: number; data?: { detail?: string } };
      };
      if (axiosErr.response?.status === 409) {
        setOccError(
          "Conflict: This task was modified concurrently by another user or window. Please refresh the page.",
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

  if (isTaskLoading) return <LoadingSpinner fullPage />;
  if (taskError || !task) {
    return <ErrorMessage message="Failed to load task details" />;
  }

  const comments = commentsData?.items ?? [];
  const activities = activityData?.items ?? [];

  return (
    <div className="page-container" style={{ maxWidth: "1000px" }}>
      {/* Back button */}
      <div style={{ marginBottom: "16px" }}>
        <Link
          to={`/projects/${task.project_id}`}
          className="text-secondary"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "13px",
          }}
        >
          <ArrowLeft size={14} /> Back to Board
        </Link>
      </div>

      {occError && (
        <div className="error-state mb-4" style={{ padding: "12px 16px" }}>
          {occError}
        </div>
      )}

      {/* Main Grid: Content (Left) + Sidebar Attributes (Right) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 300px",
          gap: "24px",
        }}
      >
        {/* Left Column */}
        <div>
          <div className="card mb-6" style={{ padding: "24px" }}>
            <h1
              style={{ fontSize: "24px", fontWeight: 700, margin: "0 0 4px 0" }}
            >
              {task.title}
            </h1>
            <div
              style={{
                fontSize: "12px",
                color: "var(--color-text-secondary)",
                fontWeight: 500,
                marginBottom: "16px",
              }}
            >
              TASK-{task.id.slice(0, 4).toUpperCase()}
            </div>

            <div style={{ marginTop: "16px" }}>
              <div
                className="label"
                style={{
                  fontSize: "12px",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Description
              </div>
              <div
                style={{
                  backgroundColor: "var(--bg-surface)",
                  borderRadius: "var(--radius-md)",
                  padding: "16px",
                  fontSize: "14px",
                  lineHeight: "1.6",
                  color: task.description
                    ? "var(--text-primary)"
                    : "var(--text-muted)",
                  minHeight: "80px",
                  whiteSpace: "pre-wrap",
                }}
              >
                {task.description || "No description provided."}
              </div>
            </div>

            {task.labels && task.labels.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <div
                  className="label"
                  style={{
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Labels
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {task.labels.map((l) => (
                    <LabelChip key={l.id} name={l.name} color={l.color} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Comments Section */}
          <div className="card mb-6" style={{ padding: "24px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "16px",
              }}
            >
              <MessageSquare size={18} />
              <h2 style={{ fontSize: "16px", fontWeight: 600 }}>
                Comments ({comments.length})
              </h2>
            </div>

            {/* Comment input */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!commentText.trim()) return;
                addCommentMutation.mutate(commentText.trim());
              }}
              style={{ marginBottom: "20px" }}
            >
              {addCommentMutation.isError && (
                <div className="mb-2">
                  <ErrorMessage message="Failed to post comment. Please try again." />
                </div>
              )}
              <textarea
                className="input"
                rows={3}
                placeholder="Write a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
              />
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  marginTop: "8px",
                }}
              >
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={addCommentMutation.isPending || !commentText.trim()}
                >
                  <Send size={14} />
                  {addCommentMutation.isPending ? "Posting..." : "Comment"}
                </button>
              </div>
            </form>

            {/* Comment list */}
            {isCommentsLoading ? (
              <LoadingSpinner />
            ) : comments.length === 0 ? (
              <p className="text-secondary" style={{ fontSize: "13px" }}>
                No comments yet. Be the first to comment.
              </p>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                {comments.map((comment) => (
                  <div
                    key={comment.id}
                    style={{
                      padding: "12px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--bg-surface)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        marginBottom: "6px",
                      }}
                    >
                      <Avatar user={comment.author} size="sm" />
                      <span style={{ fontWeight: 600, fontSize: "13px" }}>
                        {comment.author.full_name}
                      </span>
                      <span
                        className="text-secondary"
                        style={{ fontSize: "11px", marginLeft: "auto" }}
                      >
                        {new Date(comment.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: "13px",
                        lineHeight: "1.5",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {comment.body}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Activity Section */}
          <div className="card" style={{ padding: "24px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "16px",
              }}
            >
              <History size={18} />
              <h2 style={{ fontSize: "16px", fontWeight: 600 }}>
                Activity History
              </h2>
            </div>

            {isActivityLoading ? (
              <LoadingSpinner />
            ) : activities.length === 0 ? (
              <p className="text-secondary" style={{ fontSize: "13px" }}>
                No activity recorded yet.
              </p>
            ) : (
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                {activities.map((act) => (
                  <div
                    key={act.id}
                    style={{
                      fontSize: "12px",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      color: "var(--text-secondary)",
                      padding: "4px 0",
                    }}
                  >
                    <span
                      style={{ fontWeight: 500, color: "var(--text-primary)" }}
                    >
                      {act.actor?.full_name ?? "System"}
                    </span>
                    <span>{act.action}</span>
                    <span
                      style={{
                        marginLeft: "auto",
                        color: "var(--text-muted)",
                        fontSize: "11px",
                      }}
                    >
                      {new Date(act.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar: Attributes */}
        <div>
          <div className="card" style={{ padding: "20px" }}>
            <h3
              style={{
                fontSize: "14px",
                fontWeight: 600,
                marginBottom: "16px",
              }}
            >
              Details
            </h3>

            {/* Status Control */}
            <div style={{ marginBottom: "16px" }}>
              <label className="label" htmlFor="detailStatus">
                Status
              </label>
              <select
                id="detailStatus"
                className="input"
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
              </select>
            </div>

            {/* Priority Control */}
            <div style={{ marginBottom: "16px" }}>
              <label className="label" htmlFor="detailPriority">
                Priority
              </label>
              <select
                id="detailPriority"
                className="input"
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
              </select>
            </div>

            {/* Assignee */}
            <div style={{ marginBottom: "16px" }}>
              <label className="input-label" htmlFor="detailAssignee">
                Assignee
              </label>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  marginTop: "4px",
                }}
              >
                <Avatar user={task.assignee} size="sm" />
                <select
                  id="detailAssignee"
                  className="input"
                  value={task.assignee?.id ?? task.assignee_id ?? ""}
                  disabled={updateTaskMutation.isPending}
                  onChange={(e) =>
                    updateTaskMutation.mutate({
                      assignee_id: e.target.value ? e.target.value : null,
                    })
                  }
                  style={{ flex: 1 }}
                >
                  <option value="">Unassigned</option>
                  {members?.map((m) => (
                    <option key={m.user.id} value={m.user.id}>
                      {m.user.full_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Reporter / Creator */}
            <div style={{ marginBottom: "16px" }}>
              <div className="label">Reporter</div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  marginTop: "4px",
                }}
              >
                <Avatar user={task.creator} size="sm" />
                <span style={{ fontSize: "13px" }}>
                  {task.creator?.full_name ?? "Unknown"}
                </span>
              </div>
            </div>

            {/* Concurrency Version */}
            <div
              style={{
                paddingTop: "12px",
                borderTop: "1px solid var(--border-subtle)",
                fontSize: "11px",
                color: "var(--text-muted)",
              }}
            >
              OCC Version: {task.version}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
