import React from "react";
import { Bot, CheckCircle2, Clock, Crown, ShieldCheck } from "lucide-react";
import { useGame } from "../../context/GameContext";
import { PlayerPublicView } from "../../types/game";

export const TurnWaitingOverlay: React.FC = () => {
  const { room, playerId } = useGame();
  if (!room) return null;

  const submittedCount = room.players.filter((p) => p.is_turn_submitted).length;
  const totalCount = room.players.length;

  return (
    <div className="w-full rounded-2xl border border-cyan-500/40 bg-stadium-surface/90 p-6 sm:p-8 backdrop-blur-xl shadow-cyan-glow text-center">
      {/* Animated Loading Radar / Shield */}
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border-2 border-cyan-neon bg-cyan-950/60 shadow-cyan-glow animate-pulse">
        <ShieldCheck className="h-8 w-8 text-cyan-neon" />
      </div>

      <div className="inline-block rounded-full bg-cyan-500/10 border border-cyan-500/30 px-3 py-1 text-xs font-mono text-cyan-neon uppercase tracking-wider mb-2">
        TURN SUBMITTED &amp; SECURED
      </div>

      <h2 className="font-display text-2xl sm:text-3xl font-black text-white">
        AWAITING ROUND BARRIER SYNCHRONIZATION
      </h2>

      <p className="mx-auto max-w-lg text-xs sm:text-sm text-slate-300 mt-2">
        Your decision for {room.current_year} is securely locked on the server. The season will advance simultaneously for all managers once every competitor submits their action.
      </p>

      {/* Progress Counter */}
      <div className="my-6 mx-auto max-w-md">
        <div className="flex justify-between text-xs font-mono text-slate-400 mb-2">
          <span>MANAGERS READY</span>
          <span className="text-cyan-neon font-bold">
            {submittedCount} / {totalCount} SUBMITTED
          </span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-stadium-darkest border border-slate-700 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-neon to-violet-neon transition-all duration-500"
            style={{ width: `${(submittedCount / Math.max(totalCount, 1)) * 100}%` }}
          />
        </div>
      </div>

      {/* Peers Status Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 max-w-2xl mx-auto text-left">
        {room.players.map((p: PlayerPublicView) => {
          const isLocal = p.player_id === playerId;
          return (
            <div
              key={p.player_id}
              className={`flex items-center justify-between rounded-xl border p-3 ${
                p.is_turn_submitted
                  ? "border-emerald-500/40 bg-emerald-950/20 text-emerald-300"
                  : "border-slate-800 bg-stadium-darkest/60 text-slate-400"
              }`}
            >
              <div className="flex items-center gap-2 truncate">
                {p.is_ai ? (
                  <Bot className="h-4 w-4 text-violet-400 shrink-0" />
                ) : p.is_host ? (
                  <Crown className="h-4 w-4 text-amber-400 shrink-0" />
                ) : (
                  <div className="h-2 w-2 rounded-full bg-slate-500 shrink-0" />
                )}
                <span className="font-display text-xs font-bold truncate">
                  {p.display_name} {isLocal && "(You)"}
                </span>
              </div>

              <div>
                {p.is_turn_submitted ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : (
                  <Clock className="h-4 w-4 text-amber-400 shrink-0 animate-spin" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
