/**
 * TanStack Query key factories.
 *
 * Centralizes all query key definitions to ensure:
 * - Consistent cache invalidation
 * - No string typos across the codebase
 * - Hierarchical invalidation (e.g., invalidate all tasks in a project)
 */

export const queryKeys = {
  users: {
    me: () => ["users", "me"] as const,
  },

  workspaces: {
    all: () => ["workspaces"] as const,
    list: (params?: { page?: number; pageSize?: number }) =>
      ["workspaces", "list", params] as const,
    detail: (id: string) => ["workspaces", id] as const,
    members: (id: string) => ["workspaces", id, "members"] as const,
  },

  projects: {
    all: () => ["projects"] as const,
    byWorkspace: (workspaceId: string) =>
      ["projects", "workspace", workspaceId] as const,
    list: (workspaceId: string, params?: object) =>
      ["projects", "workspace", workspaceId, "list", params] as const,
    detail: (id: string) => ["projects", id] as const,
    members: (id: string) => ["projects", id, "members"] as const,
  },

  tasks: {
    all: () => ["tasks"] as const,
    byProject: (projectId: string) =>
      ["tasks", "project", projectId] as const,
    list: (projectId: string, params?: object) =>
      ["tasks", "project", projectId, "list", params] as const,
    detail: (id: string) => ["tasks", id] as const,
    activity: (id: string) => ["tasks", id, "activity"] as const,
  },

  comments: {
    byTask: (taskId: string) => ["comments", "task", taskId] as const,
  },

  labels: {
    byWorkspace: (workspaceId: string) =>
      ["labels", "workspace", workspaceId] as const,
  },
} as const;
