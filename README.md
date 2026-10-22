# Gauge — AI Agent Evaluation & Benchmarking Platform

> **Production-Hardened Portfolio Release (Days 1–4)**
> Full-stack developer platform for evaluating AI agents, establishing golden benchmark baselines, detecting behavioral regressions, and comparing model & prompt iterations.

---

## 1. Product Overview

**Gauge** is an automated benchmarking and evaluation platform built specifically for AI agents. As teams iterate on system prompts, model versions, and reasoning frameworks, small prompt adjustments frequently cause subtle regressions—improving one task while silently breaking others.

Gauge solves this by establishing a disciplined evaluation loop:
1. **Benchmark Datasets**: Curate versioned test suites containing prompt inputs, expected outputs, and scoring metadata.
2. **Agent Version Registry**: Snapshot agent configurations, model parameters, and system prompts.
3. **Execution Engine**: Execute test cases against agent adapters with per-case failure isolation, real wall-clock latency measurement, and token estimation.
4. **Baseline Management**: Designate completed runs as persistent golden baselines per dataset while preserving full audit history.
5. **Regression Detection**: Compare candidate runs against baselines, calculate exact metric deltas (percentage-point pass rates, latency shifts, error counts), and deterministically classify regressions against configurable thresholds.
6. **Analytical Dashboard**: Inspect high-level metrics, per-case outcome flips (`newly_failing`, `fixed`, `persistent_failure`), and detailed response diffs.

---

## 2. System Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             GAUGE DEVELOPER DASHBOARD                            │
│                  (React 18, TypeScript, Tailwind CSS, Vite)                      │
│                                                                                  │
│   ┌───────────────────┐    ┌────────────────────┐    ┌───────────────────────┐   │
│   │ Overview & Health │    │ Dataset & TestCase │    │ Evaluations & Results │   │
│   └───────────────────┘    └────────────────────┘    └───────────────────────┘   │
│                                      │                                           │
│   ┌──────────────────────────────────▼───────────────────────────────────────┐   │
│   │       Benchmark Comparisons & Regression Detection Inspector             │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────▲────────────────────────────────────────┘
                                          │ HTTP REST API (port 8001 / 3001 proxy)
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                               FASTAPI BACKEND SERVICE                            │
│                                                                                  │
│  ┌────────────────────┐   ┌─────────────────────┐   ┌────────────────────────┐   │
│  │ Dataset Service    │   │ Version Service     │   │ Evaluation Service     │   │
│  └────────────────────┘   └─────────────────────┘   └────────────────────────┘   │
│             │                        │                           │               │
│             │                        │                           ▼               │
│             │                        │              ┌────────────────────────┐   │
│             │                        │              │ Agent Adapter Engine   │   │
│             │                        │              │  (Mock / Extensible)   │   │
│             │                        │              └────────────────────────┘   │
│             ▼                        ▼                           ▼               │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │ Comparison Service: Metric Deltas, Threshold Boundaries, Classifier       │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │ Baseline Service: Active Designation, Historical Snapshotting             │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────▲────────────────────────────────────────┘
                                          │ SQLAlchemy 2.0 ORM (port 5433 / internal 5432)
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                              POSTGRESQL 15 DATABASE                              │
│                                                                                  │
│  • evaluation_datasets   • evaluation_test_cases   • agent_versions              │
│  • evaluation_runs       • evaluation_results      • evaluation_baselines        │
│  • evaluation_comparisons (immutable reasons & per-case comparison JSON)         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Sequence: Evaluation & Comparison Loop

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer / CI
    participant UI as Gauge Dashboard
    participant API as FastAPI Backend
    participant DB as PostgreSQL 15
    participant Adapter as Agent Adapter

    Dev->>UI: Launch Evaluation Run
    UI->>API: POST /api/v1/evaluations
    API->>DB: Query dataset test cases
    loop For each test case
        API->>Adapter: execute(prompt, system_prompt, model)
        Adapter-->>API: AgentExecutionResult (output, latency_ms, tokens)
        API->>API: score_case_execution (exact match / error / unscored)
        API->>DB: Persist EvaluationResult
    end
    API->>API: compute_aggregate_metrics (pass rate, latency percentiles)
    API->>DB: Update EvaluationRun (status: completed)
    API-->>UI: EvaluationRunDetailRead

    Dev->>UI: Set Baseline Run
    UI->>API: PUT /api/v1/baselines
    API->>DB: Archive previous active baseline & save new active baseline
    API-->>UI: Active Baseline Confirmed

    Dev->>UI: Launch Candidate Comparison
    UI->>API: POST /api/v1/comparisons
    API->>DB: Fetch baseline & candidate case results
    API->>API: Compare cases & compute metric deltas
    API->>API: classify_regression (apply thresholds)
    API->>DB: Persist EvaluationComparison snapshot
    API-->>UI: EvaluationComparisonDetailRead (deltas, reasons, per-case diffs)
