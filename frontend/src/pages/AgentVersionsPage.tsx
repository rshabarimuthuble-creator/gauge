import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Layers,
  Plus,
  Search,
  Calendar,
  Cpu,
  Terminal,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';
import { api } from '../services/api';
import { AgentVersion, HealthResponse } from '../types/api';
import { EmptyState } from '../components/EmptyState';
import { CreateAgentVersionModal } from '../components/CreateAgentVersionModal';

export const AgentVersionsPage: React.FC = () => {
  const { refreshTrigger } = useOutletContext<{ refreshTrigger: number; health: HealthResponse | null }>();

  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchVersions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAgentVersions();
      setVersions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch agent versions from backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions, refreshTrigger]);

  const handleCopy = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredVersions = versions.filter((v) =>
    v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.version.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.model_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.model_provider.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Page Actions Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search agent versions by model, tag, or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="gauge-input pl-10"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => setIsModalOpen(true)}
            className="gauge-btn-primary w-full sm:w-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Register Version</span>
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Failed to load agent versions</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="gauge-card p-5 space-y-3 animate-pulse">
              <div className="h-5 bg-slate-800 rounded w-1/2" />
              <div className="h-4 bg-slate-800 rounded w-3/4" />
              <div className="h-4 bg-slate-800 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : versions.length === 0 ? (
        <EmptyState
          icon={<Layers className="w-6 h-6" />}
          title="No Agent Versions Registered Yet"
          description="Register an agent snapshot with its model provider, model name, and prompt template to track version-over-version performance."
          actionLabel="Register First Version"
          onAction={() => setIsModalOpen(true)}
        />
      ) : filteredVersions.length === 0 ? (
        <div className="gauge-card p-8 text-center text-slate-400 text-sm">
          No agent versions match your search query "{searchQuery}".
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredVersions.map((item) => (
            <div
              key={item.id}
              className="gauge-card p-5 gauge-card-hover flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      <Cpu className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      {item.version}
                    </span>
                  </div>
                  <button
                    onClick={() => handleCopy(item.id)}
                    title="Copy Version ID"
                    className="text-slate-500 hover:text-slate-300 p-1 rounded hover:bg-slate-800 transition-colors flex items-center gap-1 text-[11px] font-mono"
                  >
                    {copiedId === item.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                    <span>{item.id.slice(0, 8)}...</span>
                  </button>
                </div>

                <h3 className="text-sm font-semibold text-white mt-3 group-hover:text-cyan-300 transition-colors">
                  {item.name}
                </h3>

                <div className="mt-2 flex items-center gap-2 text-xs font-mono text-slate-400">
                  <span className="capitalize px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
                    {item.model_provider}
                  </span>
                  <span>/</span>
                  <span className="text-slate-200">{item.model_name}</span>
                </div>

                {item.prompt_text ? (
                  <div className="mt-3 p-2.5 rounded-lg bg-[#0B0F17] border border-slate-800">
                    <div className="text-[10px] uppercase font-mono text-slate-500 mb-1 flex items-center gap-1">
                      <Terminal className="w-3 h-3" />
                      Prompt Template Preview
                    </div>
                    <p className="text-xs font-mono text-slate-300 line-clamp-3">
                      {item.prompt_text}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic mt-3">
                    No custom system prompt configured.
                  </p>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-600" />
                  {new Date(item.created_at).toLocaleDateString()}
                </span>
                <span className="text-emerald-400/80 font-medium">
                  Active
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      <CreateAgentVersionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          fetchVersions();
        }}
      />
    </div>
  );
};
