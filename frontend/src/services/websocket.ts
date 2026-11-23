/**
 * Realtime WebSocket Manager for Blind Billion 2.0.
 */

import { RealtimeEventType, WebSocketEvent } from "../types/game";

export type EventHandler = (event: WebSocketEvent) => void;

export class GameWebSocketClient {
  private ws: WebSocket | null = null;
  private roomCode: string;
  private token: string;
  private handlers: Map<RealtimeEventType | "*", Set<EventHandler>> = new Map();
  private pingInterval: number | null = null;
  private reconnectTimeout: number | null = null;
  private isExplicitlyClosed = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 8;

  constructor(roomCode: string, token: string) {
    this.roomCode = roomCode.trim().toUpperCase();
    this.token = token;
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/rooms/${this.roomCode}?token=${encodeURIComponent(this.token)}`;

    try {
      this.ws = new WebSocket(url);
    } catch (err) {
      console.error("Failed to instantiate WebSocket:", err);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      if (event.data === "pong") {
        return;
      }
      try {
        const parsed: WebSocketEvent = JSON.parse(event.data);
        this.emit(parsed);
      } catch (err) {
        console.warn("Could not parse WS payload:", event.data, err);
      }
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      if (!this.isExplicitlyClosed) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (err) => {
      console.warn("WebSocket error:", err);
    };
  }

  public on(event: RealtimeEventType | "*", handler: EventHandler): () => void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);

    return () => {
      this.handlers.get(event)?.delete(handler);
    };
  }

  private emit(event: WebSocketEvent): void {
    // Specific handlers
    const specific = this.handlers.get(event.event);
    if (specific) {
      specific.forEach((h) => h(event));
    }
    // Wildcard handlers
    const wildcard = this.handlers.get("*");
    if (wildcard) {
      wildcard.forEach((h) => h(event));
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send("ping");
      }
    }, 25000);
  }

  private stopHeartbeat(): void {
    if (this.pingInterval !== null) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout !== null || this.isExplicitlyClosed) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn("Max reconnect attempts reached for WebSocket.");
      return;
    }

    const backoff = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 15000);
    this.reconnectAttempts += 1;

    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, backoff);
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimeout !== null) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
