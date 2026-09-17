/**
 * API fetcher functions for all resources.
 *
 * Each fetcher maps to one backend endpoint.
 * They are pure async functions used by TanStack Query hooks.
 */

import { apiClient } from "./client";
import type {
  AuthResponse,
  Comment,
  Label,
  LoginCredentials,
  PaginatedResponse,
  Project,
  ProjectMember,
  RegisterCredentials,
  Task,
  TaskPriority,
  TaskStatus,
  User,
  UserConnection,
  Workspace,
  WorkspaceMember,
} from "@/types";

// ─────────────────────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────────────────────

export const authApi = {
  login: (payload: LoginCredentials): Promise<AuthResponse> =>
    apiClient.post("/auth/login", payload).then((r) => r.data),

  register: (payload: RegisterCredentials): Promise<AuthResponse> =>
    apiClient.post("/auth/register", payload).then((r) => r.data),

  me: (): Promise<User> => apiClient.get("/auth/me").then((r) => r.data),

  getWsTicket: (): Promise<string> =>
    apiClient.post("/auth/ws-ticket").then((r) => r.data.ticket),
};

// ─────────────────────────────────────────────────────────────
// Users
// ─────────────────────────────────────────────────────────────

export const usersApi = {
  me: (): Promise<User> => apiClient.get("/users/me").then((r) => r.data),
};

// ─────────────────────────────────────────────────────────────
// Connections
// ─────────────────────────────────────────────────────────────

