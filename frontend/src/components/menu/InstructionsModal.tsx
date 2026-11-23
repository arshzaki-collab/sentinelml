import React from "react";
import { X, DollarSign, Users, RefreshCw, Trophy, ShieldAlert, Sparkles } from "lucide-react";

interface InstructionsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InstructionsModal: React.FC<InstructionsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rules-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-stadium-border bg-stadium-surface p-6 sm:p-8 text-slate-200 shadow-2xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white transition p-1"
          aria-label="Close rules dialog"
        >
          <X className="h-6 w-6" />
        </button>

        {/* Title */}
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-neon">
            <Sparkles className="h-6 w-6" />
          </div>
          <div>
            <h2 className="font-display text-2xl font-black text-white tracking-wide">
              HOW TO PLAY BLIND BILLION 2.0
            </h2>
            <p className="text-xs text-slate-400">
              The Server-Authoritative Historical Football Financial Strategy Simulation
            </p>
          </div>
        </div>

        {/* Content sections */}
        <div className="space-y-6 text-sm">
          {/* Section 1 */}
          <div className="rounded-xl border border-stadium-border/60 bg-stadium-card/60 p-4">
            <div className="flex items-center gap-2 font-display font-bold text-cyan-neon text-base mb-2">
              <DollarSign className="h-5 w-5 text-emerald-400" />
              $1,000,000,000 Starting Capital
            </div>
            <p className="text-slate-300 leading-relaxed">
              You begin in 2016 with a starting transfer budget of exactly $1 Billion USD. Every purchase permanently deducts cash from your club reserves. Cash never earns interest, so investing astutely in players who appreciate over the decade is key to winning.
            </p>
          </div>

          {/* Section 2 */}
          <div className="rounded-xl border border-stadium-border/60 bg-stadium-card/60 p-4">
            <div className="flex items-center gap-2 font-display font-bold text-violet-neon text-base mb-2">
              <Users className="h-5 w-5 text-violet-400" />
              7 Required Squad Slots (2016–2026)
            </div>
            <p className="text-slate-300 mb-3 leading-relaxed">
              You must construct a complete 7-man tactical spine following the strict chronological schedule:
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
              <span className="p-2 rounded bg-stadium-darkest border border-slate-700/50">2016: 1. ST (Striker)</span>
              <span className="p-2 rounded bg-stadium-darkest border border-slate-700/50">2017: 2. WG (Winger)</span>
              <span className="p-2 rounded bg-stadium-darkest border border-slate-700/50">2018: 3. CM (Midfielder)</span>
              <span className="p-2 rounded bg-stadium-darkest border border-slate-700/50">2020: 4. CB (Defender)</span>
              <span className="p-2 rounded bg-stadium-darkest border border-slate-700/50">2021: 5. CM (Midfielder)</span>
              <span className="p-2 rounded bg-stadium-darkest border border-slate-700/50">2023: 6. CB (Defender)</span>
              <span className="p-2 rounded bg-stadium-darkest border border-slate-700/50">2024: 7. GK (Goalkeeper)</span>
            </div>
          </div>

          {/* Section 3 */}
          <div className="rounded-xl border border-stadium-border/60 bg-stadium-card/60 p-4">
            <div className="flex items-center gap-2 font-display font-bold text-amber-400 text-base mb-2">
              <ShieldAlert className="h-5 w-5 text-amber-400" />
              Blind Scouting & 3 Compulsory Hints
            </div>
            <p className="text-slate-300 leading-relaxed mb-2">
              Real player names, faces, clubs, and IDs remain completely secret until 2026! For each slot, you evaluate exactly 4 anonymous candidate cards with historical market prices and 3 statistical hints:
            </p>
            <ul className="list-disc list-inside text-xs space-y-1 text-slate-300">
              <li><strong>ST & WG:</strong> Goals compulsory + 2 of (Age, Assists, Domestic League, UCL Goals)</li>
              <li><strong>CM:</strong> Assists compulsory + 2 of (Age, Goals, Cards, Domestic League)</li>
              <li><strong>CB:</strong> Clean Sheets compulsory + 2 of (Age, Goals, Cards, Domestic League)</li>
              <li><strong>GK:</strong> Fixed 3 hints: Clean Sheets, Age, Domestic League Name</li>
            </ul>
          </div>

          {/* Section 4 */}
          <div className="rounded-xl border border-stadium-border/60 bg-stadium-card/60 p-4">
            <div className="flex items-center gap-2 font-display font-bold text-cyan-neon text-base mb-2">
              <RefreshCw className="h-5 w-5 text-cyan-400" />
              Transfer Windows (2019, 2022, 2025)
            </div>
            <p className="text-slate-300 leading-relaxed">
              During transfer windows, you may choose to sell any player signed in a previous season at their updated historical market valuation. If sold, you MUST sign a replacement immediately from that slot&apos;s original 4-player shortlist. Alternatively, you may choose to PASS.
            </p>
          </div>

          {/* Section 5 */}
          <div className="rounded-xl border border-stadium-border/60 bg-stadium-card/60 p-4">
            <div className="flex items-center gap-2 font-display font-bold text-gold-glow text-base mb-2">
              <Trophy className="h-5 w-5 text-gold-trophy" />
              2026 Settlement & Final Victory
            </div>
            <p className="text-slate-300 leading-relaxed">
              At the 2026 Final Settlement, all player identities are dramatically unmasked! Final Net Worth is calculated as:
            </p>
            <div className="p-3 my-2 text-center rounded bg-stadium-darkest border border-gold-500/30 font-mono text-gold-glow font-bold text-sm">
              FINAL NET WORTH = CASH RESERVES + 2026 SQUAD MARKET VALUE
            </div>
            <p className="text-xs text-slate-400">
              The manager with the highest total net worth wins the Blind Billion 2.0 trophy!
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-xl bg-gradient-to-r from-cyan-neon to-violet-neon px-6 py-2.5 font-display font-bold text-stadium-darkest shadow-cyan-glow transition hover:opacity-90"
          >
            GOT IT, LET&apos;S PLAY
          </button>
        </div>
      </div>
    </div>
  );
};
