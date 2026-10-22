import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  Database,
  Layers,
  PlaySquare,
  Activity,
  Plus,
  ArrowRight,
  Server,
  Sparkles,
  RefreshCw,
  GitCompare,
  Bookmark,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import {
  DashboardSummary,
  HealthResponse,
  EvaluationBaseline,
  EvaluationComparison,
} from '../types/api';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { DatabaseStatusBanner } from '../components/DatabaseStatusBanner';
import { CreateDatasetModal } from '../components/CreateDatasetModal';
import { CreateAgentVersionModal } from '../components/CreateAgentVersionModal';

export const OverviewPage: React.FC = () => {
  const { refreshTrigger } = useOutletContext<{ refreshTrigger: number; health: HealthResponse | null }>();
  const navigate = useNavigate();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [baselines, setBaselines] = useState<EvaluationBaseline[]>([]);
  const [recentComparisons, setRecentComparisons] = useState<EvaluationComparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isDatasetModalOpen, setIsDatasetModalOpen] = useState(false);
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, baselinesData, comparisonsData] = await Promise.all([
        api.getDashboardSummary(),
        api.getActiveBaselines().catch(() => []),
        api.getComparisons(undefined, 0, 5).catch(() => []),
      ]);
      setSummary(data);
      setBaselines(baselinesData);
      setRecentComparisons(comparisonsData);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard summary from backend');
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary, refreshTrigger]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Database Warning Banner if DB connection failed */}
      {summary && !summary.database_connected && (
        <DatabaseStatusBanner
          connected={summary.database_connected}
          message={summary.database_message}
          onRetry={fetchSummary}
          isRetrying={loading}
        />
      )}

      {/* Backend Unreachable Alert */}
      {error && !summary && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200 flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-rose-300 text-sm">Backend Service Unreachable</h4>
              <p className="text-xs text-rose-300/80 mt-1">{error}</p>
              <p className="text-xs text-rose-400/60 mt-2 font-mono">
                Start the backend: <code>uvicorn app.main:app --reload</code> in the backend directory.
              </p>
            </div>
          </div>
          <button
            onClick={fetchSummary}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-medium border border-rose-500/30 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Evaluation Datasets"
          value={summary?.datasets_count ?? 0}
          subtitle="Curated benchmark test sets"
          icon={<Database className="w-5 h-5" />}
          loading={loading}
          accentColor="indigo"
        />

        <MetricCard
          title="Agent Versions"
          value={summary?.versions_count ?? 0}
          subtitle="Prompt & model snapshots"
          icon={<Layers className="w-5 h-5" />}
          loading={loading}
          accentColor="cyan"
        />

        <MetricCard
          title="Evaluation Runs"
          value={summary?.total_runs_count ?? 0}
          subtitle="Benchmark executions"
          icon={<PlaySquare className="w-5 h-5" />}
          loading={loading}
          accentColor="emerald"
        />

        <MetricCard
          title="Latest Run Status"
          value={summary?.latest_run_status ? summary.latest_run_status.toUpperCase() : 'NONE'}
          subtitle={summary?.latest_run_status ? 'Most recent execution' : 'No evaluations executed yet'}
          icon={<Activity className="w-5 h-5" />}
          loading={loading}
          accentColor={summary?.latest_run_status ? 'emerald' : 'slate'}
          badge={
            summary?.latest_run_status ? (
              <StatusBadge status={summary.latest_run_status} />
            ) : null
          }
        />
      </div>

      {/* Platform Architecture & Workflow Banner */}
      <div className="gauge-card p-6 border-indigo-500/20 bg-gradient-to-br from-[#111827] via-[#141E33] to-[#111827] relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="p-1.5 rounded-md bg-indigo-500/20 text-indigo-400">
                <Sparkles className="w-4 h-4" />
              </span>
              <h2 className="text-base font-semibold text-white">The Gauge Evaluation Workflow</h2>
            </div>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Gauge provides automated evaluation loops for AI agents. Prepare your benchmark dataset, register agent snapshots with prompt templates, and compare response accuracy across versions.
            </p>

            {/* Workflow steps pipeline visual */}
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs font-mono text-slate-400">
              <span className="px-2.5 py-1 rounded bg-[#0B0F17] border border-slate-700 text-indigo-300">1. Datasets</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="px-2.5 py-1 rounded bg-[#0B0F17] border border-slate-700 text-cyan-300">2. Agent Versions</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="px-2.5 py-1 rounded bg-[#0B0F17] border border-slate-700 text-emerald-300">3. Execute Runs</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="px-2.5 py-1 rounded bg-[#0B0F17] border border-slate-700 text-amber-300">4. Compare & Detect Regressions</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 flex-shrink-0">
            <button
              onClick={() => setIsDatasetModalOpen(true)}
              className="gauge-btn-primary"
            >
              <Plus className="w-4 h-4" />
              <span>Create Dataset</span>
            </button>
            <button
              onClick={() => setIsVersionModalOpen(true)}
              className="gauge-btn-secondary"
            >
              <Layers className="w-4 h-4" />
              <span>Register Agent</span>
            </button>
          </div>
        </div>
      </div>

      {/* Day 3: Benchmarking, Baselines & Regression Alerts */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Agent Benchmarking & Regression Detection</h3>
          </div>
          <button
            onClick={() => navigate('/comparisons')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1 transition-colors"
          >
            <span>View All Comparisons</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Latest Comparison Alert if Regressed */}
        {recentComparisons.length > 0 && recentComparisons[0].status === 'regressed' && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400 mt-0.5">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div>
                <h4 className="font-semibold text-rose-300 text-sm">
                  Active Regression Alert — Latest Run Regressed
                </h4>
                <p className="text-xs text-rose-300/80 mt-1">
                  Candidate run{' '}
                  <span className="font-mono font-bold text-white">
                    {recentComparisons[0].candidate_run_name || recentComparisons[0].candidate_run_id.slice(0, 8)}
                  </span>{' '}
                  regressed compared to baseline. Delta:{' '}
                  <span className="font-mono font-bold">
                    {recentComparisons[0].pass_rate_delta !== null
                      ? `${recentComparisons[0].pass_rate_delta > 0 ? '+' : ''}${recentComparisons[0].pass_rate_delta.toFixed(1)} pp`
                      : 'N/A'}
                  </span>
                  {recentComparisons[0].newly_failing_count > 0 && (
                    <span className="ml-2 font-mono">
                      ({recentComparisons[0].newly_failing_count} newly failing test cases)
                    </span>
                  )}
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/comparisons')}
              className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-semibold transition-colors"
            >
              Inspect Regressions
            </button>
          </div>
        )}

        {/* Benchmarking Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Active Baselines Card */}
          <div className="gauge-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold flex items-center gap-1.5">
                <Bookmark className="w-3.5 h-3.5 text-indigo-400" />
                Active Baselines ({baselines.length})
              </span>
              <button
                onClick={() => navigate('/evaluations')}
                className="text-[10px] text-indigo-400 hover:underline font-mono"
              >
                + Set Baseline
              </button>
            </div>
            {baselines.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No baselines established. Set a completed run as baseline in Evaluations.
              </p>
            ) : (
              <div className="space-y-2">
                {baselines.slice(0, 2).map((b) => (
                  <div
                    key={b.id}
                    className="p-2 rounded bg-[#0B0F17] border border-slate-800 text-xs font-mono flex items-center justify-between"
                  >
                    <div>
                      <div className="text-white font-medium truncate max-w-[150px]">
                        {b.run_name || b.run_id.slice(0, 8)}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {b.agent_version || 'v1.0'}
                      </div>
                    </div>
                    <span className="text-emerald-400 font-bold">
                      {b.pass_rate !== null && b.pass_rate !== undefined ? `${b.pass_rate.toFixed(1)}%` : '—'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Latest Comparison Card */}
          <div className="gauge-card p-4 space-y-3">
            <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold flex items-center gap-1.5">
              <GitCompare className="w-3.5 h-3.5 text-cyan-400" />
              Latest Comparison
            </span>
            {recentComparisons.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No comparisons run yet. Go to Comparisons to benchmark runs.
              </p>
            ) : (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white font-medium font-mono truncate max-w-[160px]">
                    {recentComparisons[0].candidate_run_name || recentComparisons[0].candidate_run_id.slice(0, 8)}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                      recentComparisons[0].status === 'improved'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : recentComparisons[0].status === 'regressed'
                        ? 'bg-rose-500/20 text-rose-300'
                        : recentComparisons[0].status === 'mixed'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-blue-500/20 text-blue-300'
                    }`}
                  >
                    {recentComparisons[0].status}
                  </span>
                </div>
                <div className="text-xs font-mono flex items-center justify-between text-slate-400 pt-1">
                  <span>Pass Rate Δ:</span>
                  <span
                    className={`font-bold ${
                      (recentComparisons[0].pass_rate_delta ?? 0) > 0
                        ? 'text-emerald-400'
                        : (recentComparisons[0].pass_rate_delta ?? 0) < 0
                        ? 'text-rose-400'
                        : 'text-slate-200'
                    }`}
                  >
                    {recentComparisons[0].pass_rate_delta !== null
                      ? `${Math.abs(recentComparisons[0].pass_rate_delta) < 0.005 ? '0.0' : `${recentComparisons[0].pass_rate_delta > 0 ? '+' : ''}${recentComparisons[0].pass_rate_delta.toFixed(1)}`} pp`
                      : '—'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Regression Health Metric */}
          <div className="gauge-card p-4 space-y-3">
            <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              Benchmarking Status
            </span>
            <div className="pt-1">
              <div className="text-xl font-bold font-mono text-white">
                {recentComparisons.length} Comparisons
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                {recentComparisons.filter((c) => c.status === 'regressed').length} regressions flagged across historical runs
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Evaluations Section */}
      <div className="gauge-card p-6">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent Evaluation Runs</h3>
            <p className="text-xs text-slate-400">Live execution history from the Gauge database</p>
          </div>
          <button
            onClick={() => navigate('/evaluations')}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 transition-colors"
          >
            <span>View All Runs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {loading ? (
          <div className="space-y-3 py-4">
            <div className="h-10 bg-slate-800/50 animate-pulse rounded-lg" />
            <div className="h-10 bg-slate-800/50 animate-pulse rounded-lg" />
            <div className="h-10 bg-slate-800/50 animate-pulse rounded-lg" />
          </div>
        ) : summary?.recent_runs && summary.recent_runs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0B0F17] text-slate-400 uppercase tracking-wider font-mono">
                <tr>
                  <th className="px-4 py-2.5 rounded-l-lg">Run Name</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Pass Rate</th>
                  <th className="px-4 py-2.5">Cases</th>
                  <th className="px-4 py-2.5 rounded-r-lg">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono">
                {summary.recent_runs.map((run) => (
                  <tr
                    key={run.id}
                    onClick={() => navigate('/evaluations')}
                    className="hover:bg-slate-800/30 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-white">{run.name}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-3">
                      {run.pass_rate !== null && run.pass_rate !== undefined ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {run.pass_rate.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-slate-500">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {run.total_cases > 0 ? `${run.passed_cases}/${run.total_cases}` : '0 cases'}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<PlaySquare className="w-6 h-6" />}
            title="No Evaluation Runs Executed Yet"
            description="Launch benchmark evaluation runs to execute test cases against registered agent versions, calculate exact-match accuracy, and inspect per-case diagnostics."
            actionLabel="Create Benchmark Dataset"
            onAction={() => setIsDatasetModalOpen(true)}
            secondaryActionLabel="Register Agent Version"
            onSecondaryAction={() => setIsVersionModalOpen(true)}
          />
        )}
      </div>

      {/* Modals */}
      <CreateDatasetModal
        isOpen={isDatasetModalOpen}
        onClose={() => setIsDatasetModalOpen(false)}
        onSuccess={() => {
          fetchSummary();
        }}
      />

      <CreateAgentVersionModal
        isOpen={isVersionModalOpen}
        onClose={() => setIsVersionModalOpen(false)}
        onSuccess={() => {
          fetchSummary();
        }}
      />
    </div>
  );
};
