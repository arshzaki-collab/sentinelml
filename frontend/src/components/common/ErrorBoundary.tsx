import { Component, ErrorInfo, ReactNode } from "react";
import { AlertOctagon, Home, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("ErrorBoundary caught an unhandled React error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  private handleHome = (): void => {
    sessionStorage.removeItem("bb_session_token");
    sessionStorage.removeItem("bb_player_id");
    sessionStorage.removeItem("bb_room_code");
    window.location.href = "/";
  };

  public render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-stadium-darkest text-slate-100 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-red-500/40 bg-stadium-surface/90 p-6 sm:p-8 backdrop-blur-xl shadow-2xl text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-red-500/50 bg-red-950/60 text-red-400">
              <AlertOctagon className="h-7 w-7" />
            </div>
            <h1 className="font-display text-xl font-bold text-white mb-2">
              Tactical Interface Failure
            </h1>
            <p className="text-xs text-slate-300 mb-4">
              An unexpected error occurred while rendering the game interface.
            </p>
            {this.state.error && (
              <div className="mb-6 rounded-lg bg-stadium-darkest/90 border border-red-900/40 p-3 text-left font-mono text-xs text-red-300 overflow-x-auto max-h-36">
                {this.state.error.message || String(this.state.error)}
              </div>
            )}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={this.handleReset}
                className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-xl bg-cyan-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-cyan-500"
              >
                <RefreshCw className="h-4 w-4" />
                TRY AGAIN
              </button>
              <button
                onClick={this.handleHome}
                className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-stadium-darkest px-5 py-2.5 text-xs font-bold text-slate-300 transition hover:border-slate-500 hover:text-white"
              >
                <Home className="h-4 w-4" />
                MAIN MENU
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
