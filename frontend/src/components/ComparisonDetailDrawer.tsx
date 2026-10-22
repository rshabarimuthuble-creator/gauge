import React, { useState } from 'react';
import {
  X,
  GitCompare,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  HelpCircle,
  Search,
  ArrowRight,
  Info,
  Calendar,
} from 'lucide-react';
import { EvaluationComparison, CaseComparisonResult } from '../types/api';

interface ComparisonDetailDrawerProps {
  comparison: EvaluationComparison | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ComparisonDetailDrawer: React.FC<ComparisonDetailDrawerProps> = ({
  comparison,
  isOpen,
  onClose,
}) => {
  const [filterOutcome, setFilterOutcome] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  if (!isOpen || !comparison) return null;

  const cases: CaseComparisonResult[] = comparison.case_comparisons || [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'improved':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <TrendingUp className="w-3.5 h-3.5" />
            Improved
          </span>
        );
      case 'regressed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <TrendingDown className="w-3.5 h-3.5" />
            Regressed
          </span>
        );
      case 'mixed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" />
            Mixed
          </span>
        );
      case 'unchanged':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <Minus className="w-3.5 h-3.5" />
            Unchanged
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/15 text-slate-400 border border-slate-500/30">
            <HelpCircle className="w-3.5 h-3.5" />
            Inconclusive
          </span>
        );
    }
  };

  const formatDeltaMs = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return 'N/A';
    if (Math.abs(val) < 0.005) return '0.00 ms';
    return `${val > 0 ? '+' : ''}${val.toFixed(2)} ms`;
  };

  const formatDeltaPp = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return 'N/A';
    if (Math.abs(val) < 0.005) return '0.0 pp';
    return `${val > 0 ? '+' : ''}${val.toFixed(1)} pp`;
  };

  const filteredCases = cases.filter((c) => {
    const matchesFilter = filterOutcome === 'all' || c.outcome_change === filterOutcome;
    const matchesSearch =
      c.case_identifier.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.input_prompt.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.candidate_output && c.candidate_output.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.baseline_output && c.baseline_output.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  const isMockExecution = comparison.reasons.some((r) => r.includes('Mock execution detected'));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-6xl h-[92vh] gauge-card p-0 shadow-2xl border-slate-700 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-[#0B0F17]/90">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <GitCompare className="w-5 h-5 text-cyan-400" />
                Benchmark Comparison Analysis
              </h2>
              {getStatusBadge(comparison.status)}
              {isMockExecution && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  Mock Adapter Validated
                </span>
              )}
            </div>

            {/* Run pairing info */}
            <div className="flex flex-wrap items-center gap-4 mt-2.5 text-xs font-mono text-slate-300">
              <div className="flex items-center gap-1.5 bg-[#111827] px-2.5 py-1 rounded border border-slate-800">
                <span className="text-slate-500">Baseline:</span>
                <span className="text-white font-semibold">
                  {comparison.baseline_run_name || comparison.baseline_run_id.slice(0, 8)}
                </span>
                {comparison.baseline_agent_version && (
                  <span className="text-cyan-400">({comparison.baseline_agent_version})</span>
                )}
              </div>

              <ArrowRight className="w-4 h-4 text-slate-600" />

              <div className="flex items-center gap-1.5 bg-[#111827] px-2.5 py-1 rounded border border-slate-800">
                <span className="text-slate-500">Candidate:</span>
                <span className="text-white font-semibold">
                  {comparison.candidate_run_name || comparison.candidate_run_id.slice(0, 8)}
                </span>
                {comparison.candidate_agent_version && (
                  <span className="text-cyan-400">({comparison.candidate_agent_version})</span>
                )}
              </div>

              <span className="text-slate-500 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {new Date(comparison.created_at).toLocaleString()}
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Compatibility Alert Banner if Incompatible */}
          {!comparison.is_compatible && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-rose-200">Dataset / Version Incompatibility Detected</p>
                <p className="mt-0.5 opacity-90 leading-relaxed">
                  {comparison.compatibility_notes || 'The compared runs used different dataset versions, test case sets, or scoring configurations. Treat aggregate comparisons with caution.'}
                </p>
              </div>
            </div>
          )}

          {/* Mock Execution Warning / Note if applicable */}
          {isMockExecution && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-3">
              <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Mock Pipeline Validation Notice</p>
                <p className="mt-0.5 opacity-90">
                  Deterministic mock adapter was executed for both runs. This comparison validates regression threshold logic, metric delta arithmetic, and pipeline integrity without real LLM inference.
                </p>
              </div>
            </div>
          )}

          {/* Metric Deltas Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Pass Rate Delta */}
            <div className="gauge-card p-3.5 border-emerald-500/20">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold block" title="Candidate pass rate minus baseline pass rate (eligible denominator)">
                Pass Rate Δ
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-xl font-bold font-mono ${
                    (comparison.pass_rate_delta ?? 0) > 0
                      ? 'text-emerald-400'
                      : (comparison.pass_rate_delta ?? 0) < 0
                      ? 'text-rose-400'
                      : 'text-slate-200'
                  }`}
                >
                  {formatDeltaPp(comparison.pass_rate_delta)}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono flex items-center justify-between">
                <span>Base: {comparison.baseline_pass_rate ?? 0}%</span>
                <span>Cand: {comparison.candidate_pass_rate ?? 0}%</span>
              </div>
            </div>

            {/* Accuracy Delta */}
            <div className="gauge-card p-3.5 border-cyan-500/20">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold block" title="Strict accuracy delta (passed / total cases)">
                Accuracy Δ
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-xl font-bold font-mono ${
                    (comparison.accuracy_delta ?? 0) > 0
                      ? 'text-emerald-400'
                      : (comparison.accuracy_delta ?? 0) < 0
                      ? 'text-rose-400'
                      : 'text-slate-200'
                  }`}
                >
                  {formatDeltaPp(comparison.accuracy_delta)}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {comparison.passed_cases_delta > 0 ? `+${comparison.passed_cases_delta}` : comparison.passed_cases_delta} passed cases
              </div>
            </div>

            {/* Average Latency Delta */}
            <div className="gauge-card p-3.5">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold block">
                Avg Latency Δ
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-xl font-bold font-mono ${
                    (comparison.avg_latency_ms_delta ?? 0) > 0
                      ? 'text-rose-400'
                      : (comparison.avg_latency_ms_delta ?? 0) < 0
                      ? 'text-emerald-400'
                      : 'text-slate-200'
                  }`}
                >
                  {formatDeltaMs(comparison.avg_latency_ms_delta)}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono flex items-center justify-between">
                <span>Base: {comparison.baseline_avg_latency_ms ?? 0}ms</span>
                <span>Cand: {comparison.candidate_avg_latency_ms ?? 0}ms</span>
              </div>
            </div>

            {/* Error Count Delta */}
            <div className="gauge-card p-3.5">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold block">
                Errors Δ
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-xl font-bold font-mono ${
                    comparison.errored_cases_delta > 0
                      ? 'text-rose-400'
                      : comparison.errored_cases_delta < 0
                      ? 'text-emerald-400'
                      : 'text-slate-200'
                  }`}
                >
                  {comparison.errored_cases_delta > 0 ? `+${comparison.errored_cases_delta}` : comparison.errored_cases_delta}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {comparison.newly_errored_count} newly errored
              </div>
            </div>

            {/* Tokens Delta */}
            <div className="gauge-card p-3.5">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold block">
                Tokens Δ
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-xl font-bold font-mono ${
                    (comparison.tokens_delta ?? 0) > 0
                      ? 'text-amber-400'
                      : (comparison.tokens_delta ?? 0) < 0
                      ? 'text-emerald-400'
                      : 'text-slate-200'
                  }`}
                >
                  {comparison.tokens_delta !== null && comparison.tokens_delta !== undefined
                    ? `${comparison.tokens_delta > 0 ? '+' : ''}${comparison.tokens_delta}`
                    : 'N/A'}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                Telemetry diff
              </div>
            </div>

            {/* Cost Delta */}
            <div className="gauge-card p-3.5">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold block">
                Cost Δ (USD)
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-xl font-bold font-mono ${
                    (comparison.cost_usd_delta ?? 0) > 0
                      ? 'text-amber-400'
                      : (comparison.cost_usd_delta ?? 0) < 0
                      ? 'text-emerald-400'
                      : 'text-slate-200'
                  }`}
                >
                  {comparison.cost_usd_delta !== null && comparison.cost_usd_delta !== undefined
                    ? `${comparison.cost_usd_delta > 0 ? '+' : ''}$${comparison.cost_usd_delta.toFixed(4)}`
                    : 'Unknown'}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                Known pricing only
              </div>
            </div>
          </div>

          {/* Explanatory Reasons & Empirical Variance Notice */}
          <div className="gauge-card p-5 border-slate-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Regression Classification Findings
            </h3>
            <ul className="space-y-1.5 text-xs text-slate-300">
              {comparison.reasons.map((reason, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-cyan-400 mt-1">•</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Per-Case Comparisons Table */}
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-white">Per-Case Outcome Comparison</h3>
                <p className="text-xs text-slate-400">
                  {filteredCases.length} of {cases.length} cases shown
                </p>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Search prompt or case..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 pr-3 py-1.5 bg-[#111827] border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <select
                  value={filterOutcome}
                  onChange={(e) => setFilterOutcome(e.target.value)}
                  className="bg-[#111827] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="all">All Outcomes</option>
                  <option value="newly_failing">Newly Failing ({comparison.newly_failing_count})</option>
                  <option value="fixed">Newly Fixed ({comparison.newly_fixed_count})</option>
                  <option value="newly_errored">Newly Errored ({comparison.newly_errored_count})</option>
                  <option value="persistent_failure">Persistent Failures</option>
                  <option value="persistent_pass">Persistent Passes</option>
                  <option value="unchanged">Unchanged</option>
                </select>
              </div>
            </div>

            {/* Cases List */}
            <div className="gauge-card p-0 overflow-hidden border-slate-800">
              <div className="divide-y divide-slate-800/80">
                {filteredCases.map((c) => {
                  const isNewlyFailing = c.outcome_change === 'newly_failing';
                  const isFixed = c.outcome_change === 'fixed';
                  const isNewlyErrored = c.outcome_change === 'newly_errored';

                  return (
                    <div
                      key={c.case_identifier}
                      className={`p-4 transition-colors hover:bg-slate-800/40 ${
                        isNewlyFailing
                          ? 'bg-rose-500/5'
                          : isFixed
                          ? 'bg-emerald-500/5'
                          : isNewlyErrored
                          ? 'bg-amber-500/5'
                          : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-semibold text-cyan-400">
                              {c.case_identifier}
                            </span>
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                                isNewlyFailing
                                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                  : isFixed
                                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                  : isNewlyErrored
                                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {c.outcome_change.replace('_', ' ')}
                            </span>
                            {c.scoring_method && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                                {c.scoring_method}
                              </span>
                            )}
                            {(c.baseline_score !== null || c.candidate_score !== null) && (
                              <span className="text-[10px] font-mono text-slate-400">
                                score: {c.baseline_score !== null && c.baseline_score !== undefined ? c.baseline_score.toFixed(2) : '—'} → {c.candidate_score !== null && c.candidate_score !== undefined ? c.candidate_score.toFixed(2) : '—'}
                              </span>
                            )}
                          </div>

                          <p className="text-xs text-slate-300 font-mono line-clamp-2">
                            Prompt: {c.input_prompt}
                          </p>
                        </div>

                        {/* Status Delta Comparison */}
                        <div className="flex items-center gap-3 text-xs font-mono">
                          <div className="text-right">
                            <span className="text-[10px] text-slate-500 block">Baseline</span>
                            <span
                              className={
                                c.baseline_status === 'passed'
                                  ? 'text-emerald-400'
                                  : c.baseline_status === 'failed'
                                  ? 'text-rose-400'
                                  : 'text-slate-400'
                              }
                            >
                              {c.baseline_status || 'absent'}
                            </span>
                          </div>

                          <ArrowRight className="w-3.5 h-3.5 text-slate-600" />

                          <div>
                            <span className="text-[10px] text-slate-500 block">Candidate</span>
                            <span
                              className={
                                c.candidate_status === 'passed'
                                  ? 'text-emerald-400'
                                  : c.candidate_status === 'failed'
                                  ? 'text-rose-400'
                                  : 'text-slate-400'
                              }
                            >
                              {c.candidate_status || 'absent'}
                            </span>
                          </div>

                          {c.latency_delta_ms !== null && (
                            <div className="pl-2 border-l border-slate-800 text-right">
                              <span className="text-[10px] text-slate-500 block">Δ Latency</span>
                              <span
                                className={
                                  c.latency_delta_ms > 0
                                    ? 'text-rose-400'
                                    : c.latency_delta_ms < 0
                                    ? 'text-emerald-400'
                                    : 'text-slate-400'
                                }
                              >
                                {formatDeltaMs(c.latency_delta_ms)}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Outputs comparison if failing/fixed */}
                      {(isNewlyFailing || isFixed || isNewlyErrored) && (
                        <div className="mt-3 pt-3 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px] font-mono">
                          <div className="p-2.5 rounded bg-[#0B0F17] border border-slate-800">
                            <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                              Baseline Output
                            </span>
                            <p className="text-slate-300 mt-1 break-words">
                              {c.baseline_output || '—'}
                            </p>
                          </div>
                          <div className="p-2.5 rounded bg-[#0B0F17] border border-slate-800">
                            <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                              Candidate Output
                            </span>
                            <p className="text-slate-300 mt-1 break-words">
                              {c.candidate_output || '—'}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
