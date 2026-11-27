/**
 * Central Game State Context for Blind Billion 2.0.
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import {
  ActionResponse,
  AIDifficulty,
  CreateRoomResponse,
  JoinRoomResponse,
  LeaderboardEntry,
  PlayerGameStateView,
  RoomGameStateResponse,
  RoomPublicView,
  WebSocketEvent,
} from "../types/game";
import { api, ApiError } from "../services/api";
import { GameWebSocketClient } from "../services/websocket";
import { soundManager } from "../services/sound";

interface GameContextType {
  room: RoomPublicView | null;
  myState: PlayerGameStateView | null;
  leaderboard: LeaderboardEntry[] | null;
  sessionToken: string | null;
  playerId: string | null;
  roomCode: string | null;
  isLoading: boolean;
  error: string | null;
  notification: string | null;
  isConnected: boolean;
  createRoom: (hostName: string, seed?: string) => Promise<CreateRoomResponse>;
  joinRoom: (roomCode: string, playerName: string) => Promise<JoinRoomResponse>;
  startSinglePlayer: (
    playerName: string,
    difficulty?: AIDifficulty,
    aiOpponentsCount?: number
  ) => Promise<void>;
  toggleReady: (isReady: boolean) => Promise<void>;
  addAI: (difficulty: AIDifficulty) => Promise<void>;
  removeAI: (targetPlayerId: string) => Promise<void>;
  startGame: () => Promise<void>;
  submitAction: (action: {
    action_type: "BUY" | "SELL" | "REPLACE" | "PASS";
    slot_index?: number;
    candidate_token?: string;
  }) => Promise<ActionResponse | void>;
  refreshState: () => Promise<void>;
  leaveRoom: () => void;
  dismissError: () => void;
  dismissNotification: () => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [room, setRoom] = useState<RoomPublicView | null>(null);
  const [myState, setMyState] = useState<PlayerGameStateView | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[] | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(() => {
    return sessionStorage.getItem("bb_session_token");
  });
  const [playerId, setPlayerId] = useState<string | null>(() => {
    return sessionStorage.getItem("bb_player_id");
  });
  const [roomCode, setRoomCode] = useState<string | null>(() => {
    return sessionStorage.getItem("bb_room_code");
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const wsClientRef = useRef<GameWebSocketClient | null>(null);
  const roomRef = useRef<RoomPublicView | null>(null);
  const sessionTokenRef = useRef<string | null>(sessionToken);
  const roomCodeRef = useRef<string | null>(roomCode);

  useEffect(() => {
    roomRef.current = room;
  }, [room]);

  useEffect(() => {
    sessionTokenRef.current = sessionToken;
  }, [sessionToken]);

  useEffect(() => {
    roomCodeRef.current = roomCode;
  }, [roomCode]);

  const clearSession = useCallback(() => {
    sessionStorage.removeItem("bb_session_token");
    sessionStorage.removeItem("bb_player_id");
    sessionStorage.removeItem("bb_room_code");
    sessionTokenRef.current = null;
    roomCodeRef.current = null;
    roomRef.current = null;
    setSessionToken(null);
    setPlayerId(null);
    setRoomCode(null);
    setRoom(null);
    setMyState(null);
    setLeaderboard(null);
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }
  }, []);

  const fetchRoom = useCallback(async (code: string): Promise<RoomPublicView> => {
    try {
      const publicRoom = await api.getRoom(code);
      setRoom(publicRoom);
      return publicRoom;
    } catch (err) {
      console.warn("Failed to fetch room:", err);
      if (err instanceof ApiError && err.status === 404) {
        // Room no longer exists on server
        clearSession();
      }
      throw err;
    }
  }, [clearSession]);

  const fetchGameState = useCallback(async (code: string, token: string): Promise<RoomGameStateResponse> => {
    try {
      const resp: RoomGameStateResponse = await api.getGameState(code, token);
      setRoom(resp.room);
      setMyState(resp.my_state);
      if (resp.leaderboard) {
        setLeaderboard(resp.leaderboard);
      }
      return resp;
    } catch (err) {
      console.warn("Failed to fetch game state:", err);
      if (err instanceof ApiError && err.status === 401) {
        // Confirmed invalid or expired session token
        clearSession();
      }
      // Note: 404 on game state (e.g. before start) does NOT clear the session!
      throw err;
    }
  }, [clearSession]);

  const refreshState = useCallback(async () => {
    if (!roomCode) return;
    try {
      let currentRoom = roomRef.current;
      if (!currentRoom) {
        currentRoom = await fetchRoom(roomCode);
      }

      if (currentRoom.status === "LOBBY") {
        // In LOBBY: refresh public room view only, never request private game state
        await fetchRoom(roomCode);
        return;
      }

      // In IN_GAME or COMPLETED: refresh authoritative player game state
      if (sessionToken) {
        await fetchGameState(roomCode, sessionToken);
      }
    } catch (err) {
      console.warn("Failed to refresh state:", err);
    }
  }, [roomCode, sessionToken, fetchRoom, fetchGameState]);

  // Connect WebSocket when roomCode and sessionToken are present
  useEffect(() => {
    if (!roomCode || !sessionToken) {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
      setIsConnected(false);
      return;
    }

    const ws = new GameWebSocketClient(roomCode, sessionToken);
    wsClientRef.current = ws;

    // Track connection state based strictly on real WebSocket lifecycle events
    const unsubStatus = ws.onConnectionStatus((connected) => {
      setIsConnected(connected);
    });

    ws.connect();

    const unsubEvents = ws.on("*", (event: WebSocketEvent) => {
      switch (event.event) {
        case "PLAYER_JOINED":
        case "PLAYER_LEFT":
        case "PLAYER_READY":
        case "PLAYER_DISCONNECTED":
        case "PLAYER_RECONNECTED":
        case "HOST_MIGRATED": {
          const payload = event.payload as Record<string, any> | undefined;
          const currentStatus = roomRef.current?.status;
          if (!currentStatus || currentStatus === "LOBBY") {
            if (payload?.room) {
              setRoom(payload.room);
            } else if (roomCode) {
              fetchRoom(roomCode).catch(() => {});
            }
          } else if (roomCode && sessionToken) {
            fetchGameState(roomCode, sessionToken).catch(() => {});
          }
          break;
        }

        case "GAME_STARTED": {
          soundManager.playWhistle();
          const payload = event.payload as Record<string, any> | undefined;
          if (payload?.room) {
            setRoom(payload.room);
          }
          if (roomCode && sessionToken) {
            fetchGameState(roomCode, sessionToken).catch(() => {});
          }
          break;
        }

        case "ACTION_COMMITTED": {
          if (roomCode && sessionToken) {
            fetchGameState(roomCode, sessionToken).catch(() => {});
          }
          break;
        }

        case "ROUND_ADVANCED": {
          soundManager.playWhistle();
          if (roomCode && sessionToken) {
            fetchGameState(roomCode, sessionToken).catch(() => {});
          }
          break;
        }

        case "GAME_FINISHED": {
          soundManager.playFanfare();
          if (roomCode && sessionToken) {
            fetchGameState(roomCode, sessionToken).catch(() => {});
          }
          break;
        }

        default:
          break;
      }
    });

    return () => {
      unsubEvents();
      unsubStatus();
      ws.disconnect();
      setIsConnected(false);
    };
  }, [roomCode, sessionToken, fetchRoom, fetchGameState]);

  // Initial restoration on page load
  useEffect(() => {
    if (roomCode && sessionToken && !roomRef.current) {
      fetchRoom(roomCode)
        .then((publicRoom) => {
          if (publicRoom.status !== "LOBBY") {
            return fetchGameState(roomCode, sessionToken);
          }
        })
        .catch((err) => {
          console.warn("Initial room restoration error:", err);
        });
    }
  }, [roomCode, sessionToken, fetchRoom, fetchGameState]);

  const createRoom = async (hostName: string, seed?: string): Promise<CreateRoomResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.createRoom(hostName, seed);
      soundManager.playClick();
      sessionStorage.setItem("bb_session_token", resp.session_token);
      sessionStorage.setItem("bb_player_id", resp.player_id);
      sessionStorage.setItem("bb_room_code", resp.room.room_code);
      sessionTokenRef.current = resp.session_token;
      roomCodeRef.current = resp.room.room_code;
      roomRef.current = resp.room;
      setSessionToken(resp.session_token);
      setPlayerId(resp.player_id);
      setRoomCode(resp.room.room_code);
      setRoom(resp.room);
      return resp;
    } catch (err) {
      soundManager.playError();
      const msg = err instanceof ApiError ? err.message : "Failed to create room";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const joinRoom = async (code: string, playerName: string): Promise<JoinRoomResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.joinRoom(code, playerName);
      soundManager.playClick();
      sessionStorage.setItem("bb_session_token", resp.session_token);
      sessionStorage.setItem("bb_player_id", resp.player_id);
      sessionStorage.setItem("bb_room_code", resp.room.room_code);
      sessionTokenRef.current = resp.session_token;
      roomCodeRef.current = resp.room.room_code;
      roomRef.current = resp.room;
      setSessionToken(resp.session_token);
      setPlayerId(resp.player_id);
      setRoomCode(resp.room.room_code);
      setRoom(resp.room);
      return resp;
    } catch (err) {
      soundManager.playError();
      const msg = err instanceof ApiError ? err.message : "Failed to join room";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const startSinglePlayer = async (
    playerName: string,
    difficulty: AIDifficulty = "PRO",
    aiOpponentsCount: number = 2
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      soundManager.playClick();
      // 1. Create Room
      const createResp = await api.createRoom(playerName.trim() || "Chief Scout");
      const code = createResp.room.room_code;
      const token = createResp.session_token;

      sessionStorage.setItem("bb_session_token", token);
      sessionStorage.setItem("bb_player_id", createResp.player_id);
      sessionStorage.setItem("bb_room_code", code);

      sessionTokenRef.current = token;
      roomCodeRef.current = code;
      roomRef.current = createResp.room;

      setSessionToken(token);
      setPlayerId(createResp.player_id);
      setRoomCode(code);
      setRoom(createResp.room);

      // 2. Add AI opponents sequentially using direct credentials
      let latestRoom = createResp.room;
      for (let i = 0; i < aiOpponentsCount; i++) {
        latestRoom = await api.addAIOpponent(code, token, difficulty);
        roomRef.current = latestRoom;
        setRoom(latestRoom);
      }

      // 3. Immediately start game
      soundManager.playWhistle();
      const startResp = await api.startGame(code, token);
      roomRef.current = startResp.room;
      setRoom(startResp.room);
      setMyState(startResp.my_state);
      if (startResp.leaderboard) {
        setLeaderboard(startResp.leaderboard);
      }
    } catch (err) {
      soundManager.playError();
      const msg = err instanceof ApiError ? err.message : "Failed to start single-player game";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const toggleReady = async (isReady: boolean) => {
    const code = roomCodeRef.current || roomCode;
    const token = sessionTokenRef.current || sessionToken;
    if (!code || !token) return;
    try {
      soundManager.playClick();
      const updated = await api.setReady(code, token, isReady);
      roomRef.current = updated;
      setRoom(updated);
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Failed to update ready status");
    }
  };

  const addAI = async (difficulty: AIDifficulty) => {
    const code = roomCodeRef.current || roomCode;
    const token = sessionTokenRef.current || sessionToken;
    if (!code || !token) return;
    try {
      soundManager.playClick();
      const updated = await api.addAIOpponent(code, token, difficulty);
      roomRef.current = updated;
      setRoom(updated);
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Failed to add AI opponent");
    }
  };

  const removeAI = async (targetPlayerId: string) => {
    const code = roomCodeRef.current || roomCode;
    const token = sessionTokenRef.current || sessionToken;
    if (!code || !token) return;
    try {
      soundManager.playClick();
      const updated = await api.removeAIOpponent(code, token, targetPlayerId);
      roomRef.current = updated;
      setRoom(updated);
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Failed to remove AI opponent");
    }
  };

  const startGame = async () => {
    const code = roomCodeRef.current || roomCode;
    const token = sessionTokenRef.current || sessionToken;
    if (!code || !token) return;
    setIsLoading(true);
    setError(null);
    try {
      soundManager.playWhistle();
      const resp = await api.startGame(code, token);
      roomRef.current = resp.room;
      setRoom(resp.room);
      setMyState(resp.my_state);
      if (resp.leaderboard) {
        setLeaderboard(resp.leaderboard);
      }
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Failed to start game");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const submitAction = async (action: {
    action_type: "BUY" | "SELL" | "REPLACE" | "PASS";
    slot_index?: number;
    candidate_token?: string;
  }) => {
    const code = roomCodeRef.current || roomCode;
    const token = sessionTokenRef.current || sessionToken;
    if (!code || !token) return;
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.submitAction(code, token, action);
      if (action.action_type === "BUY" || action.action_type === "REPLACE") {
        soundManager.playPurchase();
      } else {
        soundManager.playClick();
      }
      roomRef.current = resp.room;
      setRoom(resp.room);
      setMyState(resp.my_state);
      setNotification(resp.message);
      return resp;
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Action failed");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const leaveRoom = () => {
    soundManager.playClick();
    clearSession();
  };

  const dismissError = () => setError(null);
  const dismissNotification = () => setNotification(null);

  return (
    <GameContext.Provider
      value={{
        room,
        myState,
        leaderboard,
        sessionToken,
        playerId,
        roomCode,
        isLoading,
        error,
        notification,
        isConnected,
        createRoom,
        joinRoom,
        startSinglePlayer,
        toggleReady,
        addAI,
        removeAI,
        startGame,
        submitAction,
        refreshState,
        leaveRoom,
        dismissError,
        dismissNotification,
      }}
    >
      {children}
    </GameContext.Provider>
  );
};

export const useGame = (): GameContextType => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGame must be used within a GameProvider");
  }
  return context;
};
