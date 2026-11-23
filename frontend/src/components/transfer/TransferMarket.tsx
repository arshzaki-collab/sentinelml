import React, { useState } from "react";
import { FastForward, RefreshCw } from "lucide-react";
import { useGame } from "../../context/GameContext";
import { CandidateClientView, SquadSlotClientView } from "../../types/game";
import { formatUSD } from "../dashboard/FinancialMetrics";
import { TurnWaitingOverlay } from "../barrier/TurnWaitingOverlay";

export const TransferMarket: React.FC = () => {
  const { myState, room, playerId, submitAction, isLoading } = useGame();
  const [selectedSlotIndex, setSelectedSlotIndex] = useState<number | null>(null);

  if (!myState || !room) return null;

  const me = room.players.find((p) => p.player_id === playerId);
  if (me?.is_turn_submitted) {
    return <TurnWaitingOverlay />;
  }

  // Eligible slots to sell & replace: must be filled and signed before current year
  const eligibleSlots = myState.slots.filter(
    (s) => s.is_filled && s.buying_year < room.current_year
  );

  const selectedSlot = selectedSlotIndex
    ? myState.slots.find((s) => s.slot_index === selectedSlotIndex)
    : null;

  const shortlist = selectedSlotIndex
    ? myState.shortlists[String(selectedSlotIndex)]
    : null;

  // Replacement candidates are candidates in the shortlist not currently assigned to this slot
  const replacementCandidates = shortlist
    ? shortlist.candidates.filter(
        (c) => c.candidate_token !== selectedSlot?.assigned_candidate_token
      )
    : [];

  const handlePass = async () => {
    try {
      await submitAction({ action_type: "PASS" });
    } catch {
      // handled in context
    }
  };

  const handleReplace = async (candidateToken: string) => {
    if (!selectedSlotIndex) return;
    try {
      await submitAction({
        action_type: "REPLACE",
        slot_index: selectedSlotIndex,
        candidate_token: candidateToken,
      });
      setSelectedSlotIndex(null);
    } catch {
      // handled in context
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-2xl border border-violet-900/60 bg-stadium-surface/90 p-5 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-violet-neon uppercase tracking-wider">
            <RefreshCw className="h-4 w-4 animate-spin-slow" />
            TRANSFER WINDOW {room.current_year}
          </div>
          <h2 className="font-display text-2xl font-black text-white mt-1">
            PORTFOLIO REBALANCING &amp; SQUAD SWAPS
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-xl">
            Liquidate any eligible squad player at their updated {room.current_year} historical market valuation. If sold, sign an immediate replacement from their original 4-player shortlist. Or PASS to preserve your squad.
          </p>
        </div>

        {/* Big PASS button */}
        <button
          onClick={handlePass}
          disabled={isLoading}
          className="flex items-center gap-2 rounded-xl bg-slate-800 border border-slate-700 px-6 py-3 font-display text-xs font-black text-white hover:border-slate-500 hover:bg-slate-700 transition shadow-lg shrink-0 disabled:opacity-40"
        >
          <FastForward className="h-4 w-4 text-cyan-neon" />
          PASS (KEEP SQUAD)
        </button>
      </div>

      {/* Eligible Owned Players to Swap */}
      <div>
        <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider mb-3">
          SELECT SQUAD SLOT TO REBALANCE ({eligibleSlots.length} ELIGIBLE)
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {eligibleSlots.map((slot: SquadSlotClientView) => {
            const isSelected = selectedSlotIndex === slot.slot_index;
            return (
              <button
                key={slot.slot_index}
                onClick={() => setSelectedSlotIndex(slot.slot_index)}
                className={`flex flex-col text-left rounded-xl border p-4 transition-all duration-200 ${
                  isSelected
                    ? "border-violet-neon bg-violet-950/40 shadow-violet-glow"
                    : "border-stadium-border/80 bg-stadium-card/70 hover:border-slate-600 hover:bg-stadium-card"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <span className="font-display font-black text-sm text-cyan-neon">
                    Slot {slot.slot_index} ({slot.position})
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Signed in {slot.buying_year}
                  </span>
                </div>

                <div className="font-display text-sm font-bold text-white mb-2">
                  Anonymous {slot.position}
                </div>

                <div className="flex items-center justify-between w-full text-xs font-mono pt-2 border-t border-slate-800">
                  <span className="text-slate-400">Sale Value ({room.current_year}):</span>
                  <span className="font-bold text-emerald-400">
                    {formatUSD(slot.current_valuation_usd)}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Replacement Candidate Picker (if a slot is selected) */}
      {selectedSlot && shortlist && (
        <div className="rounded-2xl border border-violet-500/40 bg-stadium-surface/90 p-5 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between border-b border-stadium-border/60 pb-3">
            <div>
              <div className="text-xs font-mono text-violet-neon font-bold">
                REPLACEMENT SHORTLIST FOR SLOT {selectedSlot.slot_index} ({selectedSlot.position})
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Selling this player nets{" "}
                <span className="text-emerald-400 font-bold font-mono">
                  +{formatUSD(selectedSlot.current_valuation_usd)}
                </span>
                . Select one of the {replacementCandidates.length} remaining candidates from the original shortlist:
              </p>
            </div>
            <button
              onClick={() => setSelectedSlotIndex(null)}
              className="text-xs font-mono text-slate-400 hover:text-white"
            >
              CANCEL SELECTION
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {replacementCandidates.map((cand: CandidateClientView, idx: number) => {
              // Net cost = candidate cost - sale proceeds
              const netImpact = cand.cost_usd - (selectedSlot.current_valuation_usd || 0);
              const isAffordable = myState.cash_balance >= netImpact;

              return (
                <div
                  key={cand.candidate_token}
                  className="rounded-xl border border-stadium-border bg-stadium-card/80 p-4 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
                      <span>Option #{idx + 1}</span>
                      <span className="text-white font-bold">{cand.position}</span>
                    </div>

                    <div className="my-2 rounded-lg bg-stadium-darkest p-2.5 text-center">
                      <div className="text-[10px] font-mono text-slate-400">SIGNING PRICE</div>
                      <div className="font-mono text-lg font-black text-cyan-300">
                        {formatUSD(cand.cost_usd)}
                      </div>
                      <div className="text-[10px] font-mono mt-0.5">
                        Net Impact:{" "}
                        <span
                          className={`font-bold ${
                            netImpact <= 0 ? "text-emerald-400" : "text-amber-400"
                          }`}
                        >
                          {netImpact <= 0 ? `+${formatUSD(-netImpact)}` : `-${formatUSD(netImpact)}`}
                        </span>
                      </div>
                    </div>

                    {/* Hints */}
                    <div className="space-y-1 my-3 text-xs">
                      {cand.hints.map((hint, hIdx) => (
                        <div
                          key={hIdx}
                          className="flex justify-between rounded bg-stadium-darkest/50 px-2 py-1 text-slate-300"
                        >
                          <span>{hint.label}:</span>
                          <span className="font-mono font-bold text-white">{hint.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => handleReplace(cand.candidate_token)}
                    disabled={!isAffordable || isLoading}
                    className="w-full mt-2 rounded-lg bg-gradient-to-r from-violet-600 to-cyan-500 py-2.5 font-display text-xs font-black uppercase text-stadium-darkest hover:opacity-90 disabled:opacity-40 transition shadow-md"
                  >
                    SWAP FOR OPTION #{idx + 1}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
