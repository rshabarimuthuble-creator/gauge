import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  GitCompare,
  Search,
  AlertCircle,
  Eye,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  HelpCircle,
  Bookmark,
  Database,
  ArrowRight,
  Plus,
  Loader2,
  Filter,
} from 'lucide-react';
import { api } from '../services/api';
import {
  EvaluationComparison,
  EvaluationBaseline,
  HealthResponse,
} from '../types/api';
import { EmptyState } from '../components/EmptyState';
import { LaunchComparisonModal } from '../components/LaunchComparisonModal';
import { ComparisonDetailDrawer } from '../components/ComparisonDetailDrawer';

export const ComparisonsPage: React.FC = () => {
  const { refreshTrigger } = useOutletContext<{ refreshTrigger: number; health: HealthResponse | null }>();

  const [comparisons, setComparisons] = useState<EvaluationComparison[]>([]);
  const [baselines, setBaselines] = useState<EvaluationBaseline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Drawer & Modal state
  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState(false);
  const [selectedComparison, setSelectedComparison] = useState<EvaluationComparison | null>(null);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [inspectingId, setInspectingId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [compsData, baselinesData] = await Promise.all([
        api.getComparisons(),
        api.getActiveBaselines(),
      ]);
      setComparisons(compsData);
      setBaselines(baselinesData);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch comparisons and baselines.');
    } finally {
      setLoading(false);
    }
  }, []);

  const formatDeltaMs = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return '—';
    if (Math.abs(val) < 0.005) return '0.00 ms';
    return `${val > 0 ? '+' : ''}${val.toFixed(2)} ms`;
  };

  const formatDeltaPp = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return '—';
    if (Math.abs(val) < 0.005) return '0.0 pp';
    return `${val > 0 ? '+' : ''}${val.toFixed(1)} pp`;
  };

  useEffect(() => {
    fetchData();
  }, [fetchData, refreshTrigger]);

  const handleOpenDetail = async (comp: EvaluationComparison) => {
    setInspectingId(comp.id);
    try {
      const detailed = await api.getComparison(comp.id);
      setSelectedComparison(detailed);
      setIsDetailDrawerOpen(true);
    } catch (err: any) {
      setError(`Failed to fetch comparison details: ${err.message}`);
    } finally {
      setInspectingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'improved':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <TrendingUp className="w-3 h-3" />
            Improved
          </span>
        );
      case 'regressed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <TrendingDown className="w-3 h-3" />
            Regressed
          </span>
        );
      case 'mixed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3" />
            Mixed
          </span>
        );
      case 'unchanged':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <Minus className="w-3 h-3" />
            Unchanged
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/15 text-slate-400 border border-slate-500/30">
            <HelpCircle className="w-3 h-3" />
            Inconclusive
          </span>
        );
    }
  };

  const filteredComparisons = comparisons.filter((c) => {
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    const matchesSearch =
      c.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.candidate_run_name && c.candidate_run_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.baseline_run_name && c.baseline_run_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.candidate_agent_version && c.candidate_agent_version.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.baseline_agent_version && c.baseline_agent_version.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Day 3 Architecture Banner */}
      <div className="gauge-card p-5 border-cyan-500/20 bg-cyan-500/5">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 mt-0.5">
            <GitCompare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">
                Day 3: Agent Benchmarking & Version Comparison Engine
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                Persistent Baselines & Regression Detection
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Designate golden baseline runs, evaluate candidate agent versions across identical benchmarks, calculate explicit percentage-point metric deltas, and automatically identify regressions against configurable thresholds.
            </p>
          </div>
        </div>
      </div>

      {/* Active Baselines Strip */}
      <div className="gauge-card p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Bookmark className="w-4 h-4 text-indigo-400" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Active Benchmark Baselines ({baselines.length})
            </h4>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            Persistent reference runs per dataset
          </span>
        </div>

        {baselines.length === 0 ? (
          <p className="text-xs text-slate-500 italic">
            No active baselines designated yet. Open any completed run in Evaluations and click "Set as Baseline".
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {baselines.map((b) => (
              <div
                key={b.id}
                className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800 flex items-center justify-between"
              >
                <div>
                  <div className="text-xs font-semibold text-white font-mono flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Dataset: {b.dataset_id.slice(0, 8)}...</span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    Run: {b.run_name || b.run_id.slice(0, 8)}
                    {b.agent_version && <span className="text-cyan-400"> ({b.agent_version})</span>}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold font-mono text-emerald-400">
                    {b.pass_rate !== null && b.pass_rate !== undefined ? `${b.pass_rate.toFixed(1)}%` : 'N/A'}
                  </span>
                  <span className="text-[10px] text-slate-500 block">Baseline Pass</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Comparison History Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-cyan-400" />
            Benchmark Comparisons
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Audit history of version comparisons and regression classifications
          </p>
        </div>

        <button
          onClick={() => setIsLaunchModalOpen(true)}
          className="gauge-btn-primary flex items-center gap-2 self-start sm:self-auto bg-cyan-600 hover:bg-cyan-500 shadow-cyan-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>New Comparison</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search by run name, agent version, or comparison ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#111827] border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#111827] border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Statuses</option>
            <option value="improved">Improved</option>
            <option value="regressed">Regressed</option>
            <option value="mixed">Mixed</option>
            <option value="unchanged">Unchanged</option>
            <option value="inconclusive">Inconclusive</option>
          </select>
        </div>
      </div>

      {/* Content State */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
          <span className="text-sm font-medium">Loading saved comparisons...</span>
        </div>
      ) : error ? (
        <div className="gauge-card p-6 border-rose-500/20 bg-rose-500/5 text-rose-300 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-rose-300 text-sm">Failed to Load Comparisons</h4>
            <p className="text-xs text-rose-300/80 mt-1">{error}</p>
          </div>
        </div>
      ) : filteredComparisons.length === 0 ? (
        <EmptyState
          title="No Benchmark Comparisons Found"
          description={
            searchQuery || statusFilter !== 'all'
              ? 'No comparisons match the current search or status filter.'
              : 'Launch your first evaluation run comparison against an active baseline to detect regressions and monitor agent performance.'
          }
          icon={<GitCompare className="w-8 h-8 text-cyan-400" />}
          actionLabel="Launch Comparison"
          onAction={() => setIsLaunchModalOpen(true)}
        />
      ) : (
        <div className="gauge-card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-[#0B0F17] text-xs font-mono uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Baseline vs Candidate</th>
                  <th className="px-5 py-3.5">Pass Rate Δ</th>
                  <th className="px-5 py-3.5">Avg Latency Δ</th>
                  <th className="px-5 py-3.5">Outcome Changes</th>
                  <th className="px-5 py-3.5">Timestamp</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono text-xs">
                {filteredComparisons.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => handleOpenDetail(c)}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                  >
                    {/* Status */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      {getStatusBadge(c.status)}
                    </td>

                    {/* Baseline vs Candidate */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-400">
                          {c.baseline_agent_version || c.baseline_run_name || c.baseline_run_id.slice(0, 6)}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                        <span className="text-white font-semibold">
                          {c.candidate_agent_version || c.candidate_run_name || c.candidate_run_id.slice(0, 6)}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        Dataset: {c.dataset_id.slice(0, 8)}...
                      </div>
                    </td>

                    {/* Pass Rate & Accuracy Delta */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="flex flex-col gap-0.5">
                        <span
                          className={`font-bold ${
                            (c.pass_rate_delta ?? 0) > 0
                              ? 'text-emerald-400'
                              : (c.pass_rate_delta ?? 0) < 0
                              ? 'text-rose-400'
                              : 'text-slate-300'
                          }`}
                        >
                          {formatDeltaPp(c.pass_rate_delta)} pass
                        </span>
                        {c.accuracy_delta !== null && c.accuracy_delta !== undefined && (
                          <span className="text-[10px] text-cyan-400">
                            {formatDeltaPp(c.accuracy_delta)} acc
                          </span>
                        )}
                        {!c.is_compatible && (
                          <span className="text-[9px] text-rose-400 font-semibold uppercase">
                            Incompatible
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Latency Delta */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      <span
                        className={
                          (c.avg_latency_ms_delta ?? 0) > 0
                            ? 'text-rose-400'
                            : (c.avg_latency_ms_delta ?? 0) < 0
                            ? 'text-emerald-400'
                            : 'text-slate-300'
                        }
                      >
                        {formatDeltaMs(c.avg_latency_ms_delta)}
                      </span>
                    </td>

                    {/* Outcome Diffs */}
                    <td className="px-5 py-4 whitespace-nowrap text-[11px]">
                      <div className="flex items-center gap-2.5">
                        {c.newly_failing_count > 0 && (
                          <span className="text-rose-400 font-semibold">
                            -{c.newly_failing_count} failing
                          </span>
                        )}
                        {c.newly_fixed_count > 0 && (
                          <span className="text-emerald-400 font-semibold">
                            +{c.newly_fixed_count} fixed
                          </span>
                        )}
                        {c.newly_failing_count === 0 && c.newly_fixed_count === 0 && (
                          <span className="text-slate-500">No outcome flips</span>
                        )}
                      </div>
                    </td>

                    {/* Timestamp */}
                    <td className="px-5 py-4 whitespace-nowrap text-slate-400 text-[11px]">
                      {new Date(c.created_at).toLocaleString()}
                    </td>

                    {/* Actions */}
                    <td className="px-5 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDetail(c);
                        }}
                        disabled={inspectingId === c.id}
                        className="gauge-btn-secondary py-1 px-2.5 text-xs inline-flex items-center gap-1"
                      >
                        {inspectingId === c.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                        <span>{inspectingId === c.id ? 'Loading...' : 'Inspect'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Launch Comparison Modal */}
      <LaunchComparisonModal
        isOpen={isLaunchModalOpen}
        onClose={() => setIsLaunchModalOpen(false)}
        onSuccess={(comp) => {
          fetchData();
          handleOpenDetail(comp);
        }}
      />

      {/* Comparison Detail Drawer */}
      <ComparisonDetailDrawer
        comparison={selectedComparison}
        isOpen={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedComparison(null);
        }}
      />
    </div>
  );
};
