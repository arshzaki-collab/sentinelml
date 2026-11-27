import React, { useState } from "react";
import {
  Award,
  Calendar,
  Compass,
  FileQuestion,
  Flame,
  Globe2,
  Shield,
  Trophy,
  Zap,
} from "lucide-react";
import { CandidateClientView, CandidateHint } from "../../types/game";
import { formatUSD } from "../dashboard/FinancialMetrics";
import { normalizeHints } from "../../utils/hints";

interface CandidateCardProps {
  candidate: CandidateClientView;
  index: number;
  availableCash: number;
  onSelect: (candidateToken: string) => void;
  disabled: boolean;
}

const renderHintIcon = (iconKey: string) => {
  const key = iconKey.toLowerCase().replace(/[\s_]+/g, "_");
  switch (key) {
    case "goals":
      return <Flame className="h-4 w-4 text-amber-400" />;
    case "assists":
      return <Zap className="h-4 w-4 text-cyan-neon" />;
    case "clean_sheets":
    case "cleansheets":
      return <Shield className="h-4 w-4 text-emerald-400" />;
    case "age":
      return <Calendar className="h-4 w-4 text-violet-400" />;
    case "league":
    case "domestic_league":
      return <Globe2 className="h-4 w-4 text-sky-400" />;
    case "ucl_goals":
    case "uclgoals":
      return <Trophy className="h-4 w-4 text-gold-glow" />;
    case "cards":
    case "yellow_cards":
      return <Award className="h-4 w-4 text-red-400" />;
    default:
      return <Compass className="h-4 w-4 text-slate-400" />;
  }
};

export const CandidateCard: React.FC<CandidateCardProps> = ({
  candidate,
  index,
  availableCash,
  onSelect,
  disabled,
}) => {
  const [confirming, setConfirming] = useState(false);
  const cost = candidate.cost_usd ?? 0;
  const isAffordable = cost <= availableCash;
  const hintsList = normalizeHints(candidate.hints);

  const handleBuyClick = () => {
    if (!isAffordable || disabled) return;
    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 4000);
    } else {
      onSelect(candidate.candidate_token);
      setConfirming(false);
    }
  };

  return (
    <div
      className={`group relative flex flex-col justify-between rounded-2xl border transition-all duration-300 p-5 ${
        isAffordable
          ? "border-stadium-border/80 bg-stadium-surface/90 hover:border-cyan-neon/60 hover:bg-stadium-card hover:shadow-cyan-glow"
          : "border-red-950/40 bg-stadium-darkest/60 opacity-60"
      }`}
    >
      {/* Top Header: Candidate Dossier Badge */}
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-stadium-border/50">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stadium-darkest border border-slate-700 text-xs font-mono font-bold text-cyan-neon">
              #{index + 1}
            </div>
            <div>
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                CONFIDENTIAL DOSSIER
              </div>
              <div className="font-display text-sm font-bold text-white flex items-center gap-1.5">
                <FileQuestion className="h-3.5 w-3.5 text-cyan-neon" />
                Anonymous {candidate.position}
              </div>
            </div>
          </div>

          {/* Position Badge */}
          <span className="rounded-md border border-cyan-500/40 bg-cyan-950/60 px-2.5 py-1 text-xs font-mono font-black text-cyan-neon">
            {candidate.position}
          </span>
        </div>

        {/* Valuation Price Tag */}
        <div className="my-4 rounded-xl border border-slate-800 bg-stadium-darkest/90 p-3 text-center">
          <div className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
            HISTORICAL MARKET VALUATION
          </div>
          <div className="font-mono text-xl sm:text-2xl font-black text-emerald-400 tracking-tight mt-0.5">
            {formatUSD(candidate.cost_usd)}
          </div>
        </div>

        {/* Statistical Hints */}
        <div className="space-y-2 mb-4">
          <div className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
            SCOUTING STATISTICAL HINTS ({hintsList.length})
          </div>
          <div className="grid grid-cols-1 gap-2">
            {hintsList.map((hint: CandidateHint, hIdx: number) => (
              <div
                key={hIdx}
                className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-stadium-darkest/60 px-3 py-2"
              >
                <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                  {renderHintIcon(hint.icon_key)}
                  <span>{hint.label}</span>
                </div>
                <span className="font-mono text-xs font-bold text-white bg-stadium-surface px-2 py-0.5 rounded border border-slate-700">
                  {hint.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Purchase Action Button */}
      <div className="pt-2 border-t border-stadium-border/40">
        {!isAffordable ? (
          <div className="w-full rounded-xl border border-red-900/50 bg-red-950/30 py-2.5 text-center text-xs font-mono font-semibold text-red-400">
            INSUFFICIENT FUNDS
          </div>
        ) : (
          <button
            onClick={handleBuyClick}
            disabled={disabled}
            className={`w-full rounded-xl py-3 font-display text-xs font-black uppercase tracking-wider transition-all duration-200 shadow-md ${
              confirming
                ? "bg-amber-500 text-stadium-darkest shadow-amber-500/40 animate-pulse"
                : "bg-gradient-to-r from-cyan-neon to-violet-neon text-stadium-darkest hover:opacity-90 shadow-cyan-glow"
            } disabled:opacity-40`}
          >
            {confirming ? "CONFIRM SIGNING?" : `SIGN CANDIDATE #${index + 1}`}
          </button>
        )}
      </div>
    </div>
  );
};
