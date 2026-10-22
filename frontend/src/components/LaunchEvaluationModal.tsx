import React, { useState, useEffect } from 'react';
import { X, PlaySquare, AlertCircle, Loader2, Database, Layers, CheckCircle2, Zap } from 'lucide-react';
import { api } from '../services/api';
import { EvaluationDataset, AgentVersion, EvaluationRun } from '../types/api';

interface LaunchEvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (run: EvaluationRun) => void;
}

export const LaunchEvaluationModal: React.FC<LaunchEvaluationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loadingPrereqs, setLoadingPrereqs] = useState(false);

  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [selectedVersionId, setSelectedVersionId] = useState('');
  const [executionMode, setExecutionMode] = useState<'mock' | 'real'>('mock');
  const [scoringConfig, setScoringConfig] = useState<string>('default');
  const [runName, setRunName] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<{ message: string; type: 'duplicate' | 'ratelimit' | 'connection' | 'generic' } | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const loadPrereqs = async () => {
      setLoadingPrereqs(true);
      setError(null);
      try {
        const [dsData, verData] = await Promise.all([
          api.getDatasets(),
          api.getAgentVersions(),
        ]);
        setDatasets(dsData);
        setVersions(verData);

        if (dsData.length > 0) setSelectedDatasetId(dsData[0].id);
        if (verData.length > 0) {
          setSelectedVersionId(verData[0].id);
          // Auto-select execution mode based on agent provider
          if (verData[0].model_provider === 'groq' || verData[0].model_provider === 'openai') {
            setExecutionMode('real');
          } else {
            setExecutionMode('mock');
          }
        }

        const defaultName = `Eval Run - ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        setRunName(defaultName);
      } catch (err: any) {
        setError({
          message: err.message || 'Failed to load datasets and agent versions',
          type: err.isConnectionError ? 'connection' : 'generic',
        });
      } finally {
        setLoadingPrereqs(false);
      }
    };

    loadPrereqs();
  }, [isOpen]);

  if (!isOpen) return null;

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId);
  const selectedVersion = versions.find((v) => v.id === selectedVersionId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDatasetId) {
      setError({ message: 'Please select a benchmark dataset.', type: 'generic' });
      return;
    }
    if (!selectedVersionId) {
      setError({ message: 'Please select a target agent version.', type: 'generic' });
      return;
    }
    if (!runName.trim()) {
      setError({ message: 'Please provide a name for this evaluation run.', type: 'generic' });
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const createdRun = await api.createEvaluationRun({
        name: runName.trim(),
        dataset_id: selectedDatasetId,
        agent_version_id: selectedVersionId,
        execution_mode: executionMode,
        scoring_config: scoringConfig,
      });

      onSuccess(createdRun);
      onClose();
    } catch (err: any) {
      let errType: 'duplicate' | 'ratelimit' | 'connection' | 'generic' = 'generic';
      if (err.status === 409 || err.message?.includes('already running')) {
        errType = 'duplicate';
      } else if (err.status === 429 || err.message?.includes('rate limit')) {
        errType = 'ratelimit';
      } else if (err.isConnectionError || err.message?.includes('Cannot connect')) {
        errType = 'connection';
      }
      setError({
        message: err.message || 'Failed to launch evaluation run',
        type: errType,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-xl gauge-card p-6 shadow-2xl border-slate-700">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <PlaySquare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Launch Benchmark Evaluation</h3>
              <p className="text-xs text-slate-400">Execute test cases against a registered agent version</p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className={`mt-4 p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
            error.type === 'duplicate'
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              : error.type === 'ratelimit'
              ? 'bg-orange-500/10 border-orange-500/30 text-orange-300'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
          }`}>
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">
                {error.type === 'duplicate'
                  ? 'Evaluation In Progress (Conflict)'
                  : error.type === 'ratelimit'
                  ? 'Provider Rate Limit Exceeded'
                  : error.type === 'connection'
                  ? 'Backend Connection Failed'
                  : 'Launch Evaluation Error'}
              </p>
              <p className="mt-0.5 text-[11px] opacity-90">{error.message}</p>
            </div>
          </div>
        )}


        {loadingPrereqs ? (
          <div className="p-12 text-center text-slate-400 text-sm space-y-2">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-indigo-400" />
            <p>Loading available datasets and agent versions...</p>
          </div>
        ) : datasets.length === 0 || versions.length === 0 ? (
          <div className="my-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs space-y-2">
            <p className="font-semibold text-sm">Prerequisites Missing</p>
            <p>
              {datasets.length === 0 && 'You need at least one Evaluation Dataset registered. '}
              {versions.length === 0 && 'You need at least one Agent Version registered.'}
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={onClose}
                className="gauge-btn-secondary text-xs"
              >
                Close and Create Prerequisites First
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Evaluation Run Name <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                value={runName}
                onChange={(e) => setRunName(e.target.value)}
                placeholder="e.g. GSM8K Benchmark - v1.0.0"
                className="gauge-input"
                disabled={isSubmitting}
              />
            </div>

            {/* Select Dataset */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Select Dataset</span> <span className="text-rose-400">*</span>
                </span>
                {selectedDataset && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Version: {selectedDataset.version || 'v1.0.0'}
                  </span>
                )}
              </label>
              <select
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                className="gauge-input"
                disabled={isSubmitting}
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} [{d.version || 'v1.0.0'}] ({d.test_cases_count ?? 0} test cases)
                  </option>
                ))}
              </select>
              {selectedDataset && selectedDataset.test_cases_count === 0 && (
                <p className="text-[11px] text-amber-400 mt-1">
                  Note: This dataset has 0 test cases. The evaluation will complete with 0 eligible cases.
                </p>
              )}
            </div>

            {/* Select Agent Version */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>Select Agent Version</span> <span className="text-rose-400">*</span>
              </label>
              <select
                value={selectedVersionId}
                onChange={(e) => {
                  const verId = e.target.value;
                  setSelectedVersionId(verId);
                  const ver = versions.find((v) => v.id === verId);
                  if (ver && (ver.model_provider === 'groq' || ver.model_provider === 'openai')) {
                    setExecutionMode('real');
                  } else if (ver && ver.model_provider === 'mock') {
                    setExecutionMode('mock');
                  }
                }}
                className="gauge-input"
                disabled={isSubmitting}
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.version} - {v.model_provider}/{v.model_name})
                  </option>
                ))}
              </select>
              {selectedVersion && (
                <p className="text-[11px] text-slate-400 mt-1">
                  Target: <span className="text-slate-200 font-mono">{selectedVersion.model_provider}/{selectedVersion.model_name}</span> ({selectedVersion.version})
                </p>
              )}
            </div>

            {/* Scoring Configuration Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Scoring Configuration Rule
              </label>
              <select
                value={scoringConfig}
                onChange={(e) => setScoringConfig(e.target.value)}
                className="gauge-input text-xs"
                disabled={isSubmitting}
              >
                <option value="default">Per-Case Scoring Method (Recommended: exact, normalized, structured, partial)</option>
                <option value="exact_match">Force Exact Match (Strict trimmed character equivalence)</option>
                <option value="normalized_match">Force Normalized Match (Case, whitespace, numeric & boolean equivalence)</option>
                <option value="structured_output">Force Structured Output (Deep JSON schema & key-value equivalence)</option>
                <option value="partial_credit">Force Partial Credit (Item-set / rubric overlap percentage)</option>
              </select>
              <p className="text-[10px] text-slate-400 mt-1 leading-snug">
                Configures how actual outputs are scored against reference answers. Errored and unscored cases never receive credit.
              </p>
            </div>

            {/* Execution Mode Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Execution Engine</span> <span className="text-rose-400">*</span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setExecutionMode('real')}
                  disabled={isSubmitting}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    executionMode === 'real'
                      ? 'bg-emerald-500/10 border-emerald-500/50 text-white shadow-lg shadow-emerald-500/5'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${executionMode === 'real' ? 'bg-emerald-400 ring-2 ring-emerald-400/30' : 'bg-slate-600'}`} />
                    <span className="font-semibold text-xs text-white">Real Provider API</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                    Live inference via {selectedVersion?.model_provider === 'groq' ? 'Groq' : selectedVersion?.model_provider === 'openai' ? 'OpenAI' : selectedVersion?.model_provider || 'Provider'} ({selectedVersion?.model_name || 'openai/gpt-oss-20b'}). Actual tokens & latency captured.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setExecutionMode('mock')}
                  disabled={isSubmitting}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    executionMode === 'mock'
                      ? 'bg-indigo-500/10 border-indigo-500/50 text-white shadow-lg shadow-indigo-500/5'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${executionMode === 'mock' ? 'bg-indigo-400 ring-2 ring-indigo-400/30' : 'bg-slate-600'}`} />
                    <span className="font-semibold text-xs text-white">Mock Adapter</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                    Deterministic local simulation. Zero API key required, estimated token metrics.
                  </p>
                </button>
              </div>
            </div>

            {/* Adapter Execution Notice */}
            <div className={`p-3 rounded-lg border text-xs ${
              executionMode === 'real'
                ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300'
                : 'bg-indigo-500/5 border-indigo-500/20 text-indigo-300'
            }`}>
              <div className="font-semibold flex items-center gap-1.5">
                <CheckCircle2 className={`w-3.5 h-3.5 ${executionMode === 'real' ? 'text-emerald-400' : 'text-indigo-400'}`} />
                <span>
                  {executionMode === 'real'
                    ? `Real LLM Provider Execution (${selectedVersion?.model_provider === 'groq' ? 'Groq' : selectedVersion?.model_provider === 'openai' ? 'OpenAI' : 'Live API'})`
                    : 'Deterministic Mock Execution Engine'}
                </span>
              </div>
              <p className="text-slate-400 mt-1 text-[11px] leading-relaxed">
                {executionMode === 'real'
                  ? `Cases will be executed against the live ${selectedVersion?.model_provider === 'groq' ? 'Groq' : 'OpenAI'} model (${selectedVersion?.model_name || 'configured'}). Exact prompt & completion tokens, wall-clock latency, and available costs will be recorded. If the provider rejects credentials or times out, errors are strictly recorded without falling back to mock.`
                  : 'Cases will be evaluated via the deterministic mock adapter. Execution latency will be measured, token counts estimated, and exact-match correctness scored.'}
              </p>
            </div>

            <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="gauge-btn-secondary"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="gauge-btn-primary"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Executing Evaluation...</span>
                  </>
                ) : (
                  <>
                    <PlaySquare className="w-4 h-4" />
                    <span>Start Evaluation</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
