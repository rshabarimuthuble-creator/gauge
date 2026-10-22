import React, { useState, useEffect } from 'react';
import {
  X,
  GitCompare,
  Sliders,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { api } from '../services/api';
import {
  EvaluationRun,
  EvaluationBaseline,
  EvaluationComparison,
  RegressionThresholds,
} from '../types/api';

interface LaunchComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (comparison: EvaluationComparison) => void;
  initialCandidateRunId?: string | null;
  initialBaselineRunId?: string | null;
}

export const LaunchComparisonModal: React.FC<LaunchComparisonModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialCandidateRunId,
  initialBaselineRunId,
}) => {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [baselines, setBaselines] = useState<EvaluationBaseline[]>([]);
  const [loadingInitial, setLoadingInitial] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [candidateRunId, setCandidateRunId] = useState<string>(initialCandidateRunId || '');
  const [useActiveBaseline, setUseActiveBaseline] = useState<boolean>(!initialBaselineRunId);
  const [customBaselineRunId, setCustomBaselineRunId] = useState<string>(initialBaselineRunId || '');

  // Advanced Thresholds
  const [showThresholds, setShowThresholds] = useState<boolean>(false);
  const [passRateDeclineThreshold, setPassRateDeclineThreshold] = useState<number>(0.0);
  const [latencyIncreaseThreshold, setLatencyIncreaseThreshold] = useState<number>(100.0);
  const [p95LatencyIncreaseThreshold, setP95LatencyIncreaseThreshold] = useState<number>(150.0);
  const [errorCountIncreaseThreshold, setErrorCountIncreaseThreshold] = useState<number>(1);

  useEffect(() => {
    if (isOpen) {
      loadData();
      if (initialCandidateRunId) setCandidateRunId(initialCandidateRunId);
      if (initialBaselineRunId) {
        setCustomBaselineRunId(initialBaselineRunId);
        setUseActiveBaseline(false);
      }
    }
  }, [isOpen, initialCandidateRunId, initialBaselineRunId]);

  const loadData = async () => {
    setLoadingInitial(true);
    setError(null);
    try {
      const [allRuns, activeBaselines] = await Promise.all([
        api.getEvaluationRuns(),
        api.getActiveBaselines(),
      ]);
      const completed = allRuns.filter((r) => r.status === 'completed' && r.total_cases > 0);
      setRuns(completed);
      setBaselines(activeBaselines);

      if (!candidateRunId && completed.length > 0) {
        setCandidateRunId(completed[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load evaluation runs and baselines.');
    } finally {
      setLoadingInitial(false);
    }
  };

  if (!isOpen) return null;

  const selectedCandidate = runs.find((r) => r.id === candidateRunId);
  const activeBaselineForDataset = selectedCandidate
    ? baselines.find((b) => b.dataset_id === selectedCandidate.dataset_id)
    : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidateRunId) {
      setError('Please select a candidate evaluation run.');
      return;
    }

    if (!useActiveBaseline && !customBaselineRunId) {
      setError('Please select a specific baseline run.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const thresholds: RegressionThresholds = {
        pass_rate_decline_threshold: passRateDeclineThreshold,
        latency_increase_threshold_ms: latencyIncreaseThreshold,
        p95_latency_increase_threshold_ms: p95LatencyIncreaseThreshold,
        error_count_increase_threshold: errorCountIncreaseThreshold,
      };

      const result = await api.createComparison({
        candidate_run_id: candidateRunId,
        baseline_run_id: useActiveBaseline ? undefined : customBaselineRunId,
        thresholds,
      });

      onSuccess(result);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to execute benchmark comparison.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl gauge-card p-0 shadow-2xl border-slate-700 flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-[#0B0F17]/90">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Compare Evaluation Runs</h2>
              <p className="text-xs text-slate-400">
                Detect regressions against active baseline with configurable thresholds
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Validation Error</p>
                <p className="mt-0.5 opacity-90">{error}</p>
              </div>
            </div>
          )}

          {loadingInitial ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
              <span className="text-xs">Loading available evaluation runs...</span>
            </div>
          ) : (
            <>
              {/* Candidate Run Selector */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                  <span>Candidate Evaluation Run</span>
                  <span className="text-[11px] text-cyan-400 font-mono">Run under test</span>
                </label>
                <select
                  value={candidateRunId}
                  onChange={(e) => setCandidateRunId(e.target.value)}
                  className="w-full bg-[#111827] border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  disabled={submitting}
                  required
                >
                  <option value="" disabled>
                    Select candidate run...
                  </option>
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} — Pass: {r.pass_rate !== null ? `${r.pass_rate.toFixed(1)}%` : 'N/A'} (
                      {r.total_cases} cases)
                    </option>
                  ))}
                </select>
                {selectedCandidate && (
                  <p className="text-[11px] text-slate-400 font-mono flex items-center gap-2 mt-1">
                    <span>Dataset: {selectedCandidate.dataset_id.slice(0, 8)}...</span>
                    <span>•</span>
                    <span>Version: {selectedCandidate.agent_version_id.slice(0, 8)}...</span>
                  </p>
                )}
              </div>

              {/* Baseline Source Toggle */}
              <div className="space-y-3 pt-2 border-t border-slate-800">
                <label className="text-xs font-semibold text-slate-200">Baseline Run</label>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setUseActiveBaseline(true)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      useActiveBaseline
                        ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-200'
                        : 'bg-[#111827] border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-semibold text-white">Active Dataset Baseline</div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      {activeBaselineForDataset ? (
                        <span className="text-emerald-400 font-mono">
                          ✓ Set: {activeBaselineForDataset.run_name || activeBaselineForDataset.run_id.slice(0, 8)}
                        </span>
                      ) : (
                        <span className="text-amber-400">No active baseline for this dataset</span>
                      )}
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setUseActiveBaseline(false)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      !useActiveBaseline
                        ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-200'
                        : 'bg-[#111827] border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-semibold text-white">Custom Historical Run</div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      Manually select any completed run
                    </div>
                  </button>
                </div>

                {!useActiveBaseline && (
                  <div className="space-y-1.5 mt-2">
                    <select
                      value={customBaselineRunId}
                      onChange={(e) => setCustomBaselineRunId(e.target.value)}
                      className="w-full bg-[#111827] border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                      disabled={submitting}
                      required
                    >
                      <option value="" disabled>
                        Select baseline run...
                      </option>
                      {runs
                        .filter((r) => r.id !== candidateRunId)
                        .map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.name} — Pass: {r.pass_rate !== null ? `${r.pass_rate.toFixed(1)}%` : 'N/A'} (
                            {r.total_cases} cases)
                          </option>
                        ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Advanced Regression Thresholds Accordion */}
              <div className="pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowThresholds(!showThresholds)}
                  className="flex items-center justify-between w-full text-xs text-slate-400 hover:text-slate-200 py-1"
                >
                  <span className="flex items-center gap-1.5 font-medium">
                    <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                    Configure Regression Thresholds
                  </span>
                  <span className="font-mono text-[11px] text-cyan-400">
                    {showThresholds ? 'Hide' : 'Customize'}
                  </span>
                </button>

                {showThresholds && (
                  <div className="mt-3 p-4 rounded-xl bg-[#0B0F17] border border-slate-800 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-[11px] font-mono text-slate-300 block mb-1">
                          Pass Rate Decline Threshold (pp)
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          min="0"
                          max="100"
                          value={passRateDeclineThreshold}
                          onChange={(e) => setPassRateDeclineThreshold(parseFloat(e.target.value) || 0)}
                          className="w-full bg-[#111827] border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                        />
                        <span className="text-[10px] text-slate-500 mt-0.5 block">
                          Default 0.0 pp (any drop is flagged)
                        </span>
                      </div>

                      <div>
                        <label className="text-[11px] font-mono text-slate-300 block mb-1">
                          Avg Latency Increase (ms)
                        </label>
                        <input
                          type="number"
                          step="10"
                          min="0"
                          value={latencyIncreaseThreshold}
                          onChange={(e) => setLatencyIncreaseThreshold(parseFloat(e.target.value) || 0)}
                          className="w-full bg-[#111827] border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                        />
                        <span className="text-[10px] text-slate-500 mt-0.5 block">
                          Default 100.0 ms threshold
                        </span>
                      </div>

                      <div>
                        <label className="text-[11px] font-mono text-slate-300 block mb-1">
                          P95 Latency Increase (ms)
                        </label>
                        <input
                          type="number"
                          step="10"
                          min="0"
                          value={p95LatencyIncreaseThreshold}
                          onChange={(e) => setP95LatencyIncreaseThreshold(parseFloat(e.target.value) || 0)}
                          className="w-full bg-[#111827] border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                        />
                        <span className="text-[10px] text-slate-500 mt-0.5 block">
                          Default 150.0 ms threshold
                        </span>
                      </div>

                      <div>
                        <label className="text-[11px] font-mono text-slate-300 block mb-1">
                          Error Count Increase
                        </label>
                        <input
                          type="number"
                          step="1"
                          min="1"
                          value={errorCountIncreaseThreshold}
                          onChange={(e) => setErrorCountIncreaseThreshold(parseInt(e.target.value, 10) || 1)}
                          className="w-full bg-[#111827] border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                        />
                        <span className="text-[10px] text-slate-500 mt-0.5 block">
                          Default 1 new execution error
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Footer Actions */}
          <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || loadingInitial || runs.length === 0}
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Comparing Runs...</span>
                </>
              ) : (
                <>
                  <GitCompare className="w-4 h-4" />
                  <span>Run Comparison</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
