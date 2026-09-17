import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "@/contexts/WebSocketContext";
import { queryKeys } from "@/api/queryKeys";

export function useRealtimeInvalidation() {
  const queryClient = useQueryClient();
  const { subscribeToEvent } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribeToEvent((event) => {
      console.debug("Realtime event received:", event);

      const { channel, event: eventName, data } = event;

      // Handle workspace events
      if (channel.startsWith("workspace:")) {
        const workspaceId = channel.split(":")[1];

        switch (eventName) {
          case "workspace.updated":
            queryClient.invalidateQueries({
              queryKey: queryKeys.workspaces.detail(workspaceId),
            });
            queryClient.invalidateQueries({
              queryKey: queryKeys.workspaces.list(),
            });
            break;
          case "workspace.member_added":
          case "workspace.member_removed":
          case "workspace.member_updated":
            queryClient.invalidateQueries({
              queryKey: queryKeys.workspaces.members(workspaceId),
            });
            break;
        }
      }

      // Handle project events
      if (channel.startsWith("project:")) {
        const projectId = channel.split(":")[1];

        switch (eventName) {
          case "project.updated":
            queryClient.invalidateQueries({
              queryKey: queryKeys.projects.detail(projectId),
            });
            if (data?.workspace_id) {
              queryClient.invalidateQueries({
                queryKey: queryKeys.projects.list(data.workspace_id),
              });
            }
            break;
          case "project.member_added":
          case "project.member_removed":
          case "project.member_updated":
            queryClient.invalidateQueries({
              queryKey: queryKeys.projects.members(projectId),
            });
            break;
        }
      }

      // Handle task events
      if (channel.startsWith("project:")) {
        const projectId = channel.split(":")[1];
        if (eventName.startsWith("task.")) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.tasks.list(projectId),
          });
          if (data?.id) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.tasks.detail(data.id),
            });
          }
        }
      }

      // Handle comment events
      if (channel.startsWith("task:")) {
        const taskId = channel.split(":")[1];
        if (eventName.startsWith("comment.")) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.comments.byTask(taskId),
          });
        }
      }

      // Handle user events (connections)
      if (channel.startsWith("user:")) {
        if (eventName.startsWith("connection.")) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.connections.all(),
          });
        }

        if (
          eventName === "workspace.member_added" ||
          eventName === "workspace.member_removed"
        ) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.workspaces.list(),
          });
        }

        if (
          eventName === "project.member_added" ||
          eventName === "project.member_removed"
        ) {
          queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, [queryClient, subscribeToEvent]);
}
