import React from "react";
import { AlertCircle, CheckCircle2, X } from "lucide-react";
import { useGame } from "../../context/GameContext";

export const NotificationToast: React.FC = () => {
  const { error, notification, dismissError, dismissNotification } = useGame();

  if (!error && !notification) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-md w-full px-4">
      {error && (
        <div className="flex items-start justify-between gap-3 rounded-xl border border-red-500/40 bg-red-950/90 p-4 text-red-200 shadow-xl backdrop-blur-md">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
            <div className="text-sm font-medium">{error}</div>
          </div>
          <button
            onClick={dismissError}
            className="text-red-400 hover:text-white transition p-0.5"
            aria-label="Dismiss error"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {notification && (
        <div className="flex items-start justify-between gap-3 rounded-xl border border-cyan-500/40 bg-cyan-950/90 p-4 text-cyan-200 shadow-xl backdrop-blur-md">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-5 w-5 text-cyan-400 shrink-0 mt-0.5" />
            <div className="text-sm font-medium">{notification}</div>
          </div>
          <button
            onClick={dismissNotification}
            className="text-cyan-400 hover:text-white transition p-0.5"
            aria-label="Dismiss notification"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
};
