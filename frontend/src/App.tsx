import React, { useState } from "react";
import { GameProvider, useGame } from "./context/GameContext";
import { Header } from "./components/common/Header";
import { NotificationToast } from "./components/common/NotificationToast";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { MainMenu } from "./components/menu/MainMenu";
import { GameSetup } from "./components/setup/GameSetup";
import { MultiplayerLobby } from "./components/lobby/MultiplayerLobby";
import { StadiumDashboard } from "./components/dashboard/StadiumDashboard";

const GameViewRouter: React.FC = () => {
  const { room } = useGame();
  const [setupMode, setSetupMode] = useState<"single" | "multiplayer" | null>(null);

  // If not currently in a room:
  if (!room) {
    if (setupMode) {
      return (
        <GameSetup
          initialMode={setupMode}
          onBack={() => setSetupMode(null)}
        />
      );
    }
    return <MainMenu onSelectMode={(mode) => setSetupMode(mode)} />;
  }

  // If in a room lobby:
  if (room.status === "LOBBY") {
    return <MultiplayerLobby />;
  }

  // Active game or final settlement:
  return <StadiumDashboard />;
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <GameProvider>
        <div className="min-h-screen flex flex-col bg-stadium-darkest text-slate-100 font-sans selection:bg-cyan-500/30 selection:text-cyan-300">
          <Header />
          <main className="flex-1 flex flex-col">
            <ErrorBoundary>
              <GameViewRouter />
            </ErrorBoundary>
          </main>
          <NotificationToast />
        </div>
      </GameProvider>
    </ErrorBoundary>
  );
};

export default App;
