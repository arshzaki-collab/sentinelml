import React, { useState } from "react";
import { useGame } from "../../context/GameContext";
import { TimelineProgress } from "./TimelineProgress";
import { FinancialMetrics } from "./FinancialMetrics";
import { FormationPitch } from "./FormationPitch";
import { ScoutingMarket } from "../scouting/ScoutingMarket";
import { TransferMarket } from "../transfer/TransferMarket";
import { FinalRevealScreen } from "../reveal/FinalRevealScreen";
import { LayoutGrid, ShoppingBag } from "lucide-react";

export const StadiumDashboard: React.FC = () => {
  const { room, myState } = useGame();
  const [mobileTab, setMobileTab] = useState<"market" | "pitch">("market");

  if (!room || !myState) return null;

  // If game is completed or at final settlement, show full-screen final reveal
  if (room.is_completed || room.current_phase === "FINAL_SETTLEMENT") {
    return <FinalRevealScreen />;
  }

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 p-4 sm:p-6 pb-12">
      {/* 1. Timeline Progress Bar */}
      <div className="rounded-2xl border border-stadium-border bg-stadium-surface/80 p-3 sm:p-4 backdrop-blur-md shadow-lg">
        <TimelineProgress />
      </div>

      {/* 2. Financial Metrics Strip */}
      <FinancialMetrics />

      {/* Mobile Tab Switcher */}
      <div className="grid grid-cols-2 gap-2 lg:hidden rounded-xl border border-stadium-border bg-stadium-darkest p-1">
        <button
          onClick={() => setMobileTab("market")}
          className={`flex items-center justify-center gap-2 py-2 text-xs font-mono font-bold rounded-lg transition ${
            mobileTab === "market"
              ? "bg-cyan-950 text-cyan-neon border border-cyan-500/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <ShoppingBag className="h-4 w-4" />
          MARKET DOSSIERS
        </button>
        <button
          onClick={() => setMobileTab("pitch")}
          className={`flex items-center justify-center gap-2 py-2 text-xs font-mono font-bold rounded-lg transition ${
            mobileTab === "pitch"
              ? "bg-cyan-950 text-cyan-neon border border-cyan-500/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <LayoutGrid className="h-4 w-4" />
          TACTICAL PITCH (7 SLOTS)
        </button>
      </div>

      {/* 3. Main Operational Area: Pitch & Market */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Formation Pitch (Hidden on mobile if market tab selected) */}
        <div
          className={`lg:col-span-4 xl:col-span-4 space-y-3 ${
            mobileTab === "pitch" ? "block" : "hidden lg:block"
          }`}
        >
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
            <span>SQUAD FORMATION (7 SLOTS)</span>
            <span className="text-emerald-400 font-bold">
              {myState.filled_slots_count} / 7 SIGNED
            </span>
          </div>
          <FormationPitch />
        </div>

        {/* Right Column: Active Market or Transfer Window */}
        <div
          className={`lg:col-span-8 xl:col-span-8 ${
            mobileTab === "market" ? "block" : "hidden lg:block"
          }`}
        >
          {room.current_phase === "BUYING_SEASON" && <ScoutingMarket />}
          {room.current_phase === "TRANSFER_WINDOW" && <TransferMarket />}
        </div>
      </div>
    </div>
  );
};
