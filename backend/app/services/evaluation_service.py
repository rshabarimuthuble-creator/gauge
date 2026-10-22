import json
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.evaluation_run import EvaluationRun
from app.models.evaluation_result import EvaluationResult
from app.models.dataset import EvaluationDataset
from app.models.agent_version import AgentVersion
from app.models.test_case import EvaluationTestCase
from app.schemas.evaluation_run import EvaluationRunCreate
from app.services.adapters.factory import get_agent_adapter
from app.services.adapters.base import AgentExecutionResult
from app.services.evaluator import score_case_execution, compute_aggregate_metrics
from app.core.logging import logger


class RunEntityNotFoundError(Exception):
    """Raised when an associated entity (dataset or agent version) is not found."""
    pass


class DuplicateEvaluationError(Exception):
    """Raised when an active evaluation run is already in progress for the specified dataset and agent version."""
    def __init__(self, message: str, running_run_id: Optional[str] = None):
        super().__init__(message)
        self.running_run_id = running_run_id


class EvaluationService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[EvaluationRun]:
        """Fetch all evaluation runs ordered by creation date descending."""
        stmt = (
            select(EvaluationRun)
            .order_by(EvaluationRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_by_id(db: Session, run_id: str) -> Optional[EvaluationRun]:
        """Fetch an evaluation run by its unique ID."""
        return db.get(EvaluationRun, run_id)

    @staticmethod
    def get_run_detail(db: Session, run_id: str) -> Optional[EvaluationRun]:
        """Fetch an evaluation run with eagerly loaded case results."""
        stmt = (
            select(EvaluationRun)
            .options(selectinload(EvaluationRun.results))
            .where(EvaluationRun.id == run_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def get_run_results(
        db: Session,
        run_id: str,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[EvaluationResult]:
        """Fetch paginated individual test case execution results for a specific run."""
        stmt = select(EvaluationResult).where(EvaluationResult.run_id == run_id)
        if status_filter:
            stmt = stmt.where(EvaluationResult.status == status_filter)
        stmt = stmt.order_by(EvaluationResult.created_at.asc()).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def count(db: Session) -> int:
        """Count total evaluation runs."""
        stmt = select(EvaluationRun)
        return len(list(db.scalars(stmt).all()))

    @staticmethod
    def get_latest(db: Session) -> Optional[EvaluationRun]:
        """Fetch the most recent evaluation run."""
        stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1)
        return db.scalars(stmt).first()

    @classmethod
    def create_and_execute(
        cls,
        db: Session,
        run_in: EvaluationRunCreate,
        background: bool = False,
    ) -> EvaluationRun:
        """
        Initiates an evaluation benchmark run against the specified dataset and agent version.
        Lifecycle:
        1. Validate existence of dataset and agent version.
        2. Guard against duplicate concurrent runs on the same dataset/agent.
        3. Create initial run record with status='running'.
        4. If background=True, dispatch execution to background worker and return run record immediately.
        5. If background=False (synchronous), execute test cases, score, aggregate metrics, and return completed run.
        """
        # Step 1: Validation
        dataset = db.get(EvaluationDataset, run_in.dataset_id)
        if not dataset:
            raise RunEntityNotFoundError(f"Evaluation dataset with ID '{run_in.dataset_id}' not found.")

        agent_version = db.get(AgentVersion, run_in.agent_version_id)
        if not agent_version:
            raise RunEntityNotFoundError(f"Agent version with ID '{run_in.agent_version_id}' not found.")

        # Step 2: Active duplicate run prevention
        fifteen_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
        active_stmt = (
            select(EvaluationRun)
            .where(
                EvaluationRun.dataset_id == run_in.dataset_id,
                EvaluationRun.agent_version_id == run_in.agent_version_id,
                EvaluationRun.status == "running",
            )
            .order_by(EvaluationRun.started_at.desc())
        )
        active_runs = list(db.scalars(active_stmt).all())
        for active_run in active_runs:
            started = active_run.started_at
            if started and started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if started and started >= fifteen_minutes_ago:
                raise DuplicateEvaluationError(
                    f"An evaluation run for dataset '{dataset.name}' and agent '{agent_version.name}' is already running "
                    f"(Run ID: '{active_run.id}'). Please wait for it to complete or inspect the running evaluation.",
                    running_run_id=active_run.id,
                )
            else:
                logger.warning(
                    "Marking stale running evaluation %s as failed (exceeded 15 min limit)",
                    active_run.id,
                )
                active_run.status = "failed"
                active_run.completed_at = datetime.now(timezone.utc)
                active_run.error_message = "Evaluation timed out or was interrupted."
                db.commit()

        # Step 3: Persist initial run record with status='running'
        scoring_cfg = getattr(run_in, "scoring_config", None) or "default"
        exec_mode = getattr(run_in, "execution_mode", None)

        run = EvaluationRun(
            name=run_in.name,
            dataset_id=run_in.dataset_id,
            agent_version_id=run_in.agent_version_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            dataset_version=dataset.version,
            scoring_config=scoring_cfg,
            model_provider=agent_version.model_provider,
            model_name=agent_version.model_name,
            total_cases=0,
            passed_cases=0,
            failed_cases=0,
            errored_cases=0,
            unscored_cases=0,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        logger.info(
            "Created evaluation run record '%s' (id: %s) for dataset '%s' and agent '%s' (background=%s)",
            run.name,
            run.id,
            dataset.name,
            agent_version.name,
            background,
        )

        # Step 4: Dispatch execution
        if background:
            target_run_id = run.id

            def _bg_worker(rid: str, sc_cfg: str, mode: Optional[str]):
                from app.db.session import SessionLocal
                bg_db = SessionLocal()
                try:
                    cls._execute_run(bg_db, rid, scoring_config=sc_cfg, execution_mode=mode)
                except Exception as bg_exc:
                    logger.error("Background evaluation worker failed for run %s: %s", rid, bg_exc, exc_info=True)
                finally:
                    bg_db.close()

            worker_thread = threading.Thread(
                target=_bg_worker,
                args=(target_run_id, scoring_cfg, exec_mode),
                daemon=True,
                name=f"eval-worker-{target_run_id[:8]}",
            )
            worker_thread.start()
            return run
        else:
            cls._execute_run(
                db,
                run.id,
                scoring_config=scoring_cfg,
                execution_mode=exec_mode,
            )
            db.refresh(run)
            return run

    @classmethod
    def _execute_run(
        cls,
        db: Session,
        run_id: str,
        scoring_config: str = "default",
        execution_mode: Optional[str] = None,
    ) -> Optional[EvaluationRun]:
        """
        Executes test cases for an existing evaluation run record, scores results,
        computes aggregate metrics, and transitions status to 'completed' or 'failed'.
        """
        run = db.get(EvaluationRun, run_id)
        if not run:
            logger.error("Evaluation run %s not found for execution", run_id)
            return None

        dataset = db.get(EvaluationDataset, run.dataset_id)
        agent_version = db.get(AgentVersion, run.agent_version_id)
        if not dataset or not agent_version:
            logger.error("Associated dataset or agent_version missing for run %s", run_id)
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = "Associated dataset or agent version not found."
            db.commit()
            return run

        logger.info(
            "Executing evaluation run '%s' (id: %s) for dataset '%s' (%s) and agent '%s'",
            run.name,
            run.id,
            dataset.name,
            dataset.version,
            agent_version.name,
        )

        try:
            # Query test cases for this dataset ordered by creation
            stmt = (
                select(EvaluationTestCase)
                .where(EvaluationTestCase.dataset_id == dataset.id)
                .order_by(EvaluationTestCase.created_at.asc())
            )
            test_cases = list(db.scalars(stmt).all())

            # Snapshot test cases for provenance and auditability
            snapshot_list = [
                {
                    "case_identifier": tc.case_identifier,
                    "input_prompt": tc.input_prompt,
                    "expected_output": tc.expected_output,
                    "criteria": tc.criteria,
                    "category": tc.category,
                    "difficulty": tc.difficulty,
                    "scoring_method": tc.scoring_method or "exact_match",
                    "metadata_json": tc.metadata_json,
                }
                for tc in test_cases
            ]
            run.dataset_snapshot_json = json.dumps(snapshot_list)

            # Handle empty dataset safely
            if not test_cases:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                run.total_cases = 0
                run.passed_cases = 0
                run.failed_cases = 0
                run.errored_cases = 0
                run.unscored_cases = 0
                run.pass_rate = None
                run.accuracy = None
                run.error_rate = 0.0
                run.dataset_coverage = 0.0
                db.commit()
                db.refresh(run)
                logger.info("Evaluation run %s completed: dataset had 0 test cases", run.id)
                return run

            # Execute test cases independently
            adapter = get_agent_adapter(
                provider=agent_version.model_provider,
                execution_mode=execution_mode,
            )
            evaluations = []
            is_mock_val = (execution_mode == "mock") or (agent_version.model_provider in ("mock", "mock-adapter"))

            for idx, tc in enumerate(test_cases):
                # Pacing delay between sequential real LLM provider calls to avoid bursting RPM limits
                if idx > 0 and not is_mock_val:
                    time.sleep(0.1)

                meta = {}
                if tc.metadata_json:
                    try:
                        meta = json.loads(tc.metadata_json)
                    except Exception:
                        meta = {"raw_metadata": tc.metadata_json}

                if tc.category and "category" not in meta:
                    meta["category"] = tc.category
                if tc.difficulty and "difficulty" not in meta:
                    meta["difficulty"] = tc.difficulty
                if tc.scoring_method and "scoring_method" not in meta:
                    meta["scoring_method"] = tc.scoring_method

                # Isolate case execution: individual case failure must not crash the run
                try:
                    exec_result = adapter.execute(
                        prompt=tc.input_prompt,
                        system_prompt=agent_version.prompt_text,
                        model_name=agent_version.model_name,
                        expected_output=tc.expected_output,
                        metadata=meta,
                    )
                except Exception as exc:
                    logger.error("Exception executing case '%s': %s", tc.case_identifier, str(exc))
                    exec_result = AgentExecutionResult(
                        output=None,
                        latency_ms=0.0,
                        token_usage=0,
                        prompt_tokens=0,
                        completion_tokens=0,
                        tokens_estimated=is_mock_val,
                        is_mock=is_mock_val,
                        is_error=True,
                        error_message=f"Unhandled adapter exception: {str(exc)}",
                        model_provider=agent_version.model_provider,
                        model_name=agent_version.model_name,
                    )

                default_method = tc.scoring_method or scoring_config or "exact_match"
                scored = score_case_execution(
                    expected_output=tc.expected_output,
                    execution=exec_result,
                    extra_metadata=meta,
                    default_scoring_method=default_method,
                    criteria=tc.criteria,
                )
                evaluations.append(scored)

                # Persist case-level result
                result_record = EvaluationResult(
                    run_id=run.id,
                    test_case_id=tc.id,
                    case_identifier=tc.case_identifier,
                    input_prompt=tc.input_prompt,
                    expected_output=tc.expected_output,
                    actual_output=scored.actual_output,
                    status=scored.status,
                    score=scored.score,
                    scoring_method=scored.scoring_method,
                    latency_ms=scored.latency_ms,
                    token_usage=scored.token_usage,
                    prompt_tokens=scored.prompt_tokens,
                    completion_tokens=scored.completion_tokens,
                    tokens_estimated=scored.tokens_estimated,
                    cost_usd=scored.cost_usd,
                    model_provider=scored.model_provider or agent_version.model_provider,
                    model_name=scored.model_name or agent_version.model_name,
                    error_message=scored.error_message,
                    is_mock=scored.is_mock,
                    metadata_json=scored.metadata_json,
                )
                db.add(result_record)

            # Compute aggregate metrics and update run
            metrics = compute_aggregate_metrics(evaluations, dataset_total_cases=len(test_cases))
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.total_cases = metrics["total_cases"]
            run.passed_cases = metrics["passed_cases"]
            run.failed_cases = metrics["failed_cases"]
            run.errored_cases = metrics["errored_cases"]
            run.unscored_cases = metrics["unscored_cases"]
            run.pass_rate = metrics["pass_rate"]
            run.accuracy = metrics["accuracy"]
            run.error_rate = metrics["error_rate"]
            run.dataset_coverage = metrics["dataset_coverage"]
            run.total_cost_usd = metrics["total_cost_usd"]
            run.total_tokens = metrics["total_tokens"]
            run.prompt_tokens = metrics["prompt_tokens"]
            run.completion_tokens = metrics["completion_tokens"]
            run.avg_latency_ms = metrics["avg_latency_ms"]
            run.min_latency_ms = metrics["min_latency_ms"]
            run.max_latency_ms = metrics["max_latency_ms"]
            run.p95_latency_ms = metrics["p95_latency_ms"]

            db.commit()
            db.refresh(run)

            logger.info(
                "Evaluation run %s completed: %d total, %d passed, %d failed, %d errored, %d unscored. Pass rate: %s",
                run.id,
                run.total_cases,
                run.passed_cases,
                run.failed_cases,
                run.errored_cases,
                run.unscored_cases,
                f"{run.pass_rate}%" if run.pass_rate is not None else "N/A",
            )
            return run

        except Exception as exc:
            db.rollback()
            try:
                run = db.get(EvaluationRun, run_id)
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.now(timezone.utc)
                    run.error_message = f"Fatal evaluation execution error: {str(exc)}"
                    db.commit()
                    db.refresh(run)
            except Exception as inner_exc:
                logger.error("Failed to mark run %s as failed: %s", run_id, inner_exc)
            logger.error("Fatal error during evaluation run %s: %s", run_id, str(exc), exc_info=True)
            raise
