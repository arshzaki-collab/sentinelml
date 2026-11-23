import React, { useState } from "react";
import { Volume2, VolumeX, Copy, Check, LogOut, Wifi, WifiOff } from "lucide-react";
import { useGame } from "../../context/GameContext";
import { soundManager } from "../../services/sound";

export const Header: React.FC = () => {
  const { room, roomCode, leaveRoom, isConnected } = useGame();
  const [isMuted, setIsMuted] = useState(soundManager.getMuted());
  const [copied, setCopied] = useState(false);

  const toggleSound = () => {
    const next = soundManager.toggleMute();
    setIsMuted(next);
  };

  const copyCode = () => {
    if (!roomCode) return;
    navigator.clipboard.writeText(roomCode);
    soundManager.playClick();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header className="relative z-30 w-full border-b border-stadium-border/60 bg-stadium-darkest/90 backdrop-blur-md px-4 py-3 sm:px-6">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        {/* Logo & Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-neon to-violet-neon p-[2px] shadow-cyan-glow">
            <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-stadium-surface font-display font-black text-cyan-neon text-sm">
              BB
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display text-lg font-black tracking-wider text-white">
                BLIND BILLION
              </span>
              <span className="rounded bg-gradient-to-r from-cyan-neon to-violet-neon px-1.5 py-0.5 text-[10px] font-black uppercase text-stadium-darkest">
                2.0
              </span>
            </div>
            <p className="hidden text-[11px] font-medium text-slate-400 sm:block">
              Historical Football Financial Strategy
            </p>
          </div>
        </div>

        {/* Room Info & Controls */}
        <div className="flex items-center gap-3">
          {roomCode && (
            <button
              onClick={copyCode}
              title="Click to copy Room Code"
              className="flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-950/40 px-3 py-1.5 text-xs font-mono font-semibold text-cyan-300 transition hover:border-cyan-400 hover:bg-cyan-900/50"
            >
              <span className="text-slate-400">ROOM:</span>
              <span className="font-bold text-white tracking-widest">{roomCode}</span>
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-cyan-400" />}
            </button>
          )}

          {/* Connection status indicator */}
          {room && (
            <div
              className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${
                isConnected
                  ? "bg-emerald-950/40 text-emerald-300 border border-emerald-500/30"
                  : "bg-amber-950/40 text-amber-300 border border-amber-500/30"
              }`}
            >
              {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              <span className="hidden sm:inline">{isConnected ? "Live" : "Syncing"}</span>
            </div>
          )}

          {/* Sound Toggle */}
          <button
            onClick={toggleSound}
            aria-label={isMuted ? "Unmute audio" : "Mute audio"}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700/60 bg-stadium-surface text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            {isMuted ? <VolumeX className="h-4 w-4 text-slate-500" /> : <Volume2 className="h-4 w-4 text-cyan-neon" />}
          </button>

          {/* Leave / Exit Button */}
          {room && (
            <button
              onClick={leaveRoom}
              title="Leave Room"
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-red-900/40 bg-red-950/20 text-red-300 transition hover:border-red-500 hover:bg-red-900/40 hover:text-white"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
