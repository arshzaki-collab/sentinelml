/**
 * HTTP Client for Blind Billion 2.0 Backend APIs.
 */

import {
  ActionResponse,
  CreateRoomResponse,
  JoinRoomResponse,
  RoomGameStateResponse,
  RoomPublicView,
  AIDifficulty,
} from "../types/game";

const API_BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errMsg = `Request failed (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errMsg = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new ApiError(errMsg, res.status);
  }

  return res.json() as Promise<T>;
}

export const api = {
  async createRoom(hostName: string, roomSeed?: string): Promise<CreateRoomResponse> {
    return request<CreateRoomResponse>("/rooms", {
      method: "POST",
      body: JSON.stringify({
        host_name: hostName,
        room_seed: roomSeed || null,
      }),
    });
  },

  async joinRoom(roomCode: string, playerName: string): Promise<JoinRoomResponse> {
    const code = roomCode.trim().toUpperCase();
    return request<JoinRoomResponse>(`/rooms/${code}/join`, {
      method: "POST",
      body: JSON.stringify({ player_name: playerName }),
    });
  },

  async getRoom(roomCode: string): Promise<RoomPublicView> {
    const code = roomCode.trim().toUpperCase();
    return request<RoomPublicView>(`/rooms/${code}`);
  },

  async setReady(roomCode: string, token: string, isReady: boolean): Promise<RoomPublicView> {
    const code = roomCode.trim().toUpperCase();
    return request<RoomPublicView>(`/rooms/${code}/ready`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ is_ready: isReady }),
    });
  },

  async addAIOpponent(
    roomCode: string,
    token: string,
    difficulty: AIDifficulty = "PRO"
  ): Promise<RoomPublicView> {
    const code = roomCode.trim().toUpperCase();
    return request<RoomPublicView>(`/rooms/${code}/ai`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ difficulty }),
    });
  },

  async removeAIOpponent(
    roomCode: string,
    token: string,
    playerId: string
  ): Promise<RoomPublicView> {
    const code = roomCode.trim().toUpperCase();
    return request<RoomPublicView>(`/rooms/${code}/ai/${playerId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  async startGame(roomCode: string, token: string): Promise<RoomGameStateResponse> {
    const code = roomCode.trim().toUpperCase();
    return request<RoomGameStateResponse>(`/rooms/${code}/start`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  async getGameState(roomCode: string, token: string): Promise<RoomGameStateResponse> {
    const code = roomCode.trim().toUpperCase();
    return request<RoomGameStateResponse>(`/rooms/${code}/state`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  async submitAction(
    roomCode: string,
    token: string,
    action: {
      action_type: "BUY" | "SELL" | "REPLACE" | "PASS";
      slot_index?: number;
      candidate_token?: string;
    }
  ): Promise<ActionResponse> {
    const code = roomCode.trim().toUpperCase();
    const idempotencyKey =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `idemp_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    return request<ActionResponse>(`/rooms/${code}/action`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        action_type: action.action_type,
        slot_index: action.slot_index ?? null,
        candidate_token: action.candidate_token ?? null,
        idempotency_key: idempotencyKey,
      }),
    });
  },
};