```

---

## 3. Technology Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons | Responsive dark theme, high-contrast typography, live telemetry, and zero CSS runtime overhead. |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2 | Fully typed asynchronous REST API, structured JSON logging, and comprehensive error handling. |
| **Database** | PostgreSQL 15 (Docker) & SQLite (Pytest In-Memory) | Relational persistence with foreign-key constraints, UUID primary keys, and transaction rollbacks. |
| **ORM & Migrations** | SQLAlchemy 2.0 & Alembic | Declarative ORM models, typed schemas, and version-controlled sequential database migrations. |
| **Test Suite** | pytest, pytest-asyncio, HTTPX | 50 deterministic automated tests executing in under 3 seconds with zero external network dependencies. |
| **Containerization** | Docker, Docker Compose, Nginx Alpine | Isolated multi-container deployment with internal proxying and health checks. |

---

## 4. Key Platform Features

### Feature A: Benchmark Datasets & Test Case Catalog
- Organizes benchmark datasets with unique identifiers, descriptions, and test case counts.
- Test cases store `input_prompt`, optional reference `expected_output`, and arbitrary `metadata_json`.
- Missing expected outputs are supported and classified as `unscored` rather than causing false failures.

### Feature B: Agent Version Registry
- Captures snapshots of agent configurations: `name`, `version`, `model_provider`, `model_name`, and `prompt_text`.
- Allows systematic benchmarking of agent iterations without mutating prior execution records.

### Feature C: Evaluation Engine & Scoring Rules
- **Failure Isolation**: An unhandled exception or adapter timeout on an individual test case is recorded as `error` and isolated—it never crashes the entire evaluation run.
- **Accurate Scoring Denominators**: Pass rate is strictly calculated across *eligible* cases (`passed / (passed + failed)`). Errored and unscored cases are tracked separately and excluded from the pass-rate denominator.
- **Measured Latency**: Measures real wall-clock execution time per test case using `time.perf_counter()`, computing arithmetic mean, minimum, maximum, and P95 percentiles.
- **Explicit Estimation Flag**: Token counts are deterministically estimated and visibly flagged (`tokens_estimated = true`).

### Feature D: Persistent Baseline Management
- Completed, non-empty evaluation runs can be designated as the active persistent baseline for a dataset.
- Replacing an active baseline marks previous baselines as inactive while preserving historical records for auditability.
- Rejects incomplete, failed, or zero-case runs from being designated as baselines.

### Feature E: Benchmark Comparison & Regression Detection
- **Metric Deltas**: Calculates explicit deltas between candidate and baseline runs:
  - Pass rate delta in percentage points (`pp`)
  - Average latency delta in milliseconds (`ms`)
  - P95 latency delta in milliseconds (`ms`)
  - Execution error count delta
- **Deterministic Classifier**: Categorizes comparison outcomes into:
  - `improved`: Significant pass rate gains or latency improvements with zero new failures.
  - `regressed`: Pass rate decline, latency spike, increased error count, or newly failing cases beyond configured thresholds.
  - `mixed`: Simultaneous improvements and regressions across different metrics.
  - `unchanged`: All metrics within threshold boundaries and identical case outcomes.
  - `inconclusive`: Incompatible benchmark datasets or missing metric baselines.
- **Per-Case Outcome Taxonomy**: Explicitly identifies per-case behavioral flips:
  - `newly_failing`: Passed in baseline $\rightarrow$ failed in candidate.
  - `fixed`: Failed in baseline $\rightarrow$ passed in candidate.
  - `newly_errored`: Normal in baseline $\rightarrow$ adapter exception in candidate.
  - `persistent_failure` / `persistent_pass`: Consistent outcome across both runs.
  - `added` / `removed`: Cases present in only one run.
- **Coverage Validation**: Flags partial coverage differences (differing case counts) and documents denominator discrepancies in explanatory reasons.
- **Sub-Millisecond Formatting**: Sub-millisecond latency deltas and floating-point zeros are guarded against negative-zero artifacts (`-0.0 ms`).

---

## 5. Environment Variables & Ports

### Port Reference

| Service | Host Port | Internal Port | Purpose |
| :--- | :--- | :--- | :--- |
| **Gauge Backend** | `8001` | `8000` | FastAPI REST API & OpenAPI docs |
| **Gauge Frontend** | `3001` | `80` | Nginx production static bundle & API proxy |
| **Gauge PostgreSQL** | `5433` | `5432` | PostgreSQL 15 relational database |
| *HEALOPS Backend* | `8000` | `8000` | *Preserved external service (do not modify)* |
| *HEALOPS Frontend* | `3000` | `3000` | *Preserved external service (do not modify)* |
| *HEALOPS PostgreSQL* | `5432` | `5432` | *Preserved external service (do not modify)* |

### Environment Configuration (`.env`)

```ini
# Application Environment
ENVIRONMENT=development
PROJECT_NAME=Gauge
VERSION=1.0.0

