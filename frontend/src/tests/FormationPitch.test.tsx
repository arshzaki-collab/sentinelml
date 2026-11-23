import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FormationPitch } from "../components/dashboard/FormationPitch";
import { PlayerGameStateView, RoomPublicView } from "../types/game";

// Mock useGame hook
vi.mock("../context/GameContext", () => ({
  useGame: () => ({
    room: {
      room_code: "TEST",
      status: "IN_GAME",
      current_year: 2018,
      current_phase: "BUYING_SEASON",
      current_slot_index: 3,
    } as Partial<RoomPublicView>,
    myState: {
      player_id: "p1",
      cash_balance: 920000000,
      filled_slots_count: 2,
      slots: [
        {
          slot_index: 1,
          position: "ST",
          buying_year: 2016,
          is_filled: true,
          purchase_price_usd: 50000000,
          current_valuation_usd: 55000000,
          assigned_candidate_token: "t1",
          is_revealed: false,
          revealed_player_name: null,
          revealed_player_id: null,
        },
        {
          slot_index: 2,
          position: "WG",
          buying_year: 2017,
          is_filled: true,
          purchase_price_usd: 30000000,
          current_valuation_usd: 32000000,
          assigned_candidate_token: "t2",
          is_revealed: false,
          revealed_player_name: null,
          revealed_player_id: null,
        },
        {
          slot_index: 3,
          position: "CM",
          buying_year: 2018,
          is_filled: false,
          purchase_price_usd: null,
          current_valuation_usd: null,
          assigned_candidate_token: null,
          is_revealed: false,
          revealed_player_name: null,
          revealed_player_id: null,
        },
        {
          slot_index: 4,
          position: "CB",
          buying_year: 2020,
          is_filled: false,
          purchase_price_usd: null,
          current_valuation_usd: null,
          assigned_candidate_token: null,
          is_revealed: false,
          revealed_player_name: null,
          revealed_player_id: null,
        },
        {
          slot_index: 5,
          position: "CM",
          buying_year: 2021,
          is_filled: false,
          purchase_price_usd: null,
          current_valuation_usd: null,
          assigned_candidate_token: null,
          is_revealed: false,
          revealed_player_name: null,
          revealed_player_id: null,
        },
        {
          slot_index: 6,
          position: "CB",
          buying_year: 2023,
          is_filled: false,
          purchase_price_usd: null,
          current_valuation_usd: null,
          assigned_candidate_token: null,
          is_revealed: false,
          revealed_player_name: null,
          revealed_player_id: null,
        },
        {
          slot_index: 7,
          position: "GK",
          buying_year: 2024,
          is_filled: false,
          purchase_price_usd: null,
          current_valuation_usd: null,
          assigned_candidate_token: null,
          is_revealed: false,
          revealed_player_name: null,
          revealed_player_id: null,
        },
      ],
    } as Partial<PlayerGameStateView>,
  }),
}));

describe("FormationPitch Component — 7 Tactical Slots", () => {
  it("renders all 7 tactical positions on the pitch", () => {
    render(<FormationPitch />);

    expect(screen.getAllByText("ST").length).toBeGreaterThan(0);
    expect(screen.getAllByText("WG").length).toBeGreaterThan(0);
    expect(screen.getAllByText("CM").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("CB").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("GK").length).toBeGreaterThan(0);
  });

  it("displays anonymous player labels for signed slots before reveal", () => {
    render(<FormationPitch />);

    expect(screen.getByText("Anonymous ST")).toBeInTheDocument();
    expect(screen.getByText("Anonymous WG")).toBeInTheDocument();
    expect(screen.getByText("Empty Slot 3")).toBeInTheDocument();
    expect(screen.getByText("Empty Slot 7")).toBeInTheDocument();
  });

  it("displays server purchase prices for filled slots", () => {
    render(<FormationPitch />);

    expect(screen.getByText("$50,000,000")).toBeInTheDocument();
    expect(screen.getByText("$30,000,000")).toBeInTheDocument();
  });
});
