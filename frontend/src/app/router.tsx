/**
 * Application router.
 *
 * Route structure:
 *   /                       → redirect to /workspaces
 *   /sign-in                → Email/Password Sign-in & Register
 *   /workspaces             → workspace list (protected)
 *   /workspaces/:wid        → workspace detail + project list
 *   /projects/:pid          → project board
 *   /projects/:pid/tasks    → task list
 *   /tasks/:tid             → task detail
 */

import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedLayout } from "./ProtectedLayout";
import { WorkspacesPage } from "@/features/workspaces/WorkspacesPage";
import { WorkspaceDetailPage } from "@/features/workspaces/WorkspaceDetailPage";
import { ProjectBoardPage } from "@/features/projects/ProjectBoardPage";
import { TaskDetailPage } from "@/features/tasks/TaskDetailPage";
import { ConnectionsPage } from "@/features/connections/ConnectionsPage";
import { SignInPage } from "@/features/auth/SignInPage";

export const router = createBrowserRouter([
  {
    path: "/sign-in",
    element: <SignInPage />,
  },
  {
    path: "/",
    element: <ProtectedLayout />,
    children: [
      { index: true, element: <Navigate to="/workspaces" replace /> },
      { path: "workspaces", element: <WorkspacesPage /> },
      { path: "workspaces/:workspaceId", element: <WorkspaceDetailPage /> },
      { path: "projects/:projectId", element: <ProjectBoardPage /> },
      { path: "tasks/:taskId", element: <TaskDetailPage /> },
      { path: "connections", element: <ConnectionsPage /> },
    ],
  },
]);