# Backend API Configuration
API_V1_STR=/api/v1
HOST=0.0.0.0
PORT=8001

# PostgreSQL Configuration (Host port mapped to 5433)
POSTGRES_SERVER=localhost
POSTGRES_PORT=5433
POSTGRES_USER=gauge_user
POSTGRES_PASSWORD=gauge_password
POSTGRES_DB=gauge_db

# Synchronous Database URI
# Container-to-container (Docker Compose):
DATABASE_URL=postgresql://gauge_user:gauge_password@postgres:5432/gauge_db

# Frontend Environment Variables
VITE_API_BASE_URL=http://localhost:8001
```

---

## 6. Installation & Quickstart

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repo-url> gauge
   cd gauge
   ```

2. **Start Gauge services**:
   ```bash
   docker compose up -d --build
   ```

3. **Verify running containers**:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```

4. **Access the application**:
   - **Frontend Dashboard**: [http://localhost:3001](http://localhost:3001)
   - **Backend Health Check**: [http://localhost:8001/health](http://localhost:8001/health)
   - **Interactive API Documentation (Swagger)**: [http://localhost:8001/api/v1/docs](http://localhost:8001/api/v1/docs)

---

### Option 2: Local Development Setup (Windows PowerShell)

#### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- PostgreSQL 15 running on port 5433 (or started via `docker compose up -d postgres`)

#### Backend Setup
```powershell
# Copy environment configuration
Copy-Item .env.example .env

# Install backend dependencies
python -m pip install -r backend/requirements.txt

# Run database migrations
python -m alembic -c backend/alembic.ini upgrade head

# Run backend test suite
python -m pytest backend/tests -v

# Start FastAPI server on port 8001
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --app-dir backend
```

#### Frontend Setup
```powershell
cd frontend
npm install
npm run build    # Verify production compilation
npm run dev      # Start Vite dev server on port 5173
```

---

## 7. Database Migrations

Gauge utilizes Alembic for version-controlled schema evolution:

| Revision | Name | Description |
| :--- | :--- | :--- |
| `0001` | `0001_initial_schema` | Core tables: `evaluation_datasets`, `agent_versions`, `evaluation_runs`. |
| `0002` | `0002_evaluation_engine` | Test cases & case results: `evaluation_test_cases`, `evaluation_results`. |
| `0003` | `0003_baselines_and_comparisons` | Baselines & comparisons: `evaluation_baselines`, `evaluation_comparisons`. |

### Migration Commands
```bash
# Check current migration revision
alembic -c backend/alembic.ini current

