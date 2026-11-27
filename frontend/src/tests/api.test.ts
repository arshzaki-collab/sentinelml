import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "../services/api";

describe("Frontend API Client Service", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("createRoom sends correct POST request and payload", async () => {
    const mockResponse = {
      room: { room_code: "9K2X" },
      session_token: "tok-123",
      player_id: "p1",
    };

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const resp = await api.createRoom("Alice", "SEED1");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/rooms",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ host_name: "Alice", room_seed: "SEED1" }),
      })
    );
    expect(resp.session_token).toBe("tok-123");
  });

  it("joinRoom normalizes room code to uppercase", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_token: "tok-456" }),
    });

    await api.joinRoom("abcd", "Bob");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/rooms/ABCD/join",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ player_name: "Bob" }),
      })
    );
  });

  it("submitAction generates client idempotency key and headers", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        message: "Signed",
        new_balance: 950000000,
      }),
    });

    const res = await api.submitAction("ABCD", "my-token", {
      action_type: "BUY",
      candidate_token: "cand-token",
    });

    expect(res.success).toBe(true);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/rooms/ABCD/action",
      expect.objectContaining({
        method: "POST",
        headers: expect.any(Headers),
      })
    );
  });

  it("throws ApiError with error detail on HTTP failure", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Turn already submitted for this round." }),
    });

    await expect(api.submitAction("ABCD", "token", { action_type: "PASS" })).rejects.toThrow(
      "Turn already submitted for this round."
    );
  });

  it("wraps fetch network errors in user-friendly ApiError", async () => {
    (globalThis.fetch as any).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(api.getRoom("ABCD")).rejects.toThrow(
      /Unable to connect to game server/
    );
  });

  it("getRoom sends GET request with normalized code", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ room_code: "ABCD", status: "LOBBY" }),
    });

    const room = await api.getRoom("abcd");
    expect(room.room_code).toBe("ABCD");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/rooms/ABCD",
      expect.objectContaining({ headers: expect.any(Headers) })
    );
  });

  it("getGameState sends GET request with Authorization header", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        room: { room_code: "ABCD", status: "IN_GAME" },
        my_state: { cash_balance: 1000000000 },
      }),
    });

    const state = await api.getGameState("abcd", "tok-secret");
    expect(state.room.status).toBe("IN_GAME");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/rooms/ABCD/state",
      expect.objectContaining({
        method: "GET",
        headers: expect.any(Headers),
      })
    );
  });
});

