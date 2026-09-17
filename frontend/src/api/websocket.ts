export interface RealtimeEvent {
  channel: string;
  event: string;
  data?: Record<string, unknown>;
}

type EventListener = (event: RealtimeEvent) => void;

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private token: string | null = null;
  private url: string;
  private listeners: Set<EventListener> = new Set();
  private reconnectTimeout: number | null = null;
  private isConnecting = false;
  private queuedCommands: Record<string, unknown>[] = [];

  constructor(url: string = "ws://localhost:8000/ws") {
    if (url.startsWith("/")) {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      this.url = `${protocol}//${window.location.host}${url}`;
    } else {
      this.url = url;
    }
  }

  public setToken(token: string | null) {
    this.token = token;
    if (token) {
      this.connect();
    } else {
      this.disconnect();
    }
  }

  public sendCommand(command: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(command));
    } else {
      this.queuedCommands.push(command);
    }
  }

  public connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }
    if (!this.token) {
      return;
    }

    this.isConnecting = true;
    const wsUrl = `${this.url}?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.isConnecting = false;
      if (this.reconnectTimeout) {
        window.clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
      }

      // Send queued commands
      while (this.queuedCommands.length > 0) {
        const cmd = this.queuedCommands.shift();
        this.ws?.send(JSON.stringify(cmd));
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Ignore internal system events like ping/pong or connection success
        if (data.type === "system" || data.type === "pong") {
          return;
        }

        // Ensure it looks like a RealtimeEvent
        if (data.channel && data.event) {
          this.notifyListeners(data as RealtimeEvent);
        }
      } catch (err) {
        console.error("Failed to parse websocket message:", err);
      }
    };

    this.ws.onclose = () => {
      this.isConnecting = false;
      this.ws = null;
      // Reconnect after 3 seconds if we still have a token
      if (this.token && !this.reconnectTimeout) {
        this.reconnectTimeout = window.setTimeout(() => this.connect(), 3000);
      }
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      this.ws?.close();
    };
  }

  public disconnect() {
    this.token = null;
    if (this.reconnectTimeout) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  public subscribe(listener: EventListener) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notifyListeners(event: RealtimeEvent) {
    this.listeners.forEach((listener) => listener(event));
  }
}

export const realtimeClient = new RealtimeClient("/ws");
