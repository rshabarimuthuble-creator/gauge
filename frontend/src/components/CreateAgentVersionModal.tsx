import React, { useState } from 'react';
import { X, Cpu, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { AgentVersion } from '../types/api';

interface CreateAgentVersionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (version: AgentVersion) => void;
}

export const CreateAgentVersionModal: React.FC<CreateAgentVersionModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState('');
  const [version, setVersion] = useState('v1.0.0');
  const [modelProvider, setModelProvider] = useState('groq');
  const [modelName, setModelName] = useState('openai/gpt-oss-20b');
  const [promptText, setPromptText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleProviderChange = (provider: string) => {
    setModelProvider(provider);
    if (provider === 'groq') setModelName('openai/gpt-oss-20b');
    else if (provider === 'openai') setModelName('gpt-4o');
    else if (provider === 'anthropic') setModelName('claude-3-5-sonnet-20241022');
    else if (provider === 'google') setModelName('gemini-1.5-pro');
    else if (provider === 'meta') setModelName('llama-3.3-70b-instruct');
    else if (provider === 'local') setModelName('qwen2.5-coder:32b');
    else if (provider === 'mock') setModelName('deterministic-mock');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !version.trim() || !modelProvider.trim() || !modelName.trim()) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const created = await api.createAgentVersion({
        name: name.trim(),
        version: version.trim(),
        model_provider: modelProvider.trim(),
        model_name: modelName.trim(),
        prompt_text: promptText.trim() || null,
      });
      setName('');
      setPromptText('');
      onSuccess(created);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to register agent version');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="relative w-full max-w-lg gauge-card p-6 shadow-2xl border-slate-700">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Register Agent Version</h3>
              <p className="text-xs text-slate-400">Snapshot an agent system prompt, provider, and model</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Agent Name <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Code Assistant"
                className="gauge-input"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Version Tag <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="e.g. v1.0.0"
                className="gauge-input font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Model Provider <span className="text-rose-400">*</span>
              </label>
              <select
                value={modelProvider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="gauge-input"
              >
                <option value="groq">Groq (Ultra-Fast LPUs)</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google Gemini</option>
                <option value="meta">Meta Llama</option>
                <option value="local">Local / Ollama</option>
                <option value="mock">Mock Adapter (Simulation)</option>
                <option value="custom">Custom Provider</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Model Name <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="e.g. gpt-4o"
                className="gauge-input font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              System Prompt / Template <span className="text-slate-500 font-normal">(Optional)</span>
            </label>
            <textarea
              rows={4}
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              placeholder="You are an expert AI assistant specialized in..."
              className="gauge-input font-mono text-xs resize-none"
            />
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="gauge-btn-secondary"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="gauge-btn-primary"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{loading ? 'Registering...' : 'Register Version'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
