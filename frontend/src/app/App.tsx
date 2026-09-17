/**
 * Root application component.
 *
 * Wires together:
 * - AuthProvider for authentication
 * - QueryClientProvider for server state
 * - Router for navigation
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "@/features/auth/AuthContext";
import { WebSocketProvider } from "@/contexts/WebSocketContext";
import { router } from "./router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2, // 2 minutes
      retry: (failureCount, error) => {
        // Don't retry on 401/403/404
        const status = (error as { response?: { status?: number } })?.response
          ?.status;
        if (status === 401 || status === 403 || status === 404) return false;
        return failureCount < 2;
      },
    },
    mutations: {
      retry: false,
    },
  },
});

export function App() {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
          {import.meta.env.DEV && <ReactQueryDevtools />}
        </QueryClientProvider>
      </WebSocketProvider>
    </AuthProvider>
  );
}
