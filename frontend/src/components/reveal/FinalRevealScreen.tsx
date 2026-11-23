import React, { useEffect } from "react";
import confetti from "canvas-confetti";
import {
  Crown,
  Medal,
  RotateCcw,
  TrendingDown,
  TrendingUp,
  Trophy,
} from "lucide-react";
import { useGame } from "../../context/GameContext";
import { LeaderboardEntry, SquadRevealedPlayer } from "../../types/game";
import { formatUSD } from "../dashboard/FinancialMetrics";

export const FinalRevealScreen: React.FC = () => {
  const { myState, room, leaderboard, playerId, leaveRoom } = useGame();

  useEffect(() => {
    // Launch festive confetti celebration on reveal mount
    try {
      confetti({
        particleCount: 120,
        spread: 80,
        origin: { y: 0.6 },
        colors: ["#00f0ff", "#8b5cf6", "#f59e0b", "#10b981"],
      });
    } catch {
      // ignore
    }
  }, []);

  if (!myState || !room) return null;

  const myEntry = leaderboard?.find((e) => e.player_id === playerId);
  const isWinner = myEntry?.rank === 1;

  // Extract revealed squad summary from myEntry if available, otherwise from myState.slots
  const squadList: SquadRevealedPlayer[] =
    myEntry?.squad_summary ||
    myState.slots.map((s) => {
      const pPrice = s.purchase_price_usd || 1;
      const v2026 = s.current_valuation_usd || 0;
      const roi = ((v2026 - pPrice) / pPrice) * 100;
      return {
        slot_index: s.slot_index,
        position: s.position,
        player_name: s.revealed_player_name || `Anonymous ${s.position}`,
        purchase_price_usd: s.purchase_price_usd || 0,
        valuation_2026_usd: v2026,
        roi_pct: Math.round(roi * 10) / 10,
      };
    });

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8 p-4 sm:p-6 pb-16">
      {/* Top Victory Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-gold-glow/50 bg-gradient-to-b from-amber-950/40 via-stadium-surface to-stadium-darkest p-6 sm:p-10 text-center shadow-gold-glow">
        <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-3xl border-2 border-gold-glow bg-amber-950/60 shadow-gold-glow">
          <Trophy className="h-10 w-10 text-gold-trophy" />
        </div>

        <div className="inline-block rounded-full bg-gold-glow/10 border border-gold-glow/40 px-4 py-1 text-xs font-mono font-bold text-gold-glow uppercase tracking-wider mb-2">
          2026 FINAL SETTLEMENT &amp; AUDITED VALUATIONS
        </div>

        <h1 className="font-display text-3xl sm:text-5xl font-black text-white tracking-tight">
          {isWinner ? "CHAMPION OF EUROPE!" : "DECADE SETTLEMENT COMPLETE"}
        </h1>

        <p className="mx-auto max-w-xl text-xs sm:text-sm text-slate-300 mt-2">
          All confidential player identities and 2026 historical market valuations are fully unmasked. The portfolio with the highest total net worth takes the Blind Billion trophy.
        </p>
      </div>

      {/* Leaderboard Podium Section */}
      {leaderboard && leaderboard.length > 0 && (
        <div className="rounded-2xl border border-stadium-border bg-stadium-surface/90 p-6 backdrop-blur-md">
          <div className="flex items-center gap-2 font-display text-lg font-black text-white mb-4">
            <Medal className="h-5 w-5 text-gold-glow" />
            FINAL TOURNAMENT STANDINGS
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {leaderboard.map((entry: LeaderboardEntry) => {
              const isLocal = entry.player_id === playerId;
              return (
                <div
                  key={entry.player_id}
                  className={`flex flex-col justify-between rounded-xl border p-4 transition ${
                    entry.rank === 1
                      ? "border-gold-glow/60 bg-amber-950/20 shadow-gold-glow"
                      : isLocal
                      ? "border-cyan-neon/50 bg-cyan-950/20"
                      : "border-slate-800 bg-stadium-darkest/70"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5 font-display text-sm font-black text-white">
                        {entry.rank === 1 && <Crown className="h-4 w-4 text-gold-glow" />}
                        <span>RANK #{entry.rank}</span>
                      </div>
                      {isLocal && (
                        <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[9px] font-mono text-cyan-neon font-bold">
                          YOU
                        </span>
                      )}
                    </div>

                    <div className="font-display text-base font-bold text-white truncate">
                      {entry.display_name}
                    </div>

                    <div className="mt-3 space-y-1 text-xs font-mono">
                      <div className="flex justify-between text-slate-400">
                        <span>Squad Value:</span>
                        <span className="text-cyan-300">{formatUSD(entry.squad_valuation)}</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Cash Balance:</span>
                        <span className="text-emerald-400">{formatUSD(entry.cash_balance)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800">
                    <div className="text-[10px] font-mono text-slate-400">TOTAL NET WORTH</div>
                    <div className="font-mono text-lg font-black text-gold-glow">
                      {formatUSD(entry.final_net_worth)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Unmasked 7-Player Squad Dossiers */}
      <div className="rounded-2xl border border-stadium-border bg-stadium-surface/90 p-6 backdrop-blur-md space-y-4">
        <div className="flex items-center justify-between border-b border-stadium-border/60 pb-3">
          <div>
            <h2 className="font-display text-xl font-black text-white">
              YOUR UNMASKED SQUAD &amp; ROI PERFORMANCE
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Historical purchase costs vs authentic 2026 market valuations.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {squadList.map((player: SquadRevealedPlayer) => {
            const isProfit = player.valuation_2026_usd >= player.purchase_price_usd;
            const diffUSD = player.valuation_2026_usd - player.purchase_price_usd;

            return (
              <div
                key={player.slot_index}
                className="flex flex-col justify-between rounded-xl border border-slate-800 bg-stadium-card/80 p-4 transition hover:border-slate-600"
              >
                <div>
                  <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1.5">
                    <span>Slot {player.slot_index}</span>
                    <span className="font-bold text-white bg-slate-800 px-2 py-0.5 rounded">
                      {player.position}
                    </span>
                  </div>

                  {/* Real Player Name Revealed! */}
                  <div className="font-display text-base font-black text-white truncate my-1">
                    {player.player_name}
                  </div>

                  {/* Financial Stats */}
                  <div className="my-3 rounded-lg bg-stadium-darkest/80 p-2.5 text-xs font-mono space-y-1">
                    <div className="flex justify-between text-slate-400">
                      <span>Bought At:</span>
                      <span className="text-white">{formatUSD(player.purchase_price_usd)}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>2026 Value:</span>
                      <span className="text-cyan-300 font-bold">
                        {formatUSD(player.valuation_2026_usd)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* ROI indicator */}
                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono font-bold">
                  <span className="text-slate-400">ROI:</span>
                  <div
                    className={`flex items-center gap-1 ${
                      isProfit ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {isProfit ? (
                      <TrendingUp className="h-3.5 w-3.5" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5" />
                    )}
                    <span>
                      {isProfit ? "+" : ""}
                      {player.roi_pct}% ({formatUSD(diffUSD)})
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Play Again & Leave */}
      <div className="flex items-center justify-center gap-4 pt-6">
        <button
          onClick={leaveRoom}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-neon to-violet-neon px-8 py-4 font-display text-sm font-black text-stadium-darkest tracking-wider shadow-cyan-glow transition hover:opacity-90"
        >
          <RotateCcw className="h-4 w-4" />
          PLAY AGAIN (MAIN MENU)
        </button>
      </div>
    </div>
  );
};
