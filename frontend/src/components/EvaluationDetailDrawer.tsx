import React, { useState, useEffect } from 'react';
import {
  X,
  AlertTriangle,
  Clock,
  Zap,
  Search,
  Copy,
  Check,
  Calendar,
  Layers,
  Database,
  Info,
  Bookmark,
  GitCompare,
  Loader2,
} from 'lucide-react';
import { EvaluationRun, EvaluationResult } from '../types/api';
import { StatusBadge } from './StatusBadge';
import { api } from '../services/api';

interface EvaluationDetailDrawerProps {
  run: EvaluationRun | null;
  isOpen: boolean;
  onClose: () => void;
  onSetBaselineSuccess?: () => void;
  onLaunchCompare?: (run: EvaluationRun) => void;
}

export const EvaluationDetailDrawer: React.FC<EvaluationDetailDrawerProps> = ({
  run: initialRun,
  isOpen,
  onClose,
  onSetBaselineSuccess,
  onLaunchCompare,
}) => {
  const [run, setRun] = useState<EvaluationRun | null>(initialRun);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [settingBaseline, setSettingBaseline] = useState(false);
  const [baselineNotice, setBaselineNotice] = useState<string | null>(null);

  useEffect(() => {
    setRun(initialRun);
  }, [initialRun]);

  useEffect(() => {
    if (!isOpen || !run || (run.status !== 'running' && run.status !== 'pending')) {
      return;
    }

    const intervalId = setInterval(async () => {
      try {
        const updated = await api.getEvaluationRun(run.id);
        setRun(updated);
        if (updated.status === 'completed' || updated.status === 'failed') {
          onSetBaselineSuccess?.();
        }
      } catch (pollErr) {
        // Silently retry on next tick
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [isOpen, run?.id, run?.status, onSetBaselineSuccess]);

  if (!isOpen || !run) return null;

  const results: EvaluationResult[] = run.results || [];
  const isMockExecution = results.length === 0 || results.some((r) => r.is_mock);

  const firstRealResult = results.find((r) => !r.is_mock);
  let resolvedProviderName = 'Real Provider';
  let resolvedModelName = '';
  if (firstRealResult && firstRealResult.metadata_json) {
    try {
      const parsed = JSON.parse(firstRealResult.metadata_json);
      if (parsed.provider) resolvedProviderName = parsed.provider.toUpperCase();
      if (parsed.model) resolvedModelName = parsed.model;
    } catch {}
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSetBaseline = async () => {
    if (!run || run.status !== 'completed' || run.total_cases <= 0) return;
    setSettingBaseline(true);
    setBaselineNotice(null);
    try {
      await api.setBaseline({
        dataset_id: run.dataset_id,
        run_id: run.id,
        notes: `Designated as baseline for ${run.name}`,
      });
      setBaselineNotice('Successfully set as active baseline!');
      onSetBaselineSuccess?.();
    } catch (err: any) {
      setBaselineNotice(`Failed: ${err.message}`);
    } finally {
      setSettingBaseline(false);
    }
  };

  const filteredResults = results.filter((res) => {
    const matchesStatus = filterStatus === 'all' || res.status === filterStatus;
    const matchesSearch =
      res.case_identifier.toLowerCase().includes(searchQuery.toLowerCase()) ||
      res.input_prompt.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (res.expected_output && res.expected_output.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (res.actual_output && res.actual_output.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  const eligibleCount = run.passed_cases + run.failed_cases;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-5xl h-[90vh] gauge-card p-0 shadow-2xl border-slate-700 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-[#0B0F17]/90">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-white">{run.name}</h2>
              <StatusBadge status={run.status} />
              {isMockExecution ? (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  Mock Adapter Execution
                </span>
              ) : (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
                  <Zap className="w-3 h-3 text-emerald-400" />
                  Real Provider ({resolvedProviderName}{resolvedModelName ? ` - ${resolvedModelName}` : ''}) Execution
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 mt-2 text-xs font-mono text-slate-400">
              <button
                onClick={() => handleCopy(run.id)}
                className="hover:text-slate-200 flex items-center gap-1 transition-colors"
                title="Copy Run ID"
              >
                {copiedId === run.id ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                <span>Run: {run.id.slice(0, 13)}...</span>
              </button>

              <span className="flex items-center gap-1">
                <Database className="w-3.5 h-3.5 text-indigo-400" />
                <span>Dataset: {run.dataset_id.slice(0, 8)}...</span>
                <span className="px-1.5 py-0.2 bg-indigo-500/20 text-indigo-300 rounded text-[10px] font-bold">
                  {run.dataset_version || 'v1.0.0'}
                </span>
              </span>

              {run.scoring_config && (
                <span className="flex items-center gap-1 text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                  <span>Rule:</span>
                  <span className="text-cyan-300 font-semibold">{run.scoring_config}</span>
                </span>
              )}

              <span className="flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>Agent Version: {run.agent_version_id.slice(0, 8)}...</span>
              </span>

              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                <span>{new Date(run.created_at).toLocaleString()}</span>
              </span>
            </div>

            {baselineNotice && (
              <div className="mt-2 text-xs font-mono text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded inline-block">
                {baselineNotice}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {run.status === 'completed' && run.total_cases > 0 && (
              <>
                <button
                  onClick={handleSetBaseline}
                  disabled={settingBaseline}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-all disabled:opacity-50"
                  title="Designate this completed run as the active baseline for its dataset"
                >
                  {settingBaseline ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Bookmark className="w-3.5 h-3.5" />
                  )}
                  <span>Set as Baseline</span>
                </button>

                <button
                  onClick={() => onLaunchCompare?.(run)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/20 transition-all"
                  title="Compare this run against active baseline"
                >
                  <GitCompare className="w-3.5 h-3.5" />
                  <span>Compare Run</span>
                </button>
              </>
            )}

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Active Running Progress Banner */}
          {(run.status === 'running' || run.status === 'pending') && (
            <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 text-indigo-400 animate-spin flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-white">Evaluation is running in the background...</p>
                  <p className="text-xs text-slate-400 mt-0.5">Test cases are actively executing against the agent adapter. Metrics and results will populate upon completion.</p>
                </div>
              </div>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex-shrink-0">
                Auto-refreshing (2s)
              </span>
            </div>
          )}

          {/* Fatal Failure Banner */}
          {run.status === 'failed' && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-white">Evaluation Execution Failed</p>
                <p className="text-xs text-rose-300 mt-0.5">{run.error_message || 'The evaluation run encountered a fatal error during execution.'}</p>
              </div>
            </div>
          )}

          {/* Aggregate Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">

            {/* Pass Rate */}
            <div className="gauge-card p-3.5 border-emerald-500/20 bg-emerald-500/5">
              <span className="text-[10px] font-mono uppercase text-emerald-400 font-semibold" title="Numerator: passed cases. Denominator: (passed + failed) eligible cases. Excludes errors and unscored cases.">
                Pass Rate
              </span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {run.pass_rate !== null ? `${run.pass_rate.toFixed(1)}%` : 'N/A'}
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {eligibleCount > 0 ? `${run.passed_cases}/${eligibleCount} eligible` : '0 eligible'}
              </div>
            </div>

            {/* Strict Accuracy */}
            <div className="gauge-card p-3.5 border-cyan-500/20 bg-cyan-500/5">
              <span className="text-[10px] font-mono uppercase text-cyan-400 font-semibold" title="Numerator: passed cases. Denominator: total executed cases. Penalized by errors and missing outputs.">
                Accuracy
              </span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {run.accuracy !== null && run.accuracy !== undefined ? `${run.accuracy.toFixed(1)}%` : 'N/A'}
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {run.passed_cases}/{run.total_cases} total executed
              </div>
            </div>

            {/* Error Rate */}
            <div className="gauge-card p-3.5 border-amber-500/20">
              <span className="text-[10px] font-mono uppercase text-amber-400 font-semibold" title="Numerator: errored cases. Denominator: total executed cases.">
                Error Rate
              </span>
              <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                {run.error_rate !== null && run.error_rate !== undefined ? `${run.error_rate.toFixed(1)}%` : '0.0%'}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">
                {run.errored_cases} errors ({run.unscored_cases} unscored)
              </div>
            </div>

            {/* Dataset Coverage */}
            <div className="gauge-card p-3.5 border-slate-700">
              <span className="text-[10px] font-mono uppercase text-slate-300 font-semibold" title="Numerator: executed cases. Denominator: total cases defined in dataset.">
                Coverage
              </span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {run.dataset_coverage !== null && run.dataset_coverage !== undefined ? `${run.dataset_coverage.toFixed(1)}%` : '100%'}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">
                {run.total_cases} cases evaluated
              </div>
            </div>

            {/* Total Tokens Telemetry */}
            <div className="gauge-card p-3.5 border-indigo-500/20">
              <span className="text-[10px] font-mono uppercase text-indigo-400 font-semibold">
                Tokens
              </span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {run.total_tokens !== null && run.total_tokens !== undefined ? run.total_tokens.toLocaleString() : 'N/A'}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">
                {run.prompt_tokens ? `${run.prompt_tokens} in / ${run.completion_tokens || 0} out` : 'Measured / est'}
              </div>
            </div>

            {/* Inference Cost */}
            <div className="gauge-card p-3.5 border-slate-700">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold">
                Cost (USD)
              </span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {run.total_cost_usd !== null && run.total_cost_usd !== undefined ? `$${run.total_cost_usd.toFixed(4)}` : 'Unknown'}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">
                {run.total_cost_usd !== null && run.total_cost_usd !== undefined ? 'Provider pricing' : 'Pricing unavailable'}
              </div>
            </div>
          </div>

          {/* Latency & Diagnostics Banner */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-6 text-xs font-mono text-slate-300">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-400" />
                <span>Avg Latency:</span>
                <span className="text-white font-bold">{run.avg_latency_ms !== null ? `${run.avg_latency_ms} ms` : 'N/A'}</span>
              </div>
              <div className="hidden sm:flex items-center gap-2">
                <span>Min / Max:</span>
                <span className="text-white font-bold">
                  {run.min_latency_ms !== null ? `${run.min_latency_ms} / ${run.max_latency_ms} ms` : 'N/A'}
                </span>
              </div>
              <div className="hidden sm:flex items-center gap-2">
                <span>P95:</span>
                <span className="text-white font-bold">{run.p95_latency_ms !== null ? `${run.p95_latency_ms} ms` : 'N/A'}</span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
              <Info className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
              <span>Snapshot version: {run.dataset_version || 'v1.0.0'}. Scored via {run.scoring_config || 'per-case method'}.</span>
            </div>
          </div>

          {/* Results Section Header & Filter */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-white">
                  Test Case Results ({filteredResults.length} / {results.length})
                </h3>
              </div>

              {/* Status Filters */}
              <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono">
                {[
                  { key: 'all', label: `All (${results.length})` },
                  { key: 'passed', label: `Passed (${run.passed_cases})` },
                  { key: 'failed', label: `Failed (${run.failed_cases})` },
                  { key: 'error', label: `Error (${run.errored_cases})` },
                  { key: 'unscored', label: `Unscored (${run.unscored_cases})` },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setFilterStatus(item.key)}
                    className={`px-2.5 py-1 rounded-md transition-colors ${
                      filterStatus === item.key
                        ? 'bg-indigo-600 text-white font-semibold'
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Search within results */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search prompts, expected outputs, or actual responses..."
                className="gauge-input pl-9 text-xs"
              />
            </div>

            {/* Results List */}
            {results.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs gauge-card">
                No test cases were executed in this run (dataset was empty).
              </div>
            ) : filteredResults.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs gauge-card">
                No test cases match the filter "{filterStatus}" and query "{searchQuery}".
              </div>
            ) : (
              <div className="space-y-3">
                {filteredResults.map((res) => {
                  let meta: any = null;
                  if (res.metadata_json) {
                    try {
                      meta = JSON.parse(res.metadata_json);
                    } catch {}
                  }

                  return (
                  <div
                    key={res.id}
                    className={`gauge-card p-4 space-y-3 border transition-colors ${
                      res.status === 'passed'
                        ? 'border-emerald-500/20 hover:border-emerald-500/40 bg-emerald-500/[0.02]'
                        : res.status === 'failed'
                        ? 'border-rose-500/20 hover:border-rose-500/40 bg-rose-500/[0.02]'
                        : res.status === 'error'
                        ? 'border-amber-500/20 hover:border-amber-500/40 bg-amber-500/[0.02]'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase tracking-wider ${
                            res.status === 'passed'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : res.status === 'failed'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : res.status === 'error'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-slate-700 text-slate-300'
                          }`}
                        >
                          {res.status}
                        </span>
                        <span className="font-mono text-slate-300 font-semibold">
                          {res.case_identifier}
                        </span>
                        {res.scoring_method && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20" title="Applied scoring method">
                            {res.scoring_method}
                          </span>
                        )}
                        {res.score !== null && res.score !== undefined && (
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${
                            res.score >= 1.0 ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' :
                            res.score > 0.0 ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' :
                            'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                          }`} title="Calculated score (0.00 to 1.00)">
                            score: {res.score.toFixed(2)}
                          </span>
                        )}
                        {meta?.category && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            {meta.category}
                          </span>
                        )}
                        {meta?.difficulty && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            {meta.difficulty}
                          </span>
                        )}
                        {meta?.model && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            {meta.provider ? `${meta.provider}/` : ''}{meta.model}
                          </span>
                        )}
                        {!res.is_mock && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                            live
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-slate-400">
                        {res.latency_ms !== null && (
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3 text-slate-500" />
                            {res.latency_ms} ms
                          </span>
                        )}
                        {meta?.groq_timings?.completion_time && (
                          <span
                            className="text-slate-500 text-[10px] border border-slate-800 rounded px-1.5 py-0.5"
                            title={`Queue: ${meta.groq_timings.queue_time || 0}s, Prompt: ${meta.groq_timings.prompt_time || 0}s, Comp: ${meta.groq_timings.completion_time || 0}s`}
                          >
                            infer: {(meta.groq_timings.completion_time * 1000).toFixed(0)}ms
                          </span>
                        )}
                        {res.token_usage !== null && (
                          <span
                            className={`flex items-center gap-1 ${res.tokens_estimated ? 'text-amber-400/90' : 'text-emerald-400/90'}`}
                            title={res.tokens_estimated ? 'Deterministically estimated token count' : 'Actual provider-reported tokens'}
                          >
                            <Zap className={`w-3 h-3 ${res.tokens_estimated ? 'text-amber-500' : 'text-emerald-400'}`} />
                            {res.tokens_estimated ? `~${res.token_usage} tokens (est)` : `${res.token_usage} tokens (actual)`}
                            {meta?.prompt_tokens !== undefined && meta?.completion_tokens !== undefined && (
                              <span className="text-slate-500 text-[10px]">
                                ({meta.prompt_tokens} in / {meta.completion_tokens} out)
                              </span>
                            )}
                          </span>
                        )}
                        {meta?.cost_usd !== undefined && meta?.cost_usd !== null ? (
                          <span className="text-cyan-400 text-[11px]" title="Calculated inference cost">
                            ${meta.cost_usd < 0.0001 ? meta.cost_usd.toFixed(6) : meta.cost_usd.toFixed(4)}
                          </span>
                        ) : !res.is_mock ? (
                          <span className="text-slate-500 text-[10px]" title="Cost unavailable for this model configuration">
                            cost: N/A
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {/* Input Prompt */}
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold">
                        Input Prompt
                      </span>
                      <div className="p-2.5 rounded bg-[#070A10] border border-slate-800 text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap">
                        {res.input_prompt}
                      </div>
                    </div>

                    {/* Expected vs Actual Outputs */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {/* Expected */}
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold">
                          Expected Output
                        </span>
                        <div className="p-2.5 rounded bg-[#070A10] border border-slate-800 font-mono text-slate-300 min-h-[3rem] whitespace-pre-wrap">
                          {res.expected_output !== null && res.expected_output !== '' ? (
                            res.expected_output
                          ) : (
                            <span className="text-slate-600 italic">No expected output provided (Unscored)</span>
                          )}
                        </div>
                      </div>

                      {/* Actual */}
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-mono text-slate-500 font-semibold">
                          Actual Agent Output
                        </span>
                        <div
                          className={`p-2.5 rounded font-mono min-h-[3rem] whitespace-pre-wrap ${
                            res.status === 'passed'
                              ? 'bg-emerald-500/5 border border-emerald-500/30 text-emerald-200'
                              : res.status === 'failed'
                              ? 'bg-rose-500/5 border border-rose-500/30 text-rose-200'
                              : res.status === 'error'
                              ? 'bg-amber-500/5 border border-amber-500/30 text-amber-200'
                              : 'bg-[#070A10] border border-slate-800 text-slate-300'
                          }`}
                        >
                          {res.actual_output || <span className="text-slate-600 italic">No output received</span>}
                        </div>
                      </div>
                    </div>

                    {/* Error diagnostic box if applicable */}
                    {res.error_message && (
                      <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-mono flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold">Execution Error: </span>
                          <span>{res.error_message}</span>
                        </div>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-[#0B0F17]/90 flex items-center justify-between text-xs text-slate-400 font-mono">
          <span>Run ID: {run.id}</span>
          <button onClick={onClose} className="gauge-btn-secondary py-1.5 px-4 text-xs">
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
