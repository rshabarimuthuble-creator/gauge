import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  PlaySquare,
  Sparkles,
  Search,
  Calendar,
  AlertCircle,
  Copy,
  Check,
  Eye,
  Clock,
  Loader2,
} from 'lucide-react';
import { api } from '../services/api';
import { EvaluationRun, HealthResponse } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { LaunchEvaluationModal } from '../components/LaunchEvaluationModal';
import { EvaluationDetailDrawer } from '../components/EvaluationDetailDrawer';
import { LaunchComparisonModal } from '../components/LaunchComparisonModal';
import { ComparisonDetailDrawer } from '../components/ComparisonDetailDrawer';
import { EvaluationComparison } from '../types/api';

export const EvaluationsPage: React.FC = () => {
  const { refreshTrigger } = useOutletContext<{ refreshTrigger: number; health: HealthResponse | null }>();

  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Modals state
  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [inspectingRunId, setInspectingRunId] = useState<string | null>(null);

  // Comparison Modals state
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);
  const [compareCandidateRunId, setCompareCandidateRunId] = useState<string | null>(null);
  const [activeComparison, setActiveComparison] = useState<EvaluationComparison | null>(null);
  const [isComparisonDetailOpen, setIsComparisonDetailOpen] = useState(false);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getEvaluationRuns();
      setRuns(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch evaluation runs from backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns, refreshTrigger]);

  useEffect(() => {
    const hasRunning = runs.some((r) => r.status === 'running' || r.status === 'pending');
    if (!hasRunning) return;

    const intervalId = setInterval(async () => {
      try {
        const freshRuns = await api.getEvaluationRuns();
        setRuns(freshRuns);
      } catch {
        // Silently skip transient polling errors
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [runs]);


  const handleCopy = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleOpenDetail = async (run: EvaluationRun) => {
    setInspectingRunId(run.id);
    try {
      const detail = await api.getEvaluationRun(run.id);
      setSelectedRun(detail);
      setIsDetailOpen(true);
    } catch (err: any) {
      setError(`Failed to fetch run details: ${err.message}`);
    } finally {
      setInspectingRunId(null);
    }
  };

  const handleRunSuccess = (createdRun: EvaluationRun) => {
    fetchRuns();
    // Open detail for newly created run
    handleOpenDetail(createdRun);
  };

  const filteredRuns = runs.filter((r) =>
    r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.status.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Architecture Notice */}
      <div className="gauge-card p-5 border-emerald-500/20 bg-emerald-500/5">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 mt-0.5">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">Gauge Benchmarking & Evaluation Engine Active</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                Real Groq / OpenAI LLMs & Deterministic Mock Adapter
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Execute standardized benchmarks against live model providers or deterministic simulations. Measures wall-clock execution latency, token telemetry, exact-match and multi-method scoring, and snapshots datasets to guarantee reproducible evaluations.
            </p>
          </div>
        </div>
      </div>

      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search runs by name, status, or run ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="gauge-input pl-10"
          />
        </div>

        <button
          onClick={() => setIsLaunchModalOpen(true)}
          className="gauge-btn-primary w-full sm:w-auto"
        >
          <PlaySquare className="w-4 h-4" />
          <span>Launch Evaluation</span>
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Evaluation Engine Notice</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Runs Table / Empty State */}
      {loading ? (
        <div className="gauge-card p-6 space-y-4 animate-pulse">
          <div className="h-6 bg-slate-800 rounded w-1/4" />
          <div className="h-10 bg-slate-800 rounded" />
          <div className="h-10 bg-slate-800 rounded" />
          <div className="h-10 bg-slate-800 rounded" />
        </div>
      ) : runs.length === 0 ? (
        <EmptyState
          icon={<PlaySquare className="w-6 h-6" />}
          title="No Evaluations Recorded Yet"
          description="Launch your first evaluation run to benchmark a registered agent version against a test dataset and view scored metrics."
          actionLabel="Launch First Evaluation"
          onAction={() => setIsLaunchModalOpen(true)}
        />
      ) : filteredRuns.length === 0 ? (
        <div className="gauge-card p-8 text-center text-slate-400 text-sm">
          No evaluations match your search query "{searchQuery}".
        </div>
      ) : (
        <div className="gauge-card overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Recorded Runs ({filteredRuns.length})</h3>
            <span className="text-xs text-slate-400 font-mono">Live PostgreSQL Records</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0B0F17] text-slate-400 uppercase tracking-wider font-mono">
                <tr>
                  <th className="px-5 py-3">Run Name & Engine</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Pass Rate & Acc</th>
                  <th className="px-5 py-3">Case Breakdown</th>
                  <th className="px-5 py-3">Avg Latency</th>
                  <th className="px-5 py-3">Created At</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono">
                {filteredRuns.map((run) => (
                  <tr
                    key={run.id}
                    onClick={() => handleOpenDetail(run)}
                    className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{run.name}</span>
                        {run.dataset_version && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                            {run.dataset_version}
                          </span>
                        )}
                        {run.model_provider && (
                          <span className={`text-[10px] px-1.5 py-0.2 rounded ${
                            run.model_provider === 'mock'
                              ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                              : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                          }`}>
                            {run.model_provider}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={(e) => handleCopy(run.id, e)}
                        className="text-[11px] text-slate-500 hover:text-slate-300 flex items-center gap-1 mt-0.5"
                      >
                        {copiedId === run.id ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                        <span>{run.id.slice(0, 8)}...</span>
                      </button>
                    </td>

                    <td className="px-5 py-3.5">
                      <StatusBadge status={run.status} />
                    </td>

                    <td className="px-5 py-3.5">
                      <div className="flex flex-col gap-0.5">
                        {run.pass_rate !== null ? (
                          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 w-fit">
                            {run.pass_rate.toFixed(1)}% pass
                          </span>
                        ) : (
                          <span className="text-slate-500">N/A</span>
                        )}
                        {run.accuracy !== null && run.accuracy !== undefined && (
                          <span className="text-[10px] text-cyan-400/90">
                            {run.accuracy.toFixed(1)}% acc
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="px-5 py-3.5 text-slate-300">
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-400" title="Passed">{run.passed_cases}P</span>
                        <span>/</span>
                        <span className="text-rose-400" title="Failed">{run.failed_cases}F</span>
                        {run.errored_cases > 0 && (
                          <>
                            <span>/</span>
                            <span className="text-amber-400" title="Errored">{run.errored_cases}E</span>
                          </>
                        )}
                        {run.unscored_cases > 0 && (
                          <>
                            <span>/</span>
                            <span className="text-slate-500" title="Unscored">{run.unscored_cases}U</span>
                          </>
                        )}
                        <span className="text-slate-500 text-[11px]">({run.total_cases} tot)</span>
                      </div>
                    </td>

                    <td className="px-5 py-3.5 text-slate-400">
                      {run.avg_latency_ms !== null ? (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-500" />
                          {run.avg_latency_ms} ms
                        </span>
                      ) : (
                        <span className="text-slate-600">-</span>
                      )}
                    </td>

                    <td className="px-5 py-3.5 text-slate-400">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        <span>{new Date(run.created_at).toLocaleDateString()}</span>
                      </div>
                    </td>

                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDetail(run);
                        }}
                        disabled={inspectingRunId === run.id}
                        className="gauge-btn-secondary py-1 px-2.5 text-xs inline-flex items-center gap-1"
                      >
                        {inspectingRunId === run.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                        <span>{inspectingRunId === run.id ? 'Loading...' : 'Inspect'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Launch Modal */}
      <LaunchEvaluationModal
        isOpen={isLaunchModalOpen}
        onClose={() => setIsLaunchModalOpen(false)}
        onSuccess={handleRunSuccess}
      />

      {/* Detail Drawer */}
      <EvaluationDetailDrawer
        run={selectedRun}
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        onSetBaselineSuccess={fetchRuns}
        onLaunchCompare={(run) => {
          setCompareCandidateRunId(run.id);
          setIsCompareModalOpen(true);
        }}
      />

      {/* Comparison Modal */}
      <LaunchComparisonModal
        isOpen={isCompareModalOpen}
        onClose={() => {
          setIsCompareModalOpen(false);
          setCompareCandidateRunId(null);
        }}
        initialCandidateRunId={compareCandidateRunId}
        onSuccess={(comp) => {
          setActiveComparison(comp);
          setIsComparisonDetailOpen(true);
        }}
      />

      {/* Comparison Detail Drawer */}
      <ComparisonDetailDrawer
        comparison={activeComparison}
        isOpen={isComparisonDetailOpen}
        onClose={() => {
          setIsComparisonDetailOpen(false);
          setActiveComparison(null);
        }}
      />
    </div>
  );
};
