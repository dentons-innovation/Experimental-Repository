/**
 * Shared UI components: Badge, TaskStatusBadge, TaskPriorityBadge, Avatar
 */

import type { TaskPriority, TaskStatus, User } from "@/types";
import {
  TASK_PRIORITY_LABELS,
  TASK_STATUS_LABELS,
} from "@/types";

// ─────────────────────────────────────────────────────────────
// Status Badge
// ─────────────────────────────────────────────────────────────

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span className={`badge badge-status-${status}`}>
      {TASK_STATUS_LABELS[status]}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────
// Priority Badge
// ─────────────────────────────────────────────────────────────

const PRIORITY_ICONS: Record<TaskPriority, string> = {
  low: "↓",
  medium: "→",
  high: "↑",
  critical: "⚡",
};

export function TaskPriorityBadge({ priority }: { priority: TaskPriority }) {
  return (
    <span className={`badge badge-priority-${priority}`}>
      {PRIORITY_ICONS[priority]} {TASK_PRIORITY_LABELS[priority]}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────
// Avatar
// ─────────────────────────────────────────────────────────────

interface AvatarProps {
  user: User | null;
  size?: "sm" | "md" | "lg";
}

export function Avatar({ user, size = "md" }: AvatarProps) {
  const sizeClass = size === "sm" ? "avatar-sm" : size === "lg" ? "avatar-lg" : "";

  if (!user) {
    return <div className={`avatar ${sizeClass}`}>?</div>;
  }

  if (user.avatar_url) {
    return (
      <img
        className={`avatar ${sizeClass}`}
        src={user.avatar_url}
        alt={user.full_name}
      />
    );
  }

  const initials = user.full_name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className={`avatar ${sizeClass}`} title={user.full_name}>
      {initials}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Label chip
// ─────────────────────────────────────────────────────────────

export function LabelChip({ name, color }: { name: string; color: string }) {
  return (
    <span
      className="task-label"
      style={{
        backgroundColor: `${color}22`,
        color: color,
        border: `1px solid ${color}44`,
      }}
    >
      {name}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────
// Loading / Error / Empty states
// ─────────────────────────────────────────────────────────────

export function LoadingSpinner({ fullPage = false }: { fullPage?: boolean }) {
  if (fullPage) {
    return (
      <div className="loading-center" style={{ minHeight: "60vh" }}>
        <div className="spinner" style={{ width: 36, height: 36 }} />
      </div>
    );
  }
  return (
    <div className="loading-center">
      <div className="spinner" />
    </div>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  return <div className="error-state">{message}</div>;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <div style={{ fontSize: 40 }}>📋</div>
      <div className="empty-state-title">{title}</div>
      {description && (
        <div className="empty-state-description">{description}</div>
      )}
      {action}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Modal & Form Primitives
// ─────────────────────────────────────────────────────────────
export { Modal, ModalHeader, ModalBody, ModalFooter } from "./Modal";
export type { ModalProps } from "./Modal";
export { FormField, Input, Textarea, Select } from "./FormField";
export type { FormFieldProps, InputProps, TextareaProps, SelectProps } from "./FormField";