# View migration history
alembic -c backend/alembic.ini history

# Upgrade to latest revision
alembic -c backend/alembic.ini upgrade head
```

---

## 8. Automated Testing

The backend test suite runs against an isolated SQLite in-memory database using SQLAlchemy session overrides, ensuring complete test independence and zero side effects on production data.

### Running Backend Tests
```bash
# In Docker:
docker exec gauge-backend pytest -v

# Locally:
pytest backend/tests -v
```

### Test Coverage Highlights
- **`test_comparisons.py`** (22 tests): Baseline designation, replacement history, empty run rejection, identical runs (`unchanged`), pass rate regressions, latency regressions, execution error count regressions, custom thresholds, boundary conditions ($<, =, >$), partial coverage notices, sub-millisecond deltas, and 404 validation.
- **`test_evaluations.py`** (14 tests): Exact-match evaluation, partial execution exceptions, empty datasets, unscored cases, metric calculations, latency percentiles, and repeated run independence.
- **`test_dashboard.py`** (3 tests): Summary counts and database connectivity degradation handling.
- **`test_datasets.py`** (3 tests): Dataset CRUD, schema validations, and case management.
- **`test_versions.py`** (3 tests): Agent version registration and retrieval.
- **`test_db_error_handling.py`** (2 tests): Database exception handling and error resilience.
- **`test_health.py`** (3 tests): Health check and dialect reporting.

### Total Test Results
```
======================== 50 passed, 1 warning in 2.48s =========================
```

### Production Frontend Build Check
```bash
cd frontend && npm run build
# Output: ✓ built in 3.96s (0 errors)
```

---

## 9. API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status, version, and database connectivity. |
| `GET` | `/api/v1/dashboard/summary` | Aggregate dashboard counts and recent evaluation runs. |
| `GET` | `/api/v1/datasets` | List all benchmark datasets with test case counts. |
| `POST` | `/api/v1/datasets` | Create a new benchmark dataset. |
| `GET` | `/api/v1/datasets/{id}` | Get dataset details including test cases. |
| `POST` | `/api/v1/datasets/{id}/cases` | Add a test case to a benchmark dataset. |
| `GET` | `/api/v1/versions` | List registered agent versions. |
| `POST` | `/api/v1/versions` | Register a new agent version snapshot. |
| `GET` | `/api/v1/evaluations` | List evaluation runs. |
| `POST` | `/api/v1/evaluations` | Execute an evaluation run across an agent version and dataset. |
| `GET` | `/api/v1/evaluations/{id}` | Get evaluation run details and aggregate metrics. |
| `GET` | `/api/v1/evaluations/{id}/results` | Get individual test-case execution results for a run. |
| `PUT` | `/api/v1/baselines` | Designate a completed run as the active baseline for a dataset. |
| `GET` | `/api/v1/baselines` | List all active baselines across all datasets. |
| `GET` | `/api/v1/baselines/{dataset_id}` | Get currently active baseline for a dataset. |
| `GET` | `/api/v1/baselines/{dataset_id}/history`| Get historical baseline audit trail for a dataset. |
| `POST` | `/api/v1/comparisons` | Run benchmark comparison and regression detection. |
| `GET` | `/api/v1/comparisons` | List saved benchmark comparisons. |
| `GET` | `/api/v1/comparisons/{id}` | Get full comparison details and per-case output diffs. |
| `GET` | `/api/v1/comparisons/{id}/regressions`| Get regression findings and newly failing test cases. |

Interactive OpenAPI documentation is accessible at [http://localhost:8001/api/v1/docs](http://localhost:8001/api/v1/docs).

---

## 10. Demonstration Walkthrough Script

To execute a complete evaluation, baseline, and regression comparison loop via curl or PowerShell:

```powershell
$BASE = "http://localhost:8001/api/v1"

# 1. Create a benchmark dataset
$ds = Invoke-RestMethod -Uri "$BASE/datasets" -Method Post -ContentType "application/json" -Body '{"name":"QA Golden Benchmark","description":"Core accuracy benchmark"}'
$dsId = $ds.id

