import React from 'react';
import { RefreshCw, Database } from 'lucide-react';

interface DatabaseStatusBannerProps {
  connected: boolean;
  message: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export const DatabaseStatusBanner: React.FC<DatabaseStatusBannerProps> = ({
  connected,
  message,
  onRetry,
  isRetrying = false,
}) => {
  if (connected) return null;

  return (
    <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 mt-0.5">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-amber-300 text-sm">Database Offline or Disconnected</h4>
              <span className="text-[10px] font-mono uppercase bg-amber-500/30 px-2 py-0.5 rounded text-amber-200">
                Degraded Mode
              </span>
            </div>
            <p className="text-xs text-amber-300/80 mt-1">
              {message || "The backend cannot establish a connection to PostgreSQL. Displaying zero counts."}
            </p>
            <p className="text-[11px] text-amber-400/60 mt-1.5">
              Start PostgreSQL with <code className="font-mono bg-amber-950/60 px-1 py-0.5 rounded">docker compose up -d postgres</code> or configure <code className="font-mono bg-amber-950/60 px-1 py-0.5 rounded">.env</code>.
            </p>
          </div>
        </div>

        {onRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-medium border border-amber-500/30 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
            <span>Check Connection</span>
          </button>
        )}
      </div>
    </div>
  );
};
