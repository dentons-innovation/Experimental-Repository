/**
 * Domain types for the frontend.
 *
 * These mirror the backend domain enums and Pydantic schemas.
 * Keeping them in sync is a manual process for now;
 * future work item: generate from OpenAPI spec.
 */

// ─────────────────────────────────────────────────────────────
// Enums
// ─────────────────────────────────────────────────────────────

export const TaskStatus = {
  BACKLOG: "backlog",
  TODO: "todo",
  IN_PROGRESS: "in_progress",
  IN_REVIEW: "in_review",
  DONE: "done",
} as const;
export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];

export const TaskPriority = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
} as const;
export type TaskPriority = (typeof TaskPriority)[keyof typeof TaskPriority];

export const WorkspaceRole = {
  OWNER: "owner",
  MEMBER: "member",
} as const;
export type WorkspaceRole = (typeof WorkspaceRole)[keyof typeof WorkspaceRole];

export const ProjectRole = {
  ADMIN: "admin",
  MEMBER: "member",
} as const;
export type ProjectRole = (typeof ProjectRole)[keyof typeof ProjectRole];

export const ActivityAction = {
  TASK_CREATED: "task_created",
  TASK_UPDATED: "task_updated",
  STATUS_CHANGED: "status_changed",
  PRIORITY_CHANGED: "priority_changed",
  ASSIGNED: "assigned",
  UNASSIGNED: "unassigned",
  LABEL_ADDED: "label_added",
  LABEL_REMOVED: "label_removed",
  DUE_DATE_SET: "due_date_set",
  DUE_DATE_CLEARED: "due_date_cleared",
  COMMENT_ADDED: "comment_added",
  COMMENT_EDITED: "comment_edited",
  COMMENT_DELETED: "comment_deleted",
  TITLE_CHANGED: "title_changed",
  DESCRIPTION_CHANGED: "description_changed",
} as const;
export type ActivityAction =
  (typeof ActivityAction)[keyof typeof ActivityAction];

// ─────────────────────────────────────────────────────────────
// Entity types
// ─────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  avatar_url: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  username: string;
  full_name: string;
  password: string;
  avatar_url?: string | null;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user: User;
  role: WorkspaceRole;
  created_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user: User;
  role: ProjectRole;
  created_at: string;
}

export interface Label {
  id: string;
  workspace_id: string;
  name: string;
  color: string;
}

export interface Task {
  id: string;
  project_id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assignee: User | null;
  creator: User;
  labels: Label[];
  due_date: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Comment {
  id: string;
  task_id: string;
  author: User;
  body: string;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

export interface ActivityLog {
  id: string;
  task_id: string;
  actor: User;
  action: ActivityAction;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────
// API pagination
// ─────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ─────────────────────────────────────────────────────────────
// API error
// ─────────────────────────────────────────────────────────────

export interface ApiError {
  error: {
    code: string;
    message: string;
    field?: string;
  };
}

// ─────────────────────────────────────────────────────────────
// UI helpers
// ─────────────────────────────────────────────────────────────

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  backlog: "Backlog",
  todo: "To Do",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
};

export const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const TASK_STATUS_ORDER: TaskStatus[] = [
  "backlog",
  "todo",
  "in_progress",
  "in_review",
  "done",
];
