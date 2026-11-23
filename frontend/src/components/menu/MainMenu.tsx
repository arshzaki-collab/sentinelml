import React, { useState } from "react";
import {
  Award,
  Bot,
  DollarSign,
  Globe,
  HelpCircle,
  Shield,
  Sparkles,
  Users,
} from "lucide-react";
import { InstructionsModal } from "./InstructionsModal";

interface MainMenuProps {
  onSelectMode: (mode: "single" | "multiplayer") => void;
}

export const MainMenu: React.FC<MainMenuProps> = ({ onSelectMode }) => {
  const [showInstructions, setShowInstructions] = useState(false);

  return (
    <div className="relative min-h-[calc(100vh-65px)] flex flex-col items-center justify-center p-4 sm:p-6 tactical-grid overflow-hidden">
      {/* Stadium Ambient Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-gradient-to-r from-cyan-500/10 via-violet-500/10 to-transparent blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-4xl text-center space-y-8">
        {/* Title & Tagline */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-4 py-1.5 text-xs font-mono font-bold text-cyan-neon shadow-cyan-glow">
            <Sparkles className="h-3.5 w-3.5" />
            THE DECADE FOOTBALL FINANCIAL SIMULATION (2016–2026)
          </div>

          <h1 className="font-display text-4xl sm:text-6xl md:text-7xl font-black text-white tracking-tight">
            BLIND BILLION <span className="bg-gradient-to-r from-cyan-neon via-sky-300 to-violet-neon bg-clip-text text-transparent">2.0</span>
          </h1>

          <p className="mx-auto max-w-2xl text-sm sm:text-base text-slate-300 leading-relaxed">
            Manage a starting budget of <strong className="text-emerald-400 font-mono">$1,000,000,000</strong>. Scout confidential anonymous candidate dossiers with 3 statistical hints across 7 tactical positions. Rebalance in 3 transfer windows, and see who built Europe&apos;s most valuable squad at the 2026 reveal.
          </p>
        </div>

        {/* Big Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-lg mx-auto">
          <button
            onClick={() => onSelectMode("single")}
            className="w-full sm:w-auto flex-1 flex items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-cyan-neon to-sky-400 px-6 py-4 font-display text-sm font-black text-stadium-darkest tracking-wider shadow-cyan-glow transition hover:scale-105 active:scale-95"
          >
            <Bot className="h-5 w-5 fill-current" />
            SINGLE PLAYER (VS AI)
          </button>

          <button
            onClick={() => onSelectMode("multiplayer")}
            className="w-full sm:w-auto flex-1 flex items-center justify-center gap-3 rounded-2xl border-2 border-violet-neon/80 bg-stadium-surface px-6 py-4 font-display text-sm font-black text-violet-neon tracking-wider shadow-violet-glow transition hover:bg-violet-950/40 hover:scale-105 active:scale-95"
          >
            <Globe className="h-5 w-5" />
            MULTIPLAYER (ONLINE)
          </button>
        </div>

        {/* Instructions & Help */}
        <div>
          <button
            onClick={() => setShowInstructions(true)}
            className="inline-flex items-center gap-2 text-xs font-mono font-semibold text-slate-400 hover:text-cyan-neon transition p-2"
          >
            <HelpCircle className="h-4 w-4" />
            HOW TO PLAY &amp; TOURNAMENT RULES
          </button>
        </div>

        {/* 4 Feature Highlights Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto pt-4 text-left">
          <div className="rounded-xl border border-stadium-border/70 bg-stadium-surface/80 p-3.5 backdrop-blur-sm">
            <DollarSign className="h-5 w-5 text-emerald-400 mb-1" />
            <div className="font-display font-bold text-xs text-white">$1B Budget</div>
            <div className="text-[10px] text-slate-400">Strict server solvency</div>
          </div>

          <div className="rounded-xl border border-stadium-border/70 bg-stadium-surface/80 p-3.5 backdrop-blur-sm">
            <Shield className="h-5 w-5 text-cyan-neon mb-1" />
            <div className="font-display font-bold text-xs text-white">Blind Scouting</div>
            <div className="text-[10px] text-slate-400">3 hints, zero leakage</div>
          </div>

          <div className="rounded-xl border border-stadium-border/70 bg-stadium-surface/80 p-3.5 backdrop-blur-sm">
            <Users className="h-5 w-5 text-violet-neon mb-1" />
            <div className="font-display font-bold text-xs text-white">2–4 Players</div>
            <div className="text-[10px] text-slate-400">Realtime synchronized</div>
          </div>

          <div className="rounded-xl border border-stadium-border/70 bg-stadium-surface/80 p-3.5 backdrop-blur-sm">
            <Award className="h-5 w-5 text-gold-glow mb-1" />
            <div className="font-display font-bold text-xs text-white">Real Valuations</div>
            <div className="text-[10px] text-slate-400">2016–2026 historical</div>
          </div>
        </div>
      </div>

      <InstructionsModal
        isOpen={showInstructions}
        onClose={() => setShowInstructions(false)}
      />
    </div>
  );
};
