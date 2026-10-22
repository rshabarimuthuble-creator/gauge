import {
  HealthResponse,
  DashboardSummary,
  EvaluationDataset,
  EvaluationDatasetCreate,
  EvaluationTestCase,
  EvaluationTestCaseCreate,
  AgentVersion,
  AgentVersionCreate,
  EvaluationRun,
  EvaluationRunCreate,
  EvaluationResult,
  EvaluationBaseline,
  EvaluationBaselineCreate,
  EvaluationComparison,
  EvaluationComparisonCreate,
  RegressionFindings,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit, timeoutMs: number = 15000): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...((options?.headers as Record<string, string>) || {}),
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let detailMessage = '';
        try {
          const errorData = await response.json();
          if (errorData?.detail) {
            detailMessage = typeof errorData.detail === 'string'
              ? errorData.detail
              : JSON.stringify(errorData.detail);
          }
        } catch {
          // Response body was not JSON
        }

        let userFriendlyMessage = detailMessage || `HTTP Error ${response.status}: ${response.statusText}`;

        if (response.status === 429) {
          userFriendlyMessage = detailMessage || 'Provider rate limit exceeded (HTTP 429). Please wait before retrying.';
        } else if (response.status === 409) {
          userFriendlyMessage = detailMessage || 'An evaluation run for this dataset and agent is already in progress.';
        } else if (response.status === 503) {
          userFriendlyMessage = detailMessage || 'Database or downstream service currently unavailable.';
        }

        const httpError = new Error(userFriendlyMessage) as any;
        httpError.status = response.status;
        httpError.statusText = response.statusText;
        httpError.detail = detailMessage;
        throw httpError;
      }

      return (await response.json()) as T;
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        const timeoutErr = new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s while connecting to ${url}`);
        (timeoutErr as any).isTimeout = true;
        throw timeoutErr;
      }
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        const connErr = new Error(`Cannot connect to Gauge backend at ${this.baseUrl}. Please check if the server is running on port 8001.`);
        (connErr as any).isConnectionError = true;
        throw connErr;
      }
      throw error;
    }
  }

  // System Health
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  // Dashboard Overview
  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.request<DashboardSummary>('/api/v1/dashboard/summary');
  }

  // Datasets
  async getDatasets(skip: number = 0, limit: number = 100): Promise<EvaluationDataset[]> {
    return this.request<EvaluationDataset[]>(`/api/v1/datasets?skip=${skip}&limit=${limit}`);
  }

  async getDataset(id: string): Promise<EvaluationDataset> {
    return this.request<EvaluationDataset>(`/api/v1/datasets/${id}`);
  }

  async createDataset(data: EvaluationDatasetCreate): Promise<EvaluationDataset> {
    return this.request<EvaluationDataset>('/api/v1/datasets', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async addTestCase(datasetId: string, data: EvaluationTestCaseCreate): Promise<EvaluationTestCase> {
    return this.request<EvaluationTestCase>(`/api/v1/datasets/${datasetId}/cases`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getDatasetCases(datasetId: string): Promise<EvaluationTestCase[]> {
    return this.request<EvaluationTestCase[]>(`/api/v1/datasets/${datasetId}/cases`);
  }

  async importDataset(content: string, name?: string): Promise<EvaluationDataset> {
    return this.request<EvaluationDataset>('/api/v1/datasets/import', {
      method: 'POST',
      body: JSON.stringify({ content, name }),
    });
  }

  async importCases(datasetId: string, content: string): Promise<EvaluationTestCase[]> {
    return this.request<EvaluationTestCase[]>(`/api/v1/datasets/${datasetId}/import_cases`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }

  async seedCuratedDataset(): Promise<EvaluationDataset> {
    return this.request<EvaluationDataset>('/api/v1/datasets/seed_curated', {
      method: 'POST',
    });
  }

  // Agent Versions
  async getAgentVersions(skip: number = 0, limit: number = 100): Promise<AgentVersion[]> {
    return this.request<AgentVersion[]>(`/api/v1/versions?skip=${skip}&limit=${limit}`);
  }

  async getAgentVersion(id: string): Promise<AgentVersion> {
    return this.request<AgentVersion>(`/api/v1/versions/${id}`);
  }

  async createAgentVersion(data: AgentVersionCreate): Promise<AgentVersion> {
    return this.request<AgentVersion>('/api/v1/versions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Evaluation Runs
  async getEvaluationRuns(skip: number = 0, limit: number = 100): Promise<EvaluationRun[]> {
    return this.request<EvaluationRun[]>(`/api/v1/evaluations?skip=${skip}&limit=${limit}`);
  }

  async getEvaluationRun(id: string): Promise<EvaluationRun> {
    return this.request<EvaluationRun>(`/api/v1/evaluations/${id}`);
  }

  async getEvaluationResults(runId: string, status?: string): Promise<EvaluationResult[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return this.request<EvaluationResult[]>(`/api/v1/evaluations/${runId}/results${query}`);
  }

  async createEvaluationRun(data: EvaluationRunCreate, background: boolean = true): Promise<EvaluationRun> {
    const endpoint = background ? '/api/v1/evaluations?background=true' : '/api/v1/evaluations';
    return this.request<EvaluationRun>(endpoint, {
      method: 'POST',
      body: JSON.stringify({ ...data, background }),
    }, 45000);
  }


  // Day 3: Baselines
  async setBaseline(data: EvaluationBaselineCreate): Promise<EvaluationBaseline> {
    return this.request<EvaluationBaseline>('/api/v1/baselines', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getActiveBaselines(): Promise<EvaluationBaseline[]> {
    return this.request<EvaluationBaseline[]>('/api/v1/baselines');
  }

  async getDatasetBaseline(datasetId: string): Promise<EvaluationBaseline> {
    return this.request<EvaluationBaseline>(`/api/v1/baselines/${datasetId}`);
  }

  async getDatasetBaselineHistory(datasetId: string): Promise<EvaluationBaseline[]> {
    return this.request<EvaluationBaseline[]>(`/api/v1/baselines/${datasetId}/history`);
  }

  // Day 3: Comparisons & Regressions
  async createComparison(data: EvaluationComparisonCreate): Promise<EvaluationComparison> {
    return this.request<EvaluationComparison>('/api/v1/comparisons', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getComparisons(datasetId?: string, skip: number = 0, limit: number = 50): Promise<EvaluationComparison[]> {
    const query = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}&skip=${skip}&limit=${limit}` : `?skip=${skip}&limit=${limit}`;
    return this.request<EvaluationComparison[]>(`/api/v1/comparisons${query}`);
  }

  async getComparison(id: string): Promise<EvaluationComparison> {
    return this.request<EvaluationComparison>(`/api/v1/comparisons/${id}`);
  }

  async getComparisonRegressions(id: string): Promise<RegressionFindings> {
    return this.request<RegressionFindings>(`/api/v1/comparisons/${id}/regressions`);
  }
}

export const api = new ApiService(API_BASE_URL);
