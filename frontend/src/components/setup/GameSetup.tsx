import React, { useState } from "react";
import { ArrowLeft, Bot, Globe, User, Users } from "lucide-react";
import { useGame } from "../../context/GameContext";
import { AIDifficulty } from "../../types/game";

interface GameSetupProps {
  initialMode: "single" | "multiplayer";
  onBack: () => void;
}

export const GameSetup: React.FC<GameSetupProps> = ({ initialMode, onBack }) => {
  const { createRoom, joinRoom, startSinglePlayer, isLoading } = useGame();

  const [mode, setMode] = useState<"single" | "multiplayer">(initialMode);
  const [multiSubMode, setMultiSubMode] = useState<"create" | "join">("create");

  // Single Player Form
  const [playerName, setPlayerName] = useState("Chief Scout");
  const [aiDifficulty, setAiDifficulty] = useState<AIDifficulty>("PRO");
  const [aiCount, setAiCount] = useState<number>(2);

  // Multiplayer Form
  const [hostName, setHostName] = useState("Club President");
  const [guestName, setGuestName] = useState("Director of Football");
  const [joinCode, setJoinCode] = useState("");
  const [customSeed, setCustomSeed] = useState("");

  const handleStartSinglePlayer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await startSinglePlayer(playerName.trim() || "Chief Scout", aiDifficulty, aiCount);
    } catch {
      // error handled in context
    }
  };

  const handleCreateMultiplayer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createRoom(hostName.trim() || "Host", customSeed.trim() || undefined);
    } catch {
      // error handled in context
    }
  };

  const handleJoinMultiplayer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    try {
      await joinRoom(joinCode.trim().toUpperCase(), guestName.trim() || "Player");
    } catch {
      // error handled in context
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-65px)] flex flex-col items-center justify-center p-4 sm:p-6 tactical-grid">
      <div className="w-full max-w-xl rounded-2xl border border-stadium-border bg-stadium-surface/90 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
        {/* Back Button */}
        <button
          onClick={onBack}
          className="mb-4 flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-cyan-neon transition"
        >
          <ArrowLeft className="h-4 w-4" />
          BACK TO MENU
        </button>

        {/* Mode Selector Tabs */}
        <div className="mb-6 grid grid-cols-2 gap-2 rounded-xl border border-stadium-border/60 bg-stadium-darkest p-1">
          <button
            onClick={() => setMode("single")}
            className={`flex items-center justify-center gap-2 rounded-lg py-2.5 text-xs sm:text-sm font-display font-bold transition ${
              mode === "single"
                ? "bg-gradient-to-r from-cyan-neon to-violet-neon text-stadium-darkest shadow-cyan-glow"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Bot className="h-4 w-4" />
            SINGLE PLAYER (VS AI)
          </button>
          <button
            onClick={() => setMode("multiplayer")}
            className={`flex items-center justify-center gap-2 rounded-lg py-2.5 text-xs sm:text-sm font-display font-bold transition ${
              mode === "multiplayer"
                ? "bg-gradient-to-r from-cyan-neon to-violet-neon text-stadium-darkest shadow-cyan-glow"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Globe className="h-4 w-4" />
            MULTIPLAYER (ONLINE)
          </button>
        </div>

        {/* Mode 1: Single Player vs AI */}
        {mode === "single" && (
          <form onSubmit={handleStartSinglePlayer} className="space-y-5">
            <div>
              <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                YOUR MANAGER NAME
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  maxLength={30}
                  required
                  className="w-full rounded-xl border border-slate-700/60 bg-stadium-darkest pl-10 pr-4 py-2.5 text-sm text-white focus:border-cyan-neon focus:outline-none focus:ring-1 focus:ring-cyan-neon"
                  placeholder="Enter manager name..."
                />
              </div>
            </div>

            {/* AI Difficulty */}
            <div>
              <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                AI DIFFICULTY
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["ROOKIE", "PRO", "LEGEND"] as AIDifficulty[]).map((diff) => (
                  <button
                    key={diff}
                    type="button"
                    onClick={() => setAiDifficulty(diff)}
                    className={`rounded-xl border p-3 text-center transition ${
                      aiDifficulty === diff
                        ? "border-cyan-neon bg-cyan-950/40 text-cyan-neon shadow-cyan-glow"
                        : "border-slate-800 bg-stadium-darkest text-slate-400 hover:border-slate-700 hover:text-white"
                    }`}
                  >
                    <div className="font-display font-black text-sm">{diff}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {diff === "ROOKIE" && "Heuristic"}
                      {diff === "PRO" && "Value Model"}
                      {diff === "LEGEND" && "Arbitrage"}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* AI Opponent Count */}
            <div>
              <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                AI OPPONENTS COUNT
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[1, 2, 3].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setAiCount(count)}
                    className={`flex items-center justify-center gap-1.5 rounded-xl border py-2.5 text-xs font-bold transition ${
                      aiCount === count
                        ? "border-violet-neon bg-violet-950/40 text-violet-neon shadow-violet-glow"
                        : "border-slate-800 bg-stadium-darkest text-slate-400 hover:border-slate-700 hover:text-white"
                    }`}
                  >
                    <Users className="h-3.5 w-3.5" />
                    {count} {count === 1 ? "BOT" : "BOTS"}
                  </button>
                ))}
              </div>
            </div>

            {/* Summary Box */}
            <div className="rounded-xl border border-stadium-border/60 bg-stadium-card/60 p-4 text-xs space-y-1.5 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-400">Total Participants:</span>
                <span className="font-mono font-bold text-white">
                  1 Human + {aiCount} AI ({1 + aiCount} Total)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Starting Budget:</span>
                <span className="font-mono font-bold text-emerald-400">$1,000,000,000</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Timeline:</span>
                <span className="font-mono font-bold text-cyan-300">2016 – 2026 (7 Slots, 3 Windows)</span>
              </div>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-xl bg-gradient-to-r from-cyan-neon to-violet-neon py-3.5 font-display text-sm font-black text-stadium-darkest tracking-wider shadow-cyan-glow transition hover:opacity-90 disabled:opacity-50"
            >
              {isLoading ? "INITIALIZING HISTORICAL DUCKDB CACHE..." : "START SINGLE-PLAYER MATCH"}
            </button>
          </form>
        )}

        {/* Mode 2: Multiplayer */}
        {mode === "multiplayer" && (
          <div className="space-y-5">
            {/* Sub-mode tabs */}
            <div className="grid grid-cols-2 gap-2 border-b border-stadium-border/60 pb-3">
              <button
                type="button"
                onClick={() => setMultiSubMode("create")}
                className={`py-1.5 text-xs font-mono font-bold transition ${
                  multiSubMode === "create" ? "text-cyan-neon border-b-2 border-cyan-neon" : "text-slate-400 hover:text-white"
                }`}
              >
                CREATE NEW ROOM
              </button>
              <button
                type="button"
                onClick={() => setMultiSubMode("join")}
                className={`py-1.5 text-xs font-mono font-bold transition ${
                  multiSubMode === "join" ? "text-cyan-neon border-b-2 border-cyan-neon" : "text-slate-400 hover:text-white"
                }`}
              >
                JOIN EXISTING ROOM
              </button>
            </div>

            {multiSubMode === "create" ? (
              <form onSubmit={handleCreateMultiplayer} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                    HOST DISPLAY NAME
                  </label>
                  <input
                    type="text"
                    value={hostName}
                    onChange={(e) => setHostName(e.target.value)}
                    maxLength={30}
                    required
                    className="w-full rounded-xl border border-slate-700/60 bg-stadium-darkest px-4 py-2.5 text-sm text-white focus:border-cyan-neon focus:outline-none focus:ring-1 focus:ring-cyan-neon"
                    placeholder="Enter host name..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                    OPTIONAL ROOM SEED
                  </label>
                  <input
                    type="text"
                    value={customSeed}
                    onChange={(e) => setCustomSeed(e.target.value)}
                    maxLength={32}
                    className="w-full rounded-xl border border-slate-700/60 bg-stadium-darkest px-4 py-2.5 text-sm text-white focus:border-cyan-neon focus:outline-none focus:ring-1 focus:ring-cyan-neon font-mono"
                    placeholder="Leave blank for random seed..."
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Sharing the same seed produces identical shortlist candidates across rooms.
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full rounded-xl bg-gradient-to-r from-cyan-neon to-violet-neon py-3.5 font-display text-sm font-black text-stadium-darkest tracking-wider shadow-cyan-glow transition hover:opacity-90 disabled:opacity-50"
                >
                  {isLoading ? "CREATING ROOM..." : "CREATE PRIVATE ROOM (LOBBY)"}
                </button>
              </form>
            ) : (
              <form onSubmit={handleJoinMultiplayer} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                    4-CHARACTER ROOM CODE
                  </label>
                  <input
                    type="text"
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value.toUpperCase().slice(0, 4))}
                    maxLength={4}
                    required
                    className="w-full rounded-xl border border-cyan-500/40 bg-stadium-darkest px-4 py-3 text-center text-2xl font-mono font-black tracking-widest text-cyan-neon uppercase focus:border-cyan-neon focus:outline-none focus:ring-2 focus:ring-cyan-neon/30"
                    placeholder="e.g. 7X9K"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                    YOUR PLAYER NAME
                  </label>
                  <input
                    type="text"
                    value={guestName}
                    onChange={(e) => setGuestName(e.target.value)}
                    maxLength={30}
                    required
                    className="w-full rounded-xl border border-slate-700/60 bg-stadium-darkest px-4 py-2.5 text-sm text-white focus:border-cyan-neon focus:outline-none focus:ring-1 focus:ring-cyan-neon"
                    placeholder="Enter your name..."
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading || joinCode.length !== 4}
                  className="w-full rounded-xl bg-gradient-to-r from-cyan-neon to-violet-neon py-3.5 font-display text-sm font-black text-stadium-darkest tracking-wider shadow-cyan-glow transition hover:opacity-90 disabled:opacity-50"
                >
                  {isLoading ? "CONNECTING..." : "ENTER LOBBY"}
                </button>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
