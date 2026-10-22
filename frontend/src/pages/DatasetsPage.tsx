import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Database,
  Plus,
  Search,
  Calendar,
  Layers,
  AlertCircle,
  Copy,
  Check,
  Upload,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { api } from '../services/api';
import { EvaluationDataset, HealthResponse } from '../types/api';
import { EmptyState } from '../components/EmptyState';
import { CreateDatasetModal } from '../components/CreateDatasetModal';
import { ImportDatasetModal } from '../components/ImportDatasetModal';

export const DatasetsPage: React.FC = () => {
  const { refreshTrigger } = useOutletContext<{ refreshTrigger: number; health: HealthResponse | null }>();

  const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDatasets();
      setDatasets(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch evaluation datasets from backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets, refreshTrigger]);

  const handleCopy = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSeedCurated = async () => {
    setSeeding(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const seeded = await api.seedCuratedDataset();
      setSuccessMessage(`Curated benchmark suite "${seeded.name}" (${seeded.version}) ready with ${seeded.test_cases_count} cases.`);
      fetchDatasets();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setError(err.message || 'Failed to seed curated benchmark dataset.');
    } finally {
      setSeeding(false);
    }
  };

  const filteredDatasets = datasets.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.description && d.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
    d.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Page Header Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search datasets by name or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="gauge-input pl-10"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
          <button
            onClick={handleSeedCurated}
            disabled={seeding}
            className="gauge-btn-secondary text-xs flex items-center gap-1.5 border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10"
            title="Seed curated 36-case benchmark suite (Math, Logic, JSON, Multi-part)"
          >
            {seeding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-indigo-400" />}
            <span>Seed Curated Suite</span>
          </button>

          <button
            onClick={() => setIsImportModalOpen(true)}
            className="gauge-btn-secondary text-xs flex items-center gap-1.5"
            title="Import benchmark dataset from raw JSON or JSONL format"
          >
            <Upload className="w-3.5 h-3.5 text-cyan-400" />
            <span>Import JSON / JSONL</span>
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="gauge-btn-primary text-xs flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Dataset</span>
          </button>
        </div>
      </div>

      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2 font-mono">
          <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Failed to load datasets</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Datasets Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="gauge-card p-5 space-y-3 animate-pulse">
              <div className="h-5 bg-slate-800 rounded w-1/2" />
              <div className="h-4 bg-slate-800 rounded w-3/4" />
              <div className="h-4 bg-slate-800 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : datasets.length === 0 ? (
        <EmptyState
          icon={<Database className="w-6 h-6" />}
          title="No Evaluation Datasets Found"
          description="Evaluation datasets contain prompt inputs, expected tool calls, or reference answers to benchmark agent versions against."
          actionLabel="Create First Dataset"
          onAction={() => setIsModalOpen(true)}
        />
      ) : filteredDatasets.length === 0 ? (
        <div className="gauge-card p-8 text-center text-slate-400 text-sm">
          No datasets match your search query "{searchQuery}".
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredDatasets.map((dataset) => (
            <div
              key={dataset.id}
              className="gauge-card p-5 gauge-card-hover flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    <Database className="w-4 h-4" />
                  </div>
                  <button
                    onClick={() => handleCopy(dataset.id)}
                    title="Copy Dataset ID"
                    className="text-slate-500 hover:text-slate-300 p-1 rounded hover:bg-slate-800 transition-colors flex items-center gap-1 text-[11px] font-mono"
                  >
                    {copiedId === dataset.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                    <span>{dataset.id.slice(0, 8)}...</span>
                  </button>
                </div>

                <div className="flex items-center gap-2 mt-3">
                  <h3 className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
                    {dataset.name}
                  </h3>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                    {dataset.version || 'v1.0.0'}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1.5 line-clamp-3 leading-relaxed">
                  {dataset.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-600" />
                  {new Date(dataset.created_at).toLocaleDateString()}
                </span>
                <span className="flex items-center gap-1 text-indigo-400 font-medium">
                  <Layers className="w-3 h-3" />
                  {dataset.test_cases_count ?? 0} Test Cases
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Dataset Modal */}
      <CreateDatasetModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          fetchDatasets();
        }}
      />

      {/* Import Dataset Modal */}
      <ImportDatasetModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={(imported) => {
          setSuccessMessage(`Dataset "${imported.name}" successfully imported with ${imported.test_cases_count ?? 0} test cases.`);
          fetchDatasets();
          setTimeout(() => setSuccessMessage(null), 5000);
        }}
      />
    </div>
  );
};
