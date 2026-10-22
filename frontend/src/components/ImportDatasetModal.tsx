import React, { useState } from 'react';
import { X, Upload, FileText, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { EvaluationDataset } from '../types/api';

interface ImportDatasetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (dataset: EvaluationDataset) => void;
}

export const ImportDatasetModal: React.FC<ImportDatasetModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [content, setContent] = useState('');
  const [datasetName, setDatasetName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setContent(text);
      if (!datasetName && file.name) {
        const cleanName = file.name.replace(/\.(json|jsonl)$/i, '');
        setDatasetName(cleanName);
      }
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      setError('Please provide JSON or JSONL benchmark content to import.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const imported = await api.importDataset(content.trim(), datasetName.trim() || undefined);
      setContent('');
      setDatasetName('');
      onSuccess(imported);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to import benchmark dataset.');
    } finally {
      setLoading(false);
    }
  };

  const sampleJson = `[
  {
    "case_identifier": "MATH-01",
    "input_prompt": "What is 15 * 4?",
    "expected_output": "60",
    "scoring_method": "exact_match",
    "category": "mathematics",
    "difficulty": "easy"
  }
]`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl gauge-card p-6 shadow-2xl border-slate-700 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Import Benchmark Dataset</h3>
              <p className="text-xs text-slate-400">Import structured test cases from JSON or JSONL format</p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-200">Import Validation Failed</p>
              <p className="mt-0.5 leading-relaxed">{error}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4 flex-1 overflow-y-auto pr-1">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Dataset Name <span className="text-slate-500 font-normal">(Optional Override)</span>
            </label>
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g. GSM8K Benchmark v1.0"
              className="gauge-input text-xs"
              disabled={loading}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Raw JSON / JSONL Content <span className="text-rose-400">*</span>
              </label>
              <label className="cursor-pointer text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-mono">
                <FileText className="w-3.5 h-3.5" />
                <span>Upload File</span>
                <input
                  type="file"
                  accept=".json,.jsonl,.txt"
                  className="hidden"
                  onChange={handleFileUpload}
                  disabled={loading}
                />
              </label>
            </div>
            <textarea
              rows={9}
              required
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={`Paste JSON array of cases, or JSONL lines, or an object with "test_cases": [...]\nExample:\n${sampleJson}`}
              className="gauge-input font-mono text-xs leading-relaxed resize-none"
              disabled={loading}
            />
          </div>

          {/* Format Guide */}
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-1 font-mono">
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Supported Import Formats:</span>
            </div>
            <p>1. JSON array of objects: <code className="text-indigo-300">[&#123; "input_prompt": "...", "expected_output": "..." &#125;]</code></p>
            <p>2. JSONL: One case per line with mandatory <code className="text-indigo-300">input_prompt</code></p>
            <p>3. Duplicate case IDs and malformed lines are rejected deterministically with clear error messages.</p>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="gauge-btn-secondary text-xs"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="gauge-btn-primary text-xs"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{loading ? 'Validating & Importing...' : 'Import Dataset'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
