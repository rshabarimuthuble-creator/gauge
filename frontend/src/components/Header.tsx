import React from 'react';
import { RefreshCw, ExternalLink, Activity, Database } from 'lucide-react';
import { HealthResponse } from '../types/api';

interface HeaderProps {
  title: string;
  description?: string;
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
  actions?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  description,
  health,
  loading,
  onRefresh,
  actions,
}) => {
  const isHealthy = health?.status === 'ok';
  const isDegraded = health?.status === 'degraded';
  const isDbConnected = health?.database?.connected;

  return (
    <header className="h-16 bg-[#111827]/80 backdrop-blur-md border-b border-[#2A374A] px-8 flex items-center justify-between sticky top-0 z-30">
      <div>
        <h1 className="text-lg font-semibold text-white tracking-tight flex items-center gap-2">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-slate-400 font-normal">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Backend & DB Status Pills */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#161F30] border border-[#2A374A] text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">API:</span>
            <span className={isHealthy ? 'text-emerald-400' : isDegraded ? 'text-amber-400' : 'text-rose-400'}>
              {health?.status || 'offline'}
            </span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">DB:</span>
            <span className={isDbConnected ? 'text-emerald-400' : 'text-rose-400'}>
              {isDbConnected ? 'connected' : 'offline'}
            </span>
          </div>
        </div>

        {/* Refresh API Data */}
        <button
          onClick={onRefresh}
          disabled={loading}
          title="Refresh Data from API"
          className="p-2 rounded-lg bg-[#161F30] hover:bg-[#1E293B] text-slate-300 hover:text-white border border-[#2A374A] transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
        </button>

        {/* API Docs Link */}
        <a
          href="http://localhost:8001/api/v1/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#161F30] hover:bg-[#1E293B] text-slate-300 hover:text-white border border-[#2A374A] text-xs font-medium transition-colors"
        >
          <span>FastAPI Docs</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>

        {/* Page Actions (e.g. Create Button) */}
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
};
