/**
 * Game domain types and API contracts for Blind Billion 2.0.
 */

export type RoomStatus = "LOBBY" | "IN_GAME" | "COMPLETED";

export type GamePhase =
  | "BUYING_SEASON"
  | "TRANSFER_WINDOW"
  | "FINAL_SETTLEMENT"
  | "COMPLETED";

export type Position = "ST" | "WG" | "CM" | "CB" | "GK";

export type AIDifficulty = "ROOKIE" | "PRO" | "LEGEND";

export interface PlayerPublicView {
  player_id: string;
  display_name: string;
  is_host: boolean;
  is_ready: boolean;
  is_connected: boolean;
  is_turn_submitted: boolean;
  joined_at: string;
  is_ai?: boolean;
  ai_difficulty?: AIDifficulty | string | null;
}

export interface RoomPublicView {
  room_code: string;
  status: RoomStatus;
  host_player_id: string;
  current_year: number;
  current_phase: string;
  current_slot_index: number | null;
  timeline_step_index: number;
  players: PlayerPublicView[];
  created_at: string;
  is_game_started: boolean;
  is_completed: boolean;
}

export interface CandidateHint {
  label: string;
  value: string | number;
  icon_key: string;
}

export interface CandidateClientView {
  candidate_token: string;
  cost_usd: number;
  position: Position | string;
  hints: CandidateHint[] | Record<string, string | number>;
}

export interface ShortlistClientView {
  slot_index: number;
  required_position: Position | string;
  buying_year: number;
  candidates: CandidateClientView[];
}

export interface SquadSlotClientView {
  slot_index: number;
  position?: Position | string;
  required_position?: Position | string;
  buying_year: number;
  is_filled: boolean;
  purchase_price_usd: number | null;
  purchase_year?: number | null;
  current_valuation_usd?: number | null;
  assigned_candidate_token?: string | null;
  is_revealed?: boolean;
  revealed_player_name?: string | null;
  current_player_name?: string | null;
  current_player_id?: string | null;
  revealed_player_id?: number | null;
}

export interface TransactionRecordClientView {
  year: number;
  phase: string;
  action: string;
  slot_index: number;
  cost_usd: number;
  proceeds_usd: number;
  candidate_token: string | null;
  player_name: string | null;
}

export interface PlayerGameStateView {
  player_id: string;
  display_name: string;
  cash_balance: number;
  current_year: number;
  current_phase: string;
  active_slot_index: number | null;
  timeline_step_index: number;
  filled_slots_count: number;
  is_completed: boolean;
  final_net_worth: number | null;
  final_squad_value: number | null;
  slots: SquadSlotClientView[];
  shortlists: Record<string, ShortlistClientView>;
  transaction_history: TransactionRecordClientView[];
}

export interface SquadRevealedPlayer {
  slot_index: number;
  position: string;
  player_name: string;
  purchase_price_usd: number;
  valuation_2026_usd: number;
  roi_pct: number;
}

export interface LeaderboardEntry {
  player_id: string;
  display_name: string;
  rank: number;
  cash_balance: number;
  squad_valuation: number;
  final_net_worth: number;
  total_roi_pct: number;
  squad_summary: SquadRevealedPlayer[];
}

export interface RoomGameStateResponse {
  room: RoomPublicView;
  my_state: PlayerGameStateView;
  leaderboard: LeaderboardEntry[] | null;
}

export interface CreateRoomResponse {
  room: RoomPublicView;
  session_token: string;
  player_id: string;
}

export interface JoinRoomResponse {
  room: RoomPublicView;
  session_token: string;
  player_id: string;
}

export interface ActionResponse {
  success: boolean;
  message: string;
  action_type: string;
  new_balance: number;
  is_barrier_cleared: boolean;
  room: RoomPublicView;
  my_state: PlayerGameStateView;
}

export type RealtimeEventType =
  | "PLAYER_JOINED"
  | "PLAYER_LEFT"
  | "PLAYER_READY"
  | "PLAYER_DISCONNECTED"
  | "PLAYER_RECONNECTED"
  | "HOST_MIGRATED"
  | "GAME_STARTED"
  | "ACTION_COMMITTED"
  | "ROUND_ADVANCED"
  | "GAME_FINISHED"
  | "HEARTBEAT"
  | "ERROR";

export interface WebSocketEvent<T = unknown> {
  event: RealtimeEventType;
  room_code: string;
  payload: T;
  timestamp: string;
}