# 2. Add test cases
Invoke-RestMethod -Uri "$BASE/datasets/$dsId/cases" -Method Post -ContentType "application/json" -Body '{"case_identifier":"CASE-1","input_prompt":"What is 2 + 2?","expected_output":"4"}'
Invoke-RestMethod -Uri "$BASE/datasets/$dsId/cases" -Method Post -ContentType "application/json" -Body '{"case_identifier":"CASE-2","input_prompt":"Capital of Japan?","expected_output":"Tokyo"}'

# 3. Register agent versions
$v1 = Invoke-RestMethod -Uri "$BASE/versions" -Method Post -ContentType "application/json" -Body '{"name":"MathAgent","version":"v1.0","model_provider":"mock","model_name":"mock-model","prompt_text":"Concise answers"}'
$v2 = Invoke-RestMethod -Uri "$BASE/versions" -Method Post -ContentType "application/json" -Body '{"name":"MathAgent","version":"v2.0","model_provider":"mock","model_name":"mock-model","prompt_text":"Verbose answers"}'

# 4. Execute baseline evaluation run
$run1 = Invoke-RestMethod -Uri "$BASE/evaluations" -Method Post -ContentType "application/json" -Body "{`"name`":`"Baseline Run`",`"dataset_id`":`"$dsId`",`"agent_version_id`":`"$($v1.id)`"}"

# 5. Set run1 as active baseline
Invoke-RestMethod -Uri "$BASE/baselines" -Method Put -ContentType "application/json" -Body "{`"dataset_id`":`"$dsId`",`"run_id`":`"$($run1.id)`",`"notes`":`"Golden baseline`"}"

# 6. Execute candidate evaluation run
$run2 = Invoke-RestMethod -Uri "$BASE/evaluations" -Method Post -ContentType "application/json" -Body "{`"name`":`"Candidate Run`",`"dataset_id`":`"$dsId`",`"agent_version_id`":`"$($v2.id)`"}"

# 7. Compare candidate against baseline
$comp = Invoke-RestMethod -Uri "$BASE/comparisons" -Method Post -ContentType "application/json" -Body "{`"candidate_run_id`":`"$($run2.id)`",`"baseline_run_id`":`"$($run1.id)`"}"

Write-Host "Comparison Status:" $comp.status
Write-Host "Pass Rate Delta:" $comp.pass_rate_delta "pp"
Write-Host "Avg Latency Delta:" $comp.avg_latency_ms_delta "ms"
```

---

## 11. Known Limitations & Design Trade-offs

1. **Mock Adapter Execution**:
   - The current adapter implementation uses a deterministic `MockAgentAdapter` (`BaseAgentAdapter` interface).
   - *Rationale*: Allows complete end-to-end pipeline execution, regression threshold validation, and unit testing locally without paid LLM API keys or external rate-limit dependencies.
   - *Limitation*: Mock evaluation results do not validate real LLM model intelligence or reasoning; they validate evaluation pipeline correctness, metric delta arithmetic, and regression detection logic.
2. **Exact-Match String Correctness**:
   - Scoring currently uses trimmed exact string equality (`actual.strip() == expected.strip()`).
   - Semantic similarity (cosine embedding distance) and LLM-as-a-judge evaluation are not yet implemented.
3. **Synchronous Test Execution**:
   - Test cases are executed sequentially within the evaluation service. For ultra-large datasets ($> 10,000$ cases), background Celery/Redis task workers would be beneficial.
4. **Statistical Significance**:
   - Comparisons compute exact percentage-point deltas and configured threshold boundaries. They do not calculate p-values, confidence intervals, or statistical hypothesis tests (e.g. McNemar's test).

---

## 12. Security & Secret Hygiene

- No API keys, credentials, or secrets are committed in source code or Docker images.
- Uncommitted `.env` files and SQLite databases are excluded by `.gitignore`.
- Database error handlers prevent leaking internal stack traces or database connection URIs in HTTP response bodies.

---

## 13. License

MIT License. Designed and engineered as a modular AI engineering portfolio project.
