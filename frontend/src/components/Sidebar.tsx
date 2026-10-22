import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  Layers,
  PlaySquare,
  GitCompare,
  Settings as SettingsIcon,
  Gauge,
  Activity,
  TerminalSquare,
} from 'lucide-react';
import { HealthResponse } from '../types/api';

interface SidebarProps {
  health: HealthResponse | null;
  loading: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ health, loading }) => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/datasets', label: 'Datasets', icon: Database },
    { to: '/versions', label: 'Agent Versions', icon: Layers },
    { to: '/evaluations', label: 'Evaluations', icon: PlaySquare },
    { to: '/comparisons', label: 'Comparisons', icon: GitCompare },
    { to: '/settings', label: 'Settings', icon: SettingsIcon },
  ];

  const isDbConnected = health?.database?.connected ?? false;

  return (
    <aside className="w-64 bg-[#111827] border-r border-[#2A374A] flex flex-col h-screen flex-shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-[#2A374A] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 p-0.5 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-[#111827] rounded-[10px] flex items-center justify-center">
              <Gauge className="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold tracking-tight text-white text-base">GAUGE</span>
              <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                DAY 3
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Agent Evaluation & Benchmarking</p>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Platform
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-[#1E293B]/70'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Database & System Connectivity Status */}
      <div className="p-4 border-t border-[#2A374A] bg-[#0B0F17]/50">
        <div className="p-3 rounded-lg bg-[#111827] border border-[#2A374A]/80 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-slate-500" />
              API Service
            </span>
            <span className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  loading
                    ? 'bg-amber-400 animate-pulse'
                    : health?.status === 'ok'
                    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                    : health?.status === 'degraded'
                    ? 'bg-amber-400'
                    : 'bg-rose-400'
                }`}
              />
              <span className="text-[11px] font-mono text-slate-300 capitalize">
                {loading ? 'Checking' : health?.status || 'Offline'}
              </span>
            </span>
          </div>

          <div className="flex items-center justify-between text-xs pt-1.5 border-t border-slate-800">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-slate-500" />
              PostgreSQL
            </span>
            <span className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  loading
                    ? 'bg-amber-400 animate-pulse'
                    : isDbConnected
                    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                    : 'bg-rose-400'
                }`}
              />
              <span className="text-[11px] font-mono text-slate-300">
                {isDbConnected ? 'Connected' : 'Offline'}
              </span>
            </span>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 px-1 font-mono">
          <span>v0.1.0-day1</span>
          <span className="flex items-center gap-1">
            <TerminalSquare className="w-3 h-3" />
            FastAPI+React
          </span>
        </div>
      </div>
    </aside>
  );
};
