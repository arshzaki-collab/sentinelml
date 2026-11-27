import React from "react";
import { DollarSign, Shield, TrendingUp, Users } from "lucide-react";
import { useGame } from "../../context/GameContext";

export const formatUSD = (val: number | null | undefined): string => {
  if (val === null || val === undefined) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(val);
};

export const FinancialMetrics: React.FC = () => {
  const { myState, room } = useGame();
  if (!myState || !room) return null;

  // Calculate squad valuation as of current year from filled slots
  const squadValuation = myState.slots
    ? myState.slots
        .filter((s) => s.is_filled)
        .reduce((sum, s) => sum + (s.current_valuation_usd ?? s.purchase_price_usd ?? 0), 0)
    : 0;

  const totalNetWorth = myState.cash_balance + squadValuation;
  const filledSlotsCount = myState.slots ? myState.slots.filter((s) => s.is_filled).length : 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 w-full">
      {/* 1. Cash Reserves */}
      <div className="rounded-xl border border-emerald-900/40 bg-stadium-card/90 p-4 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between text-xs font-mono text-emerald-400 mb-1">
          <span>AVAILABLE CASH</span>
          <DollarSign className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="font-mono text-lg sm:text-2xl font-black text-emerald-300">
          {formatUSD(myState.cash_balance)}
        </div>
        <div className="text-[10px] text-slate-400 mt-0.5">
          Starting Budget: $1.00B
        </div>
      </div>

      {/* 2. Squad Valuation */}
      <div className="rounded-xl border border-cyan-900/40 bg-stadium-card/90 p-4 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between text-xs font-mono text-cyan-400 mb-1">
          <span>SQUAD VALUATION</span>
          <TrendingUp className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="font-mono text-lg sm:text-2xl font-black text-cyan-300">
          {formatUSD(squadValuation)}
        </div>
        <div className="text-[10px] text-slate-400 mt-0.5">
          As of July 1, {room.current_year}
        </div>
      </div>

      {/* 3. Total Net Worth */}
      <div className="rounded-xl border border-violet-900/40 bg-stadium-card/90 p-4 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between text-xs font-mono text-violet-400 mb-1">
          <span>TOTAL NET WORTH</span>
          <Shield className="h-4 w-4 text-violet-400" />
        </div>
        <div className="font-mono text-lg sm:text-2xl font-black text-violet-300">
          {formatUSD(totalNetWorth)}
        </div>
        <div className="text-[10px] text-slate-400 mt-0.5">
          Cash + Historical Squad Value
        </div>
      </div>

      {/* 4. Squad Slots Progress */}
      <div className="rounded-xl border border-stadium-border bg-stadium-card/90 p-4 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
          <span>SQUAD SLOTS</span>
          <Users className="h-4 w-4 text-slate-400" />
        </div>
        <div className="font-mono text-lg sm:text-2xl font-black text-white">
          {filledSlotsCount} <span className="text-slate-500 text-sm font-normal">/ 7 SIGNED</span>
        </div>
        <div className="text-[10px] text-slate-400 mt-0.5">
          Phase: {room.current_phase.replace("_", " ")}
        </div>
      </div>
    </div>
  );
};
