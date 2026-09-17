import React, {
  createContext,
  useContext,
  useEffect,
  useCallback,
} from "react";
import { useAuth } from "@/features/auth/AuthContext";
import { realtimeClient, RealtimeEvent } from "@/api/websocket";
import { authApi } from "@/api/fetchers";

interface WebSocketContextValue {
  subscribeToEvent: (listener: (event: RealtimeEvent) => void) => () => void;
  joinChannel: (channel: string) => void;
  leaveChannel: (channel: string) => void;
}

const WebSocketContext = createContext<WebSocketContextValue | undefined>(
  undefined,
);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { token, isAuthenticated } = useAuth();

  useEffect(() => {
    realtimeClient.setTicketFetcher(() => authApi.getWsTicket());
  }, []);

  useEffect(() => {
    if (isAuthenticated && token) {
      realtimeClient.setToken(token);
    } else {
      realtimeClient.disconnect();
    }

    return () => {
      // Disconnect on unmount
      realtimeClient.disconnect();
    };
  }, [isAuthenticated, token]);

  const joinChannel = useCallback((channel: string) => {
    realtimeClient.joinChannel(channel);
  }, []);

  const leaveChannel = useCallback((channel: string) => {
    realtimeClient.leaveChannel(channel);
  }, []);

  const subscribeToEvent = useCallback(
    (listener: (event: RealtimeEvent) => void) => {
      return realtimeClient.subscribe(listener);
    },
    [],
  );

  const value = {
    joinChannel,
    leaveChannel,
    subscribeToEvent,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return context;
}
