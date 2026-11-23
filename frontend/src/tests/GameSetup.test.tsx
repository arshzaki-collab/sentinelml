import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { GameSetup } from "../components/setup/GameSetup";

const mockCreateRoom = vi.fn().mockResolvedValue(undefined);
const mockJoinRoom = vi.fn().mockResolvedValue(undefined);
const mockAddAI = vi.fn().mockResolvedValue(undefined);
const mockStartGame = vi.fn().mockResolvedValue(undefined);

vi.mock("../context/GameContext", () => ({
  useGame: () => ({
    createRoom: mockCreateRoom,
    joinRoom: mockJoinRoom,
    addAI: mockAddAI,
    startGame: mockStartGame,
    isLoading: false,
  }),
}));

describe("GameSetup Component", () => {
  it("renders single-player form with AI difficulty and count selectors", () => {
    render(<GameSetup initialMode="single" onBack={vi.fn()} />);

    expect(screen.getByText("YOUR MANAGER NAME")).toBeInTheDocument();
    expect(screen.getByText("ROOKIE")).toBeInTheDocument();
    expect(screen.getByText("PRO")).toBeInTheDocument();
    expect(screen.getByText("LEGEND")).toBeInTheDocument();
    expect(screen.getByText("START SINGLE-PLAYER MATCH")).toBeInTheDocument();
  });

  it("switches to multiplayer tab and allows room code input", () => {
    render(<GameSetup initialMode="single" onBack={vi.fn()} />);

    // Click Multiplayer tab
    fireEvent.click(screen.getByText("MULTIPLAYER (ONLINE)"));
    expect(screen.getByText("CREATE PRIVATE ROOM (LOBBY)")).toBeInTheDocument();

    // Click Join Existing Room sub-tab
    fireEvent.click(screen.getByText("JOIN EXISTING ROOM"));
    expect(screen.getByText("4-CHARACTER ROOM CODE")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. 7X9K")).toBeInTheDocument();
  });

  it("submits single-player setup with AI opponents", async () => {
    render(<GameSetup initialMode="single" onBack={vi.fn()} />);

    // Select Legend difficulty
    fireEvent.click(screen.getByText("LEGEND"));

    // Select 3 Bots
    fireEvent.click(screen.getByText("3 BOTS"));

    // Submit
    fireEvent.click(screen.getByText("START SINGLE-PLAYER MATCH"));

    expect(mockCreateRoom).toHaveBeenCalled();
  });
});
