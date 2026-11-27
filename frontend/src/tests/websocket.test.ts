import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { GameWebSocketClient } from "../services/websocket";

describe("GameWebSocketClient", () => {
  let createdSockets: any[] = [];

  class MockWebSocket {
    url: string;
    readyState = 0;
    onopen: (() => void) | null = null;
    onmessage: ((ev: any) => void) | null = null;
    onclose: (() => void) | null = null;
    onerror: ((err: any) => void) | null = null;
    sent: string[] = [];

    constructor(url: string) {
      this.url = url;
      createdSockets.push(this);
      setTimeout(() => {
        this.readyState = 1;
        if (this.onopen) this.onopen();
      }, 0);
    }

    send(data: string) {
      this.sent.push(data);
    }

    close(code = 1000, reason = "") {
      this.readyState = 3;
      if (this.onclose) (this.onclose as any)({ code, reason });
    }
  }

  const originalWs = globalThis.WebSocket;

  beforeEach(() => {
    createdSockets = [];
    (globalThis as any).WebSocket = MockWebSocket;
    vi.useFakeTimers();
  });

  afterEach(() => {
    (globalThis as any).WebSocket = originalWs;
    vi.clearAllTimers();
    vi.restoreAllMocks();
  });

  it("constructs WebSocket with custom WS URL when provided", () => {
    const client = new GameWebSocketClient("ROOM1", "my-tok", "ws://backend.local:8000");
    client.connect();

    expect(createdSockets.length).toBe(1);
    expect(createdSockets[0].url).toBe("ws://backend.local:8000/ws/rooms/ROOM1?token=my-tok");

    client.disconnect();
  });

  it("dispatches incoming events to subscribed listeners", async () => {
    const client = new GameWebSocketClient("ROOM1", "my-tok", "ws://backend.local:8000");
    client.connect();

    const received: any[] = [];
    const unsub = client.on("PLAYER_JOINED", (ev) => {
      received.push(ev);
    });

    const mockEv = {
      event: "PLAYER_JOINED" as const,
      room_code: "ROOM1",
      timestamp: new Date().toISOString(),
      payload: { player_name: "Bob" },
    };

    createdSockets[0].onmessage({ data: JSON.stringify(mockEv) });

    expect(received.length).toBe(1);
    expect(received[0].payload.player_name).toBe("Bob");

    unsub();
    client.disconnect();
  });

  it("handles ping/pong heartbeat without emitting to listeners", () => {
    const client = new GameWebSocketClient("ROOM1", "my-tok", "ws://backend.local:8000");
    client.connect();

    const received: any[] = [];
    client.on("*", (ev) => received.push(ev));

    createdSockets[0].onmessage({ data: "pong" });
    expect(received.length).toBe(0);

    client.disconnect();
  });

  it("notifies connection status listeners on open and close", async () => {
    const client = new GameWebSocketClient("ROOM1", "my-tok", "ws://backend.local:8000");
    const statuses: boolean[] = [];
    const unsub = client.onConnectionStatus((s) => statuses.push(s));

    client.connect();
    expect(statuses).toEqual([]); // Not connected immediately

    // Trigger onopen
    createdSockets[0].onopen();
    expect(statuses).toEqual([true]);

    // Close socket
    createdSockets[0].close();
    expect(statuses).toEqual([true, false]);

    unsub();
    client.disconnect();
  });

  it("does not schedule reconnect when closed with policy violation (1008)", async () => {
    const client = new GameWebSocketClient("ROOM1", "bad-tok", "ws://backend.local:8000");
    client.connect();

    // Trigger onclose with code 1008
    createdSockets[0].onclose({ code: 1008 });

    // Advance time
    vi.advanceTimersByTime(30000);

    // No new socket should have been instantiated
    expect(createdSockets.length).toBe(1);

    client.disconnect();
  });
});
