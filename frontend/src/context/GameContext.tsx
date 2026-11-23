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
  createRoom: (hostName: string, seed?: string) => Promise<void>;
  joinRoom: (roomCode: string, playerName: string) => Promise<void>;
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

  const clearSession = useCallback(() => {
    sessionStorage.removeItem("bb_session_token");
    sessionStorage.removeItem("bb_player_id");
    sessionStorage.removeItem("bb_room_code");
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

  const refreshState = useCallback(async () => {
    if (!roomCode || !sessionToken) return;
    try {
      const resp: RoomGameStateResponse = await api.getGameState(roomCode, sessionToken);
      setRoom(resp.room);
      setMyState(resp.my_state);
      if (resp.leaderboard) {
        setLeaderboard(resp.leaderboard);
      }
    } catch (err) {
      console.warn("Failed to refresh state:", err);
      if (err instanceof ApiError && (err.status === 401 || err.status === 404)) {
        clearSession();
      }
    }
  }, [roomCode, sessionToken, clearSession]);

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
    ws.connect();
    setIsConnected(true);

    const unsub = ws.on("*", (event: WebSocketEvent) => {
      switch (event.event) {
        case "PLAYER_JOINED":
        case "PLAYER_LEFT":
        case "PLAYER_READY":
        case "PLAYER_DISCONNECTED":
        case "PLAYER_RECONNECTED":
        case "HOST_MIGRATED":
          refreshState();
          break;

        case "GAME_STARTED":
          soundManager.playWhistle();
          refreshState();
          break;

        case "ACTION_COMMITTED":
          refreshState();
          break;

        case "ROUND_ADVANCED":
          soundManager.playWhistle();
          refreshState();
          break;

        case "GAME_FINISHED":
          soundManager.playFanfare();
          refreshState();
          break;

        default:
          break;
      }
    });

    return () => {
      unsub();
      ws.disconnect();
      setIsConnected(false);
    };
  }, [roomCode, sessionToken, refreshState]);

  // Initial restoration on page load
  useEffect(() => {
    if (roomCode && sessionToken && !myState) {
      refreshState();
    }
  }, [roomCode, sessionToken, myState, refreshState]);

  const createRoom = async (hostName: string, seed?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.createRoom(hostName, seed);
      soundManager.playClick();
      sessionStorage.setItem("bb_session_token", resp.session_token);
      sessionStorage.setItem("bb_player_id", resp.player_id);
      sessionStorage.setItem("bb_room_code", resp.room.room_code);
      setSessionToken(resp.session_token);
      setPlayerId(resp.player_id);
      setRoomCode(resp.room.room_code);
      setRoom(resp.room);
    } catch (err) {
      soundManager.playError();
      const msg = err instanceof ApiError ? err.message : "Failed to create room";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const joinRoom = async (code: string, playerName: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.joinRoom(code, playerName);
      soundManager.playClick();
      sessionStorage.setItem("bb_session_token", resp.session_token);
      sessionStorage.setItem("bb_player_id", resp.player_id);
      sessionStorage.setItem("bb_room_code", resp.room.room_code);
      setSessionToken(resp.session_token);
      setPlayerId(resp.player_id);
      setRoomCode(resp.room.room_code);
      setRoom(resp.room);
    } catch (err) {
      soundManager.playError();
      const msg = err instanceof ApiError ? err.message : "Failed to join room";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const toggleReady = async (isReady: boolean) => {
    if (!roomCode || !sessionToken) return;
    try {
      soundManager.playClick();
      const updated = await api.setReady(roomCode, sessionToken, isReady);
      setRoom(updated);
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Failed to update ready status");
    }
  };

  const addAI = async (difficulty: AIDifficulty) => {
    if (!roomCode || !sessionToken) return;
    try {
      soundManager.playClick();
      const updated = await api.addAIOpponent(roomCode, sessionToken, difficulty);
      setRoom(updated);
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Failed to add AI opponent");
    }
  };

  const removeAI = async (targetPlayerId: string) => {
    if (!roomCode || !sessionToken) return;
    try {
      soundManager.playClick();
      const updated = await api.removeAIOpponent(roomCode, sessionToken, targetPlayerId);
      setRoom(updated);
    } catch (err) {
      soundManager.playError();
      setError(err instanceof ApiError ? err.message : "Failed to remove AI opponent");
    }
  };

  const startGame = async () => {
    if (!roomCode || !sessionToken) return;
    setIsLoading(true);
    setError(null);
    try {
      soundManager.playWhistle();
      const resp = await api.startGame(roomCode, sessionToken);
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
    if (!roomCode || !sessionToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.submitAction(roomCode, sessionToken, action);
      if (action.action_type === "BUY" || action.action_type === "REPLACE") {
        soundManager.playPurchase();
      } else {
        soundManager.playClick();
      }
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