export const connectionsApi = {
  searchUsers: (query: string): Promise<PaginatedResponse<User>> =>
    apiClient
      .get("/connections/users/search", { params: { q: query } })
      .then((r) => r.data),

  list: (params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<UserConnection>> =>
    apiClient.get("/connections", { params }).then((r) => r.data),

  listPendingIncoming: (params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<UserConnection>> =>
    apiClient
      .get("/connections/pending/incoming", { params })
      .then((r) => r.data),

  listPendingOutgoing: (params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<UserConnection>> =>
    apiClient
      .get("/connections/pending/outgoing", { params })
      .then((r) => r.data),

  sendRequest: (receiverId: string): Promise<UserConnection> =>
    apiClient
      .post("/connections", { receiver_id: receiverId })
      .then((r) => r.data),

  accept: (connectionId: string): Promise<UserConnection> =>
    apiClient.post(`/connections/${connectionId}/accept`).then((r) => r.data),

  reject: (connectionId: string): Promise<void> =>
    apiClient.post(`/connections/${connectionId}/reject`).then((r) => r.data),

  remove: (connectionId: string): Promise<void> =>
    apiClient.delete(`/connections/${connectionId}`).then((r) => r.data),
};

// ─────────────────────────────────────────────────────────────
// Workspaces
// ─────────────────────────────────────────────────────────────

export interface WorkspaceListParams {
  page?: number;
  page_size?: number;
}

export const workspacesApi = {
  list: (params?: WorkspaceListParams): Promise<PaginatedResponse<Workspace>> =>
    apiClient.get("/workspaces", { params }).then((r) => r.data),

  get: (id: string): Promise<Workspace> =>
    apiClient.get(`/workspaces/${id}`).then((r) => r.data),

  create: (payload: {
    name: string;
    description?: string;
    slug?: string;
  }): Promise<Workspace> =>
    apiClient.post("/workspaces", payload).then((r) => r.data),

  update: (
    id: string,
    payload: { name?: string; description?: string | null },
  ): Promise<Workspace> =>
    apiClient.patch(`/workspaces/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/workspaces/${id}`).then(() => undefined),

  listMembers: (id: string): Promise<WorkspaceMember[]> =>
    apiClient.get(`/workspaces/${id}/members`).then((r) => r.data),

  addMember: (
    id: string,
    payload: { user_id: string; role: string },
  ): Promise<WorkspaceMember> =>
    apiClient.post(`/workspaces/${id}/members`, payload).then((r) => r.data),

  removeMember: (workspaceId: string, userId: string): Promise<void> =>
    apiClient
      .delete(`/workspaces/${workspaceId}/members/${userId}`)
      .then(() => undefined),

  updateMemberRole: (
    workspaceId: string,
    userId: string,
    payload: { role: string },
  ): Promise<WorkspaceMember> =>
    apiClient
      .put(`/workspaces/${workspaceId}/members/${userId}`, payload)
      .then((r) => r.data),
};

// ─────────────────────────────────────────────────────────────
// Projects
// ─────────────────────────────────────────────────────────────

export const projectsApi = {
  list: (
    workspaceId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<PaginatedResponse<Project>> =>
    apiClient
      .get(`/workspaces/${workspaceId}/projects`, { params })
      .then((r) => r.data),

  get: (id: string): Promise<Project> =>
    apiClient.get(`/projects/${id}`).then((r) => r.data),

  create: (
    workspaceId: string,
    payload: { name: string; description?: string; slug?: string },
  ): Promise<Project> =>
    apiClient
      .post(`/workspaces/${workspaceId}/projects`, payload)
      .then((r) => r.data),

  update: (
    id: string,
    payload: { name?: string; description?: string | null },
  ): Promise<Project> =>
    apiClient.patch(`/projects/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/projects/${id}`).then(() => undefined),

  listMembers: (id: string): Promise<ProjectMember[]> =>
    apiClient.get(`/projects/${id}/members`).then((r) => r.data),

  addMember: (
    id: string,
    payload: { user_id: string; role: string },
  ): Promise<ProjectMember> =>
    apiClient.post(`/projects/${id}/members`, payload).then((r) => r.data),

  removeMember: (projectId: string, userId: string): Promise<void> =>
    apiClient
      .delete(`/projects/${projectId}/members/${userId}`)
      .then(() => undefined),

  updateMemberRole: (
    projectId: string,
    userId: string,
    payload: { role: string },
  ): Promise<ProjectMember> =>
    apiClient
      .put(`/projects/${projectId}/members/${userId}`, payload)
      .then((r) => r.data),
};

// ─────────────────────────────────────────────────────────────
// Tasks
// ─────────────────────────────────────────────────────────────

export interface TaskListParams {
  page?: number;
  page_size?: number;
  status?: TaskStatus[];
  priority?: TaskPriority[];
  assignee_id?: string;
  label_ids?: string[];
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export const tasksApi = {
  list: (
    projectId: string,
    params?: TaskListParams,
  ): Promise<PaginatedResponse<Task>> =>
    apiClient
      .get(`/projects/${projectId}/tasks`, { params })
      .then((r) => r.data),

  get: (id: string): Promise<Task> =>
    apiClient.get(`/tasks/${id}`).then((r) => r.data),

  create: (
    projectId: string,
    payload: {
      title: string;
      description?: string;
      status?: TaskStatus;
      priority?: TaskPriority;
      assignee_id?: string;
      due_date?: string;
      label_ids?: string[];
    },
  ): Promise<Task> =>
    apiClient.post(`/projects/${projectId}/tasks`, payload).then((r) => r.data),

  update: (
    id: string,
    payload: {
      version: number;
      title?: string;
      description?: string;
      status?: TaskStatus;
      priority?: TaskPriority;
      assignee_id?: string | null;
      due_date?: string | null;
    },
  ): Promise<Task> =>
    apiClient.patch(`/tasks/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/tasks/${id}`).then(() => undefined),

  addLabel: (taskId: string, labelId: string): Promise<Task> =>
    apiClient
      .post(`/tasks/${taskId}/labels`, { label_id: labelId })
      .then((r) => r.data),

  removeLabel: (taskId: string, labelId: string): Promise<Task> =>
    apiClient.delete(`/tasks/${taskId}/labels/${labelId}`).then((r) => r.data),

  getActivity: (
    taskId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<PaginatedResponse<import("@/types").ActivityLog>> =>
    apiClient.get(`/tasks/${taskId}/activity`, { params }).then((r) => r.data),
};

// ─────────────────────────────────────────────────────────────
// Comments
// ─────────────────────────────────────────────────────────────

export const commentsApi = {
  list: (
    taskId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<PaginatedResponse<Comment>> =>
    apiClient.get(`/tasks/${taskId}/comments`, { params }).then((r) => r.data),

  create: (taskId: string, body: string): Promise<Comment> =>
    apiClient.post(`/tasks/${taskId}/comments`, { body }).then((r) => r.data),

  update: (commentId: string, body: string): Promise<Comment> =>
    apiClient.patch(`/comments/${commentId}`, { body }).then((r) => r.data),

  delete: (commentId: string): Promise<void> =>
    apiClient.delete(`/comments/${commentId}`).then(() => undefined),
};

// ─────────────────────────────────────────────────────────────
// Labels
// ─────────────────────────────────────────────────────────────

export const labelsApi = {
  list: (workspaceId: string): Promise<Label[]> =>
    apiClient.get(`/workspaces/${workspaceId}/labels`).then((r) => r.data),

  create: (
    workspaceId: string,
    payload: { name: string; color?: string },
  ): Promise<Label> =>
    apiClient
      .post(`/workspaces/${workspaceId}/labels`, payload)
      .then((r) => r.data),

  update: (
    id: string,
    payload: { name?: string; color?: string },
  ): Promise<Label> =>
    apiClient.patch(`/labels/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/labels/${id}`).then(() => undefined),
};
