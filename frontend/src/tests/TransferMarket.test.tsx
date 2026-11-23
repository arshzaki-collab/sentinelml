import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TransferMarket } from "../components/transfer/TransferMarket";
import { PlayerGameStateView, RoomPublicView } from "../types/game";

const mockSubmitAction = vi.fn().mockResolvedValue({ success: true });

const mockRoom: RoomPublicView = {
  room_code: "TR01",
  status: "IN_GAME",
  host_player_id: "p1",
  current_year: 2019,
  current_phase: "TRANSFER_WINDOW",
  current_slot_index: null,
  timeline_step_index: 3,
  created_at: new Date().toISOString(),
  is_game_started: true,
  is_completed: false,
  players: [
    {
      player_id: "p1",
      display_name: "Manager Alice",
      is_host: true,
      is_ready: true,
      is_connected: true,
      is_turn_submitted: false,
      joined_at: new Date().toISOString(),
    },
  ],
};

const mockMyState: PlayerGameStateView = {
  player_id: "p1",
  display_name: "Manager Alice",
  cash_balance: 850000000,
  current_year: 2019,
  current_phase: "TRANSFER_WINDOW",
  active_slot_index: null,
  timeline_step_index: 3,
  filled_slots_count: 3,
  is_completed: false,
  final_net_worth: null,
  final_squad_value: null,
  slots: [
    {
      slot_index: 1,
      position: "ST",
      buying_year: 2016,
      is_filled: true,
      purchase_price_usd: 50000000,
      current_valuation_usd: 65000000,
      assigned_candidate_token: "cand-st-1",
      is_revealed: false,
      revealed_player_name: null,
      revealed_player_id: null,
    },
    {
      slot_index: 2,
      position: "WG",
      buying_year: 2017,
      is_filled: true,
      purchase_price_usd: 40000000,
      current_valuation_usd: 48000000,
      assigned_candidate_token: "cand-wg-1",
      is_revealed: false,
      revealed_player_name: null,
      revealed_player_id: null,
    },
    {
      slot_index: 3,
      position: "CM",
      buying_year: 2018,
      is_filled: true,
      purchase_price_usd: 60000000,
      current_valuation_usd: 55000000,
      assigned_candidate_token: "cand-cm-1",
      is_revealed: false,
      revealed_player_name: null,
      revealed_player_id: null,
    },
  ],
  shortlists: {
    "1": {
      slot_index: 1,
      required_position: "ST",
      buying_year: 2016,
      candidates: [
        {
          candidate_token: "cand-st-1", // currently owned
          cost_usd: 50000000,
          position: "ST",
          hints: [
            { label: "Goals", value: 25, icon_key: "goals" },
            { label: "Assists", value: 8, icon_key: "assists" },
            { label: "Age", value: 26, icon_key: "age" },
          ],
        },
        {
          candidate_token: "cand-st-2", // replacement candidate
          cost_usd: 55000000,
          position: "ST",
          hints: [
            { label: "Goals", value: 31, icon_key: "goals" },
            { label: "Assists", value: 4, icon_key: "assists" },
            { label: "Age", value: 24, icon_key: "age" },
          ],
        },
      ],
    },
  },
  transaction_history: [],
};

vi.mock("../context/GameContext", () => ({
  useGame: () => ({
    room: mockRoom,
    myState: mockMyState,
    playerId: "p1",
    submitAction: mockSubmitAction,
    isLoading: false,
  }),
}));

describe("TransferMarket Component", () => {
  it("renders 2019 transfer window header and PASS button", () => {
    render(<TransferMarket />);

    expect(screen.getByText("TRANSFER WINDOW 2019")).toBeInTheDocument();
    expect(screen.getByText("PASS (KEEP SQUAD)")).toBeInTheDocument();
  });

  it("allows player to PASS transfer window", () => {
    render(<TransferMarket />);

    fireEvent.click(screen.getByText("PASS (KEEP SQUAD)"));
    expect(mockSubmitAction).toHaveBeenCalledWith({ action_type: "PASS" });
  });

  it("lists eligible owned slots and shows replacement options on click", () => {
    render(<TransferMarket />);

    expect(screen.getByText("Slot 1 (ST)")).toBeInTheDocument();
    expect(screen.getByText("Slot 2 (WG)")).toBeInTheDocument();
    expect(screen.getByText("Slot 3 (CM)")).toBeInTheDocument();

    // Select Slot 1 (ST)
    fireEvent.click(screen.getByText("Slot 1 (ST)"));

    // Replacement shortlist for Slot 1 should appear
    expect(
      screen.getByText("REPLACEMENT SHORTLIST FOR SLOT 1 (ST)")
    ).toBeInTheDocument();
    expect(screen.getByText("SWAP FOR OPTION #1")).toBeInTheDocument();

    // Click swap
    fireEvent.click(screen.getByText("SWAP FOR OPTION #1"));
    expect(mockSubmitAction).toHaveBeenCalledWith({
      action_type: "REPLACE",
      slot_index: 1,
      candidate_token: "cand-st-2",
    });
  });
});
