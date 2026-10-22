import React, { useState, useEffect } from 'react';
import {
  Server,
  Database,
  ShieldCheck,
  RefreshCw,
  Activity,
  Zap,
  Key,
} from 'lucide-react';
import { api } from '../services/api';
import { HealthResponse } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';

export const SettingsPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runDiagnostics = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const data = await api.getHealth();
      const end = performance.now();
      setLatency(Math.round(end - start));
      setHealth(data);
      setLastChecked(new Date());
    } catch (err: any) {
      const end = performance.now();
      setLatency(Math.round(end - start));
      setError(err.message || 'Health check failed');
      setHealth(null);
      setLastChecked(new Date());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runDiagnostics();
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Diagnostics Hero */}
      <div className="gauge-card p-6 border-indigo-500/20 bg-gradient-to-br from-[#111827] to-[#161F30]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">System Health & Live Connectivity</h2>
              <p className="text-xs text-slate-400">Real-time status check against the Gauge backend and database</p>
            </div>
          </div>

          <button
            onClick={runDiagnostics}
            disabled={loading}
            className="gauge-btn-primary flex-shrink-0"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Run Health Check</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-5 border-t border-slate-800">
          <div className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800">
            <span className="text-[11px] uppercase tracking-wider text-slate-500 font-mono">Backend Status</span>
            <div className="mt-1 flex items-center gap-2">
              {health ? (
                <StatusBadge status={health.status} />
              ) : (
                <span className="text-xs text-rose-400 font-mono">Unreachable</span>
              )}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800">
            <span className="text-[11px] uppercase tracking-wider text-slate-500 font-mono">PostgreSQL Status</span>
            <div className="mt-1 flex items-center gap-2">
              {health?.database?.connected ? (
                <StatusBadge status="completed" />
              ) : (
                <StatusBadge status="unhealthy" />
              )}
              <span className="text-xs text-slate-300 font-mono">
                {health?.database?.connected ? 'Connected' : 'Offline'}
              </span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800">
            <span className="text-[11px] uppercase tracking-wider text-slate-500 font-mono">API Round-Trip Latency</span>
            <div className="mt-1 flex items-baseline gap-1 font-mono text-sm font-bold text-white">
              {latency !== null ? `${latency} ms` : '—'}
              <span className="text-[10px] text-slate-500 font-normal">HTTP ping</span>
            </div>
          </div>
        </div>
      </div>

      {/* Diagnostics Response Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Application Configuration Info */}
        <div className="gauge-card p-6 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Server className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white">Application Metadata</h3>
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Application Name</span>
              <span className="text-white font-semibold">Gauge</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Service Identifier</span>
              <span className="text-indigo-300">{health?.service || 'gauge-api'}</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Build Version</span>
              <span className="text-white">{health?.version || '0.1.0-day1'}</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Environment</span>
              <span className="text-slate-300 capitalize">{health?.environment || 'development'}</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">API Endpoint Base</span>
              <span className="text-slate-300 truncate max-w-[200px]">{api.getBaseUrl()}</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-slate-400">Last Telemetry Ping</span>
              <span className="text-slate-400">
                {lastChecked ? lastChecked.toLocaleTimeString() : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Database & Infrastructure Engine */}
        <div className="gauge-card p-6 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Database className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Database & Migration Engine</h3>
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Target Store</span>
              <span className="text-white">PostgreSQL 15+</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">ORM Framework</span>
              <span className="text-cyan-300">SQLAlchemy 2.x (Sync Sessions)</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Migrations Engine</span>
              <span className="text-white">Alembic (Initial Revision Active)</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Dialect Detected</span>
              <span className="text-slate-300">{health?.database?.dialect || 'postgresql'}</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-slate-400">Connection Message</span>
              <span className="text-slate-400 truncate max-w-[200px]" title={health?.database?.message}>
                {health?.database?.message || (error ? error : 'Disconnected')}
              </span>
            </div>
          </div>
        </div>

        {/* Real LLM Provider Integration */}
        <div className="gauge-card p-6 space-y-4 md:col-span-2">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Zap className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">Real LLM Provider & Adapter Engine</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="space-y-3">
              <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Configured Real Provider</span>
                <span className="text-white uppercase font-bold">{health?.llm_provider?.provider || 'groq'}</span>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Default Model ID</span>
                <span className="text-indigo-300 font-semibold">{health?.llm_provider?.model || 'openai/gpt-oss-20b'}</span>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <span className="text-slate-400">Default Execution Mode</span>
                <span className="text-slate-300 capitalize">{health?.llm_provider?.default_execution_mode || 'auto'}</span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">API Key Detection</span>
                {health?.llm_provider?.api_key_configured ? (
                  <span className="px-2 py-0.5 rounded text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold flex items-center gap-1">
                    <Key className="w-3 h-3" />
                    Configured (Environment)
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[11px] bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold flex items-center gap-1">
                    <Key className="w-3 h-3" />
                    Unset (Mock Mode Active)
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Telemetry Capture</span>
                <span className="text-emerald-400">Tokens, Wall-Clock Latency & Cost</span>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <span className="text-slate-400">Error Handling</span>
                <span className="text-slate-300">Strict Error Recording (No Silent Fallback)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Security & Credentials Safety Note */}
      <div className="gauge-card p-5 border-emerald-500/20 bg-emerald-500/5 flex items-start gap-3">
        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 mt-0.5">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-white">Security & Environment Isolation</h4>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
            Database credentials, passwords, and secret keys are isolated in local <code className="font-mono bg-slate-900 px-1 py-0.5 rounded text-slate-300">.env</code> files and are never exposed over public API endpoints or frontend clients.
          </p>
        </div>
      </div>
    </div>
  );
};
