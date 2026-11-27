import React from "react";
import { Check } from "lucide-react";
import { useGame } from "../../context/GameContext";
import { SquadSlotClientView } from "../../types/game";
import { formatUSD } from "./FinancialMetrics";

// Formation tactical grid layout (e.g. 2-2-2-1)
// ST at top, WG slightly below, CMs in midfield, CBs in defense, GK in goal
const SLOT_TACTICAL_LAYOUT: Record<number, { top: string; left: string; label: string }> = {
  1: { top: "12%", left: "50%", label: "ST" }, // 2016 Striker
  2: { top: "26%", left: "75%", label: "WG" }, // 2017 Winger
  3: { top: "42%", left: "32%", label: "CM 1" }, // 2018 Midfielder 1
  5: { top: "42%", left: "68%", label: "CM 2" }, // 2021 Midfielder 2
  4: { top: "65%", left: "32%", label: "CB 1" }, // 2020 Defender 1
  6: { top: "65%", left: "68%", label: "CB 2" }, // 2023 Defender 2
  7: { top: "85%", left: "50%", label: "GK" }, // 2024 Goalkeeper
};

export const FormationPitch: React.FC = () => {
  const { myState, room } = useGame();
  if (!myState || !room) return null;

  const activeSlotIndex = room.current_slot_index;

  return (
    <div className="relative w-full h-[480px] sm:h-[540px] rounded-2xl border border-pitch-border/50 bg-pitch-grass overflow-hidden shadow-2xl">
      {/* Pitch Grass Texture & Tactical Grid */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#062817] via-[#09351f] to-[#062817] opacity-95" />

      {/* Pitch Markings */}
      <div className="absolute inset-4 rounded-xl border border-pitch-line pointer-events-none">
        {/* Halfway line */}
        <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-pitch-line" />
        {/* Center circle */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full border border-pitch-line" />
        {/* Penalty Area Top */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-20 border-b border-x border-pitch-line rounded-b-md" />
        {/* Penalty Area Bottom (GK) */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-48 h-20 border-t border-x border-pitch-line rounded-t-md" />
      </div>

      {/* 7 Tactical Slots */}
      {myState.slots.map((slot: SquadSlotClientView) => {
        const position = slot.position || slot.required_position || "Slot";
        const layout = SLOT_TACTICAL_LAYOUT[slot.slot_index] || {
          top: "50%",
          left: "50%",
          label: position,
        };
        const isActive = activeSlotIndex === slot.slot_index && room.current_phase === "BUYING_SEASON";
        const playerName = slot.is_revealed && slot.revealed_player_name
          ? slot.revealed_player_name
          : slot.is_filled
          ? (slot.current_player_name || `Anonymous ${position}`)
          : `Empty Slot ${slot.slot_index}`;

        return (
          <div
            key={slot.slot_index}
            style={{ top: layout.top, left: layout.left }}
            className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer"
          >
            {/* Slot Token / Badge */}
            <div
              className={`relative flex h-14 w-14 sm:h-16 sm:w-16 flex-col items-center justify-center rounded-2xl border-2 transition-all duration-300 ${
                slot.is_filled
                  ? "border-emerald-400 bg-emerald-950/80 text-emerald-300 shadow-lg shadow-emerald-950/50"
                  : isActive
                  ? "border-cyan-neon bg-cyan-950 text-cyan-neon shadow-cyan-glow-lg animate-pulse"
                  : "border-slate-700/60 bg-stadium-surface/80 text-slate-400 hover:border-slate-500"
              }`}
            >
              <div className="font-display font-black text-xs sm:text-sm tracking-wider">
                {position}
              </div>
              <div className="text-[9px] font-mono text-slate-400">
                {slot.buying_year}
              </div>

              {/* Status Indicator Icon */}
              {slot.is_filled && (
                <div className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-stadium-darkest">
                  <Check className="h-2.5 w-2.5 stroke-[3]" />
                </div>
              )}
            </div>

            {/* Name / Price Tag Underneath */}
            <div className="mt-1 flex flex-col items-center rounded-md bg-stadium-darkest/90 px-2 py-0.5 border border-slate-800 backdrop-blur-sm max-w-[120px] text-center">
              <span className="text-[10px] font-display font-bold text-white truncate w-full">
                {playerName}
              </span>
              {slot.is_filled && slot.purchase_price_usd && (
                <span className="text-[9px] font-mono font-medium text-emerald-400">
                  {formatUSD(slot.purchase_price_usd)}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
