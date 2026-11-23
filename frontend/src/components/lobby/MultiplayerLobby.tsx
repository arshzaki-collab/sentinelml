import React, { useState } from "react";
import {
  Bot,
  CheckCircle2,
  Clock,
  Copy,
  Crown,
  Play,
  Plus,
  Trash2,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useGame } from "../../context/GameContext";
import { AIDifficulty, PlayerPublicView } from "../../types/game";

export const MultiplayerLobby: React.FC = () => {
  const {
    room,
    playerId,
    roomCode,
    toggleReady,
    addAI,
    removeAI,
    startGame,
    leaveRoom,
    isLoading,
  } = useGame();

  const [copied, setCopied] = useState(false);
  const [selectedDifficulty, setSelectedDifficulty] = useState<AIDifficulty>("PRO");

  if (!room) return null;

  const me = room.players.find((p) => p.player_id === playerId);
  const isHost = me?.is_host ?? false;
  const canStart =
    isHost &&
    room.players.length >= 2 &&
    room.players.every((p) => p.is_ready);

  const copyCode = () => {
    if (!roomCode) return;
    navigator.clipboard.writeText(roomCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAddAI = async () => {
    if (room.players.length >= 4) return;
    await addAI(selectedDifficulty);
  };

  return (
    <div className="min-h-[calc(100vh-65px)] flex flex-col items-center justify-center p-4 sm:p-6 tactical-grid">
      <div className="w-full max-w-3xl rounded-2xl border border-stadium-border bg-stadium-surface/90 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
        {/* Top Bar: Room Code Showcase */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-stadium-border/60 pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-neon uppercase tracking-wider">
              <span className="inline-block h-2 w-2 rounded-full bg-cyan-neon animate-pulse" />
              MULTIPLAYER BOARDROOM
            </div>
            <h1 className="font-display text-2xl sm:text-3xl font-black text-white">
              SQUAD DRAFT LOBBY
            </h1>
          </div>

          {/* Room Code Badge */}
          <div className="flex items-center gap-2">
            <button
              onClick={copyCode}
              title="Copy 4-character Room Code"
              className="flex items-center gap-3 rounded-xl border border-cyan-500/40 bg-cyan-950/50 px-5 py-3 transition hover:border-cyan-neon hover:bg-cyan-900/60 shadow-cyan-glow group"
            >
              <div className="text-left">
                <div className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                  ROOM CODE
                </div>
                <div className="font-mono text-2xl font-black tracking-widest text-white">
                  {room.room_code}
                </div>
              </div>
              {copied ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              ) : (
                <Copy className="h-5 w-5 text-cyan-400 group-hover:text-white transition" />
              )}
            </button>
          </div>
        </div>

        {/* Players List Grid */}
        <div className="my-6">
          <div className="mb-3 flex items-center justify-between text-xs font-mono text-slate-400">
            <span>
              PARTICIPANTS ({room.players.length}/4 PLAYERS)
            </span>
            <span>MIN 2 PLAYERS TO START</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {room.players.map((p: PlayerPublicView) => {
              const isLocal = p.player_id === playerId;
              return (
                <div
                  key={p.player_id}
                  className={`flex items-center justify-between rounded-xl border p-4 transition ${
                    isLocal
                      ? "border-cyan-neon/50 bg-cyan-950/20 shadow-cyan-glow"
                      : "border-stadium-border/80 bg-stadium-darkest/70"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-xl font-display font-bold text-sm ${
                        p.is_ai
                          ? "bg-violet-950 border border-violet-500/40 text-violet-neon"
                          : p.is_host
                          ? "bg-amber-950 border border-amber-500/40 text-amber-400"
                          : "bg-slate-800 border border-slate-700 text-slate-200"
                      }`}
                    >
                      {p.is_ai ? <Bot className="h-5 w-5" /> : p.display_name.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-display font-bold text-sm text-white">
                          {p.display_name}
                        </span>
                        {isLocal && (
                          <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[9px] font-mono text-cyan-neon font-bold">
                            YOU
                          </span>
                        )}
                        {p.is_host && (
                          <span className="flex items-center gap-0.5 rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-mono text-amber-300 font-bold">
                            <Crown className="h-2.5 w-2.5" /> HOST
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-slate-400">
                        {p.is_ai ? (
                          <span className="text-violet-400 font-mono text-[10px]">
                            AI BOT ({p.ai_difficulty})
                          </span>
                        ) : p.is_connected ? (
                          <span className="flex items-center gap-1 text-emerald-400">
                            <Wifi className="h-2.5 w-2.5" /> Connected
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-slate-500">
                            <WifiOff className="h-2.5 w-2.5" /> Offline
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Ready Status & Host Actions */}
                  <div className="flex items-center gap-2">
                    <div
                      className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
                        p.is_ready
                          ? "border border-emerald-500/30 bg-emerald-950/40 text-emerald-300"
                          : "border border-amber-500/30 bg-amber-950/40 text-amber-300"
                      }`}
                    >
                      {p.is_ready ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                          <span>READY</span>
                        </>
                      ) : (
                        <>
                          <Clock className="h-3.5 w-3.5 text-amber-400" />
                          <span>WAITING</span>
                        </>
                      )}
                    </div>

                    {/* Remove AI button (Host Only) */}
                    {isHost && p.is_ai && (
                      <button
                        onClick={() => removeAI(p.player_id)}
                        title="Remove AI opponent"
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-red-950/50 hover:text-red-400 transition"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Placeholder Empty Slots */}
            {Array.from({ length: 4 - room.players.length }).map((_, idx) => (
              <div
                key={`empty-${idx}`}
                className="flex items-center justify-center rounded-xl border border-dashed border-slate-800 bg-stadium-darkest/40 p-4 text-xs font-mono text-slate-500"
              >
                EMPTY SQUAD SEAT ({room.players.length + idx + 1}/4)
              </div>
            ))}
          </div>
        </div>

        {/* Host AI Opponent Controls */}
        {isHost && room.players.length < 4 && (
          <div className="mb-6 rounded-xl border border-violet-900/40 bg-violet-950/20 p-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-violet-neon">
                  <Bot className="h-4 w-4" />
                  ADD AUTONOMOUS AI OPPONENT
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Populate empty seats with server-authoritative AI personas.
                </p>
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <select
                  value={selectedDifficulty}
                  onChange={(e) => setSelectedDifficulty(e.target.value as AIDifficulty)}
                  className="rounded-lg border border-slate-700 bg-stadium-darkest px-3 py-1.5 text-xs text-white focus:border-violet-neon focus:outline-none"
                >
                  <option value="ROOKIE">Rookie (Probabilistic)</option>
                  <option value="PRO">Pro (Value Model)</option>
                  <option value="LEGEND">Legend (Optimal Stopping)</option>
                </select>

                <button
                  onClick={handleAddAI}
                  disabled={isLoading}
                  className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3.5 py-1.5 text-xs font-bold text-white transition hover:bg-violet-500 shadow-violet-glow"
                >
                  <Plus className="h-3.5 w-3.5" />
                  ADD BOT
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Bottom Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-stadium-border/60 pt-6">
          <button
            onClick={leaveRoom}
            className="w-full sm:w-auto rounded-xl border border-slate-700 px-5 py-2.5 text-xs font-mono font-semibold text-slate-300 hover:border-red-500 hover:text-red-400 transition"
          >
            EXIT LOBBY
          </button>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            {/* Ready Toggle for Guest / Non-Host */}
            {!isHost && me && (
              <button
                onClick={() => toggleReady(!me.is_ready)}
                className={`w-full sm:w-auto rounded-xl px-6 py-3 font-display font-bold text-xs uppercase tracking-wider transition ${
                  me.is_ready
                    ? "border border-amber-500/40 bg-amber-950/40 text-amber-300 hover:bg-amber-900/50"
                    : "bg-gradient-to-r from-emerald-500 to-cyan-500 text-stadium-darkest shadow-cyan-glow hover:opacity-90"
                }`}
              >
                {me.is_ready ? "SET UNREADY" : "READY UP"}
              </button>
            )}

            {/* Host Start Button */}
            {isHost && (
              <button
                onClick={startGame}
                disabled={!canStart || isLoading}
                className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-neon to-violet-neon px-8 py-3.5 font-display text-sm font-black text-stadium-darkest tracking-wider shadow-cyan-glow transition hover:opacity-90 disabled:opacity-40"
              >
                <Play className="h-4 w-4 fill-current" />
                {isLoading ? "INITIALIZING HISTORICAL SEED..." : "START TOURNAMENT"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
