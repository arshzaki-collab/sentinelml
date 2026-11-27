import React from "react";
import { Eye, Users } from "lucide-react";
import { useGame } from "../../context/GameContext";
import { CandidateCard } from "./CandidateCard";
import { TurnWaitingOverlay } from "../barrier/TurnWaitingOverlay";

export const ScoutingMarket: React.FC = () => {
  const { myState, room, playerId, submitAction, isLoading } = useGame();

  if (!myState || !room) return null;

  const me = room.players.find((p) => p.player_id === playerId);
  const activeSlotIndex = room.current_slot_index;

  // If the player has already submitted their turn in this round, show the synchronized waiting barrier
  if (me?.is_turn_submitted) {
    return <TurnWaitingOverlay />;
  }

  const activeShortlist = activeSlotIndex ? myState.shortlists[String(activeSlotIndex)] : null;

  if (!activeShortlist || !activeShortlist.candidates.length) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-stadium-border bg-stadium-surface">
        <Users className="h-10 w-10 text-slate-500 mb-2" />
        <h3 className="font-display font-bold text-lg text-white">No Active Shortlist Available</h3>
        <p className="text-xs text-slate-400 mt-1">
          Awaiting next season schedule from the referee engine.
        </p>
      </div>
    );
  }

  const handlePurchase = async (candidateToken: string) => {
    try {
      await submitAction({
        action_type: "BUY",
        candidate_token: candidateToken,
      });
    } catch {
      // handled in context
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Dossier Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-2xl border border-stadium-border bg-stadium-surface/90 p-4 sm:p-5 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-neon uppercase tracking-wider">
            <span className="inline-block h-2 w-2 rounded-full bg-cyan-neon animate-pulse" />
            BUYING SEASON {room.current_year} — SLOT {activeSlotIndex} ({activeShortlist.required_position || (activeShortlist as any).position || activeShortlist.candidates[0]?.position || ""})
          </div>
          <h2 className="font-display text-xl sm:text-2xl font-black text-white mt-0.5">
            SCOUTING MARKET CANDIDATE DOSSIERS
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Evaluate all 4 anonymous candidates and commit your signature. Identities remain strictly confidential until 2026.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-2 text-xs font-mono text-cyan-300">
          <Eye className="h-4 w-4 text-cyan-neon" />
          <span>ZERO LEAKAGE GUARD ACTIVE</span>
        </div>
      </div>

      {/* 4 Candidate Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {activeShortlist.candidates.map((cand, idx) => (
          <CandidateCard
            key={cand.candidate_token}
            candidate={cand}
            index={idx}
            availableCash={myState.cash_balance}
            onSelect={handlePurchase}
            disabled={isLoading}
          />
        ))}
      </div>
    </div>
  );
};
