import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MultiplayerLobby } from "../components/lobby/MultiplayerLobby";
import { RoomPublicView } from "../types/game";

const mockToggleReady = vi.fn();
const mockAddAI = vi.fn();
const mockRemoveAI = vi.fn();
const mockStartGame = vi.fn();
const mockLeaveRoom = vi.fn();

const mockRoom: RoomPublicView = {
  room_code: "9K2X",
  status: "LOBBY",
  host_player_id: "host-1",
  current_year: 2016,
  current_phase: "BUYING_SEASON",
  current_slot_index: 1,
  timeline_step_index: 0,
  created_at: new Date().toISOString(),
  is_game_started: false,
  is_completed: false,
  players: [
    {
      player_id: "host-1",
      display_name: "Alice (Host)",
      is_host: true,
      is_ready: true,
      is_connected: true,
      is_turn_submitted: false,
      joined_at: new Date().toISOString(),
      is_ai: false,
      ai_difficulty: null,
    },
    {
      player_id: "p2",
      display_name: "Bob",
      is_host: false,
      is_ready: false,
      is_connected: true,
      is_turn_submitted: false,
      joined_at: new Date().toISOString(),
      is_ai: false,
      ai_difficulty: null,
    },
  ],
};

vi.mock("../context/GameContext", () => ({
  useGame: () => ({
    room: mockRoom,
    playerId: "host-1",
    roomCode: "9K2X",
    toggleReady: mockToggleReady,
    addAI: mockAddAI,
    removeAI: mockRemoveAI,
    startGame: mockStartGame,
    leaveRoom: mockLeaveRoom,
    isLoading: false,
  }),
}));

describe("MultiplayerLobby Component", () => {
  it("renders 4-character room code and participants list", () => {
    render(<MultiplayerLobby />);

    expect(screen.getByText("9K2X")).toBeInTheDocument();
    expect(screen.getByText("Alice (Host)")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText(/PARTICIPANTS \(2\/4 PLAYERS\)/i)).toBeInTheDocument();
  });

  it("identifies host and shows START TOURNAMENT button disabled when peer is unready", () => {
    render(<MultiplayerLobby />);

    expect(screen.getByText("HOST")).toBeInTheDocument();
    const startBtn = screen.getByText(/START TOURNAMENT/i);
    expect(startBtn).toBeDisabled(); // Bob is not ready!
  });

  it("allows host to add an AI opponent", () => {
    render(<MultiplayerLobby />);

    const addBotBtn = screen.getByText(/ADD BOT/i);
    fireEvent.click(addBotBtn);
    expect(mockAddAI).toHaveBeenCalledWith("PRO");
  });
});
