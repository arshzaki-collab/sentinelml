import React from "react";
import { Check, RefreshCw, Trophy } from "lucide-react";
import { useGame } from "../../context/GameContext";

interface StepItem {
  index: number;
  year: number;
  type: "BUY" | "TRANSFER" | "SETTLEMENT";
  label: string;
}

const TIMELINE_STEPS: StepItem[] = [
  { index: 0, year: 2016, type: "BUY", label: "ST" },
  { index: 1, year: 2017, type: "BUY", label: "WG" },
  { index: 2, year: 2018, type: "BUY", label: "CM" },
  { index: 3, year: 2019, type: "TRANSFER", label: "Window" },
  { index: 4, year: 2020, type: "BUY", label: "CB" },
  { index: 5, year: 2021, type: "BUY", label: "CM" },
  { index: 6, year: 2022, type: "TRANSFER", label: "Window" },
  { index: 7, year: 2023, type: "BUY", label: "CB" },
  { index: 8, year: 2024, type: "BUY", label: "GK" },
  { index: 9, year: 2025, type: "TRANSFER", label: "Window" },
  { index: 10, year: 2026, type: "SETTLEMENT", label: "Reveal" },
];

export const TimelineProgress: React.FC = () => {
  const { room } = useGame();
  if (!room) return null;

  const currentStep = room.timeline_step_index;

  return (
    <div className="w-full overflow-x-auto py-3 px-2">
      <div className="flex items-center justify-between min-w-[700px] sm:min-w-0 sm:w-full relative">
        {/* Connecting Track Line */}
        <div className="absolute left-6 right-6 top-1/2 -translate-y-1/2 h-[3px] bg-slate-800 -z-0" />

        {TIMELINE_STEPS.map((step) => {
          const isPassed = step.index < currentStep;
          const isCurrent = step.index === currentStep;

          let badgeColor = "border-slate-800 bg-stadium-surface text-slate-500";
          let textColor = "text-slate-500";

          if (isPassed) {
            badgeColor = "border-emerald-500/50 bg-emerald-950/80 text-emerald-400";
            textColor = "text-emerald-400";
          } else if (isCurrent) {
            if (step.type === "TRANSFER") {
              badgeColor = "border-violet-neon bg-violet-950 text-violet-neon shadow-violet-glow scale-110";
              textColor = "text-violet-neon";
            } else if (step.type === "SETTLEMENT") {
              badgeColor = "border-gold-glow bg-amber-950 text-gold-glow shadow-gold-glow scale-110";
              textColor = "text-gold-glow";
            } else {
              badgeColor = "border-cyan-neon bg-cyan-950 text-cyan-neon shadow-cyan-glow scale-110";
              textColor = "text-cyan-neon";
            }
          }

          return (
            <div key={step.index} className="flex flex-col items-center relative z-10">
              <div
                className={`flex h-8 w-8 sm:h-9 sm:w-9 items-center justify-center rounded-xl border-2 text-xs font-mono font-bold transition-all duration-300 ${badgeColor}`}
              >
                {isPassed ? (
                  <Check className="h-4 w-4" />
                ) : step.type === "TRANSFER" ? (
                  <RefreshCw className="h-3.5 w-3.5" />
                ) : step.type === "SETTLEMENT" ? (
                  <Trophy className="h-3.5 w-3.5" />
                ) : (
                  <span>{step.label}</span>
                )}
              </div>
              <div className="mt-1.5 flex flex-col items-center">
                <span className={`text-[11px] font-mono font-bold ${textColor}`}>
                  {step.year}
                </span>
                <span className="text-[9px] uppercase tracking-wider text-slate-500">
                  {step.type === "TRANSFER" ? "Window" : step.type === "SETTLEMENT" ? "Settlement" : `Slot ${step.label}`}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
