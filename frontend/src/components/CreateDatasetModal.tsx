import React, { useState } from 'react';
import { X, Database, AlertCircle, Loader2, CheckSquare, Square } from 'lucide-react';
import { api } from '../services/api';
import { EvaluationDataset, EvaluationTestCaseCreate } from '../types/api';

interface CreateDatasetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (dataset: EvaluationDataset) => void;
}

export const CreateDatasetModal: React.FC<CreateDatasetModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [includeSamples, setIncludeSamples] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const sampleCases: EvaluationTestCaseCreate[] = [
    {
      case_identifier: 'gsm-01',
      input_prompt: 'A farmer has 45 chickens and buys 20 more. How many chickens does he have in total?',
      expected_output: '65',
      criteria: 'Exact integer matching',
    },
    {
      case_identifier: 'geo-02',
      input_prompt: 'What is the capital city of Japan?',
      expected_output: 'Tokyo',
      criteria: 'Factual retrieval',
    },
    {
      case_identifier: 'logic-03',
      input_prompt: 'Is 15 multiplied by 4 equal to 60? Answer Yes or No.',
      expected_output: 'Yes',
      criteria: 'Boolean response validation',
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Dataset name is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const created = await api.createDataset({
        name: name.trim(),
        description: description.trim() || null,
        test_cases: includeSamples ? sampleCases : [],
      });
      setName('');
      setDescription('');
      onSuccess(created);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create dataset');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-lg gauge-card p-6 shadow-2xl border-slate-700">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Create Evaluation Dataset</h3>
              <p className="text-xs text-slate-400">Register a benchmark dataset for agent test runs</p>
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
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Dataset Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. GSM8K Reasoning Benchmark"
              className="gauge-input"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Description <span className="text-slate-500 font-normal">(Optional)</span>
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide context on test cases, target capabilities, and domain..."
              className="gauge-input resize-none"
            />
          </div>

          {/* Sample test cases option */}
          <div
            onClick={() => setIncludeSamples(!includeSamples)}
            className="p-3 rounded-xl bg-indigo-500/5 border border-indigo-500/20 flex items-start gap-3 cursor-pointer hover:bg-indigo-500/10 transition-colors"
          >
            <div className="mt-0.5 text-indigo-400">
              {includeSamples ? (
                <CheckSquare className="w-4 h-4" />
              ) : (
                <Square className="w-4 h-4 text-slate-500" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white">
                  Include 3 Benchmark Test Cases
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                  Recommended
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                Initializes dataset with sample reasoning and knowledge test cases ready for Day 2 evaluations.
              </p>
            </div>
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
              <span>{loading ? 'Creating...' : 'Create Dataset'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
