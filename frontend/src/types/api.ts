export interface DBHealthStatus {
  connected: boolean;
  message: string;
  dialect?: string | null;
}

export interface LLMProviderStatus {
  provider: string;
  model: string;
  api_key_configured: boolean;
  default_execution_mode: string;
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'unhealthy';
  service: string;
  version: string;
  environment: string;
  database: DBHealthStatus;
  llm_provider?: LLMProviderStatus | null;
  timestamp: string;
}

export interface EvaluationTestCase {
  id: string;
  dataset_id: string;
  case_identifier: string;
  input_prompt: string;
  expected_output: string | null;
  criteria: string | null;
  category?: string | null;
  difficulty?: string | null;
  scoring_method?: string | null;
  metadata_json: string | null;
  created_at: string;
}

export interface EvaluationTestCaseCreate {
  case_identifier?: string;
  input_prompt: string;
  expected_output?: string | null;
  criteria?: string | null;
  category?: string | null;
  difficulty?: string | null;
  scoring_method?: string | null;
  metadata_json?: string | null;
}

export interface EvaluationDataset {
  id: string;
  name: string;
  description: string | null;
  version: string;
  created_at: string;
  updated_at: string;
  test_cases_count?: number;
  test_cases?: EvaluationTestCase[] | null;
}

export interface EvaluationDatasetCreate {
  name: string;
  description?: string | null;
  version?: string;
  test_cases?: EvaluationTestCaseCreate[] | null;
}

export interface AgentVersion {
  id: string;
  name: string;
  version: string;
  model_provider: string;
  model_name: string;
  prompt_text: string | null;
  created_at: string;
}

export interface AgentVersionCreate {
  name: string;
  version: string;
  model_provider: string;
  model_name: string;
  prompt_text?: string | null;
}

export interface EvaluationResult {
  id: string;
  run_id: string;
  test_case_id: string | null;
  case_identifier: string;
  input_prompt: string;
  expected_output: string | null;
  actual_output: string | null;
  status: 'passed' | 'failed' | 'error' | 'unscored';
  score?: number | null;
  scoring_method?: string | null;
  latency_ms: number | null;
  token_usage: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  tokens_estimated: boolean;
  cost_usd?: number | null;
  model_provider?: string | null;
  model_name?: string | null;
  error_message: string | null;
  is_mock: boolean;
  metadata_json: string | null;
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  dataset_id: string;
  agent_version_id: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;

  // Snapshot & Provenance
  dataset_version?: string | null;
  dataset_snapshot_json?: string | null;
  scoring_config?: string | null;
  model_provider?: string | null;
  model_name?: string | null;

  // Metrics
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  errored_cases: number;
  unscored_cases: number;
  pass_rate: number | null;
  accuracy?: number | null;
  error_rate?: number | null;
  dataset_coverage?: number | null;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  p95_latency_ms: number | null;

  // Telemetry
  total_cost_usd?: number | null;
  total_tokens?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;

  error_message: string | null;
  results?: EvaluationResult[];
}

export interface EvaluationRunCreate {
  name: string;
  dataset_id: string;
  agent_version_id: string;
  execution_mode?: 'real' | 'mock' | 'auto';
  scoring_config?: string | null;
}

export interface DashboardSummary {
  datasets_count: number;
  versions_count: number;
  total_runs_count: number;
  latest_run_status: string | null;
  database_connected: boolean;
  database_message: string;
  recent_runs: EvaluationRun[];
}

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// Day 3: Baseline & Comparison Types

export interface EvaluationBaseline {
  id: string;
  dataset_id: string;
  run_id: string;
  agent_version_id: string;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
  run_name?: string | null;
  agent_name?: string | null;
  agent_version?: string | null;
  pass_rate?: number | null;
}

export interface EvaluationBaselineCreate {
  dataset_id: string;
  run_id: string;
  notes?: string | null;
}

export interface RegressionThresholds {
  pass_rate_decline_threshold?: number;
  latency_increase_threshold_ms?: number;
  p95_latency_increase_threshold_ms?: number;
  error_count_increase_threshold?: number;
  pass_rate_improvement_threshold?: number;
}

export interface CaseComparisonResult {
  case_identifier: string;
  input_prompt: string;
  expected_output: string | null;
  baseline_status: 'passed' | 'failed' | 'error' | 'unscored' | null;
  candidate_status: 'passed' | 'failed' | 'error' | 'unscored' | null;
  baseline_score?: number | null;
  candidate_score?: number | null;
  scoring_method?: string | null;
  outcome_change:
    | 'newly_failing'
    | 'fixed'
    | 'newly_errored'
    | 'newly_unscored'
    | 'persistent_failure'
    | 'persistent_pass'
    | 'added'
    | 'removed'
    | 'unchanged';
  baseline_latency_ms: number | null;
  candidate_latency_ms: number | null;
  latency_delta_ms: number | null;
  baseline_output: string | null;
  candidate_output: string | null;
}

export interface EvaluationComparison {
  id: string;
  dataset_id: string;
  baseline_run_id: string;
  candidate_run_id: string;
  status: 'improved' | 'regressed' | 'unchanged' | 'mixed' | 'inconclusive';
  is_compatible: boolean;
  compatibility_notes: string | null;
  pass_rate_delta: number | null;
  accuracy_delta?: number | null;
  passed_cases_delta: number;
  failed_cases_delta: number;
  errored_cases_delta: number;
  unscored_cases_delta: number;
  avg_latency_ms_delta: number | null;
  p95_latency_ms_delta: number | null;
  cost_usd_delta?: number | null;
  tokens_delta?: number | null;
  newly_failing_count: number;
  newly_fixed_count: number;
  newly_errored_count: number;
  newly_unscored_count: number;
  total_cases_baseline: number;
  total_cases_candidate: number;
  reasons: string[];
  created_at: string;
  baseline_run_name?: string | null;
  candidate_run_name?: string | null;
  baseline_agent_name?: string | null;
  candidate_agent_name?: string | null;
  baseline_agent_version?: string | null;
  candidate_agent_version?: string | null;
  baseline_pass_rate?: number | null;
  candidate_pass_rate?: number | null;
  baseline_avg_latency_ms?: number | null;
  candidate_avg_latency_ms?: number | null;
  case_comparisons?: CaseComparisonResult[];
}

export interface EvaluationComparisonCreate {
  candidate_run_id: string;
  baseline_run_id?: string | null;
  thresholds?: RegressionThresholds;
}

export interface RegressionFindings {
  comparison_id: string;
  status: 'improved' | 'regressed' | 'unchanged' | 'mixed' | 'inconclusive';
  is_compatible: boolean;
  reasons: string[];
  pass_rate_delta: number | null;
  avg_latency_ms_delta: number | null;
  newly_failing_count: number;
  newly_errored_count: number;
  newly_unscored_count: number;
  newly_failing_cases: CaseComparisonResult[];
  newly_errored_cases: CaseComparisonResult[];
  newly_unscored_cases: CaseComparisonResult[];
}
