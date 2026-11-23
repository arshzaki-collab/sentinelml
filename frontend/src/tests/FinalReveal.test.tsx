import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import confetti from "canvas-confetti";
import { FinalRevealScreen } from "../components/reveal/FinalRevealScreen";
import { LeaderboardEntry, PlayerGameStateView, RoomPublicView } from "../types/game";

const mockLeaderboard: LeaderboardEntry[] = [
  {
    player_id: "p1",
    display_name: "Alice",
    rank: 1,
    cash_balance: 450000000,
    squad_valuation: 750000000,
    final_net_worth: 1200000000,
    total_roi_pct: 35.5,
    squad_summary: [
      {
        slot_index: 1,
        position: "ST",
        player_name: "Kylian Mbappé",
        purchase_price_usd: 80000000,
        valuation_2026_usd: 180000000,
        roi_pct: 125.0,
      },
      {
        slot_index: 2,
        position: "WG",
        player_name: "Mohamed Salah",
        purchase_price_usd: 60000000,
        valuation_2026_usd: 110000000,
        roi_pct: 83.3,
      },
    ],
  },
  {
    player_id: "p2",
    display_name: "Bot (Pro)",
    rank: 2,
    cash_balance: 300000000,
    squad_valuation: 700000000,
    final_net_worth: 1000000000,
    total_roi_pct: 18.2,
    squad_summary: [],
  },
];

vi.mock("../context/GameContext", () => ({
  useGame: () => ({
    room: {
      room_code: "REV9",
      status: "COMPLETED",
      is_completed: true,
      current_year: 2026,
      current_phase: "COMPLETED",
      players: [
        { player_id: "p1", display_name: "Alice", is_host: true },
        { player_id: "p2", display_name: "Bot (Pro)", is_host: false },
      ],
    } as Partial<RoomPublicView>,
    myState: {
      player_id: "p1",
      cash_balance: 450000000,
      slots: [],
    } as Partial<PlayerGameStateView>,
    leaderboard: mockLeaderboard,
    playerId: "p1",
    leaveRoom: vi.fn(),
  }),
}));

describe("FinalRevealScreen Component", () => {
  it("triggers confetti celebration on reveal mount", () => {
    render(<FinalRevealScreen />);
    expect(confetti).toHaveBeenCalled();
  });

  it("unmasks real player identities and displays ROI performance", () => {
    render(<FinalRevealScreen />);

    expect(screen.getByText("Kylian Mbappé")).toBeInTheDocument();
    expect(screen.getByText("Mohamed Salah")).toBeInTheDocument();
    expect(screen.getByText("+125% ($100,000,000)")).toBeInTheDocument();
  });

  it("renders final tournament leaderboard with audited net worth", () => {
    render(<FinalRevealScreen />);

    expect(screen.getByText("CHAMPION OF EUROPE!")).toBeInTheDocument();
    expect(screen.getByText("RANK #1")).toBeInTheDocument();
    expect(screen.getByText("RANK #2")).toBeInTheDocument();
    expect(screen.getByText("$1,200,000,000")).toBeInTheDocument();
    expect(screen.getByText("$1,000,000,000")).toBeInTheDocument();
  });
});
