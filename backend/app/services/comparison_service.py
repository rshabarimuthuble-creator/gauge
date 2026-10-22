import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comparison import EvaluationComparison
from app.models.evaluation_run import EvaluationRun
from app.models.evaluation_result import EvaluationResult
from app.models.baseline import EvaluationBaseline
from app.models.agent_version import AgentVersion
from app.schemas.comparison import (
    RegressionThresholds,
    CaseComparisonResult,
    EvaluationComparisonCreate,
    EvaluationComparisonRead,
    EvaluationComparisonDetailRead,
)
from app.core.logging import logger


class ComparisonValidationError(Exception):
    """Raised when evaluation runs cannot be compared due to invalid input or status."""
    pass


class ComparisonNotFoundError(Exception):
    """Raised when a comparison record is not found."""
    pass


class ComparisonService:
    @staticmethod
    def _enrich_comparison(
        db: Session,
        comp: EvaluationComparison,
        include_details: bool = False,
    ) -> dict:
        """
        Converts EvaluationComparison ORM model to dictionary with parsed JSON fields
        and joined metadata for Pydantic schema validation.
        """
        reasons = json.loads(comp.reasons_json) if comp.reasons_json else []

        base_run = db.get(EvaluationRun, comp.baseline_run_id)
        cand_run = db.get(EvaluationRun, comp.candidate_run_id)

        base_agent = db.get(AgentVersion, base_run.agent_version_id) if base_run else None
        cand_agent = db.get(AgentVersion, cand_run.agent_version_id) if cand_run else None

        data = {
            "id": comp.id,
            "dataset_id": comp.dataset_id,
            "baseline_run_id": comp.baseline_run_id,
            "candidate_run_id": comp.candidate_run_id,
            "status": comp.status,
            "is_compatible": comp.is_compatible,
            "compatibility_notes": comp.compatibility_notes,
            "pass_rate_delta": comp.pass_rate_delta,
            "accuracy_delta": comp.accuracy_delta,
            "passed_cases_delta": comp.passed_cases_delta,
            "failed_cases_delta": comp.failed_cases_delta,
            "errored_cases_delta": comp.errored_cases_delta,
            "unscored_cases_delta": comp.unscored_cases_delta,
            "avg_latency_ms_delta": comp.avg_latency_ms_delta,
            "p95_latency_ms_delta": comp.p95_latency_ms_delta,
            "cost_usd_delta": comp.cost_usd_delta,
            "tokens_delta": comp.tokens_delta,
            "newly_failing_count": comp.newly_failing_count,
            "newly_fixed_count": comp.newly_fixed_count,
            "newly_errored_count": comp.newly_errored_count,
            "newly_unscored_count": comp.newly_unscored_count,
            "total_cases_baseline": comp.total_cases_baseline,
            "total_cases_candidate": comp.total_cases_candidate,
            "reasons": reasons,
            "created_at": comp.created_at,
            "baseline_run_name": base_run.name if base_run else None,
            "candidate_run_name": cand_run.name if cand_run else None,
            "baseline_agent_name": base_agent.name if base_agent else None,
            "candidate_agent_name": cand_agent.name if cand_agent else None,
            "baseline_agent_version": base_agent.version if base_agent else None,
            "candidate_agent_version": cand_agent.version if cand_agent else None,
            "baseline_pass_rate": base_run.pass_rate if base_run else None,
            "candidate_pass_rate": cand_run.pass_rate if cand_run else None,
            "baseline_avg_latency_ms": base_run.avg_latency_ms if base_run else None,
            "candidate_avg_latency_ms": cand_run.avg_latency_ms if cand_run else None,
        }

        if include_details:
            case_list = json.loads(comp.case_comparisons_json) if comp.case_comparisons_json else []
            data["case_comparisons"] = [CaseComparisonResult(**c) for c in case_list]

        return data

    @staticmethod
    def check_dataset_compatibility(
        baseline_run: EvaluationRun,
        candidate_run: EvaluationRun,
        baseline_results: List[EvaluationResult],
        candidate_results: List[EvaluationResult],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates benchmark dataset compatibility between two evaluation runs.
        Returns (is_compatible, explanation).
        """
        notes = []
        if baseline_run.dataset_id != candidate_run.dataset_id:
            return False, (
                f"Dataset mismatch: baseline uses dataset '{baseline_run.dataset_id}', "
                f"while candidate uses dataset '{candidate_run.dataset_id}'."
            )

        if len(baseline_results) == 0 or len(candidate_results) == 0:
            return False, "One or both runs have zero test case results to compare."

        base_version = getattr(baseline_run, "dataset_version", None)
        cand_version = getattr(candidate_run, "dataset_version", None)
        if base_version and cand_version and base_version != cand_version:
            notes.append(f"dataset version discrepancy: baseline ({base_version}) vs candidate ({cand_version})")

        base_config = getattr(baseline_run, "scoring_config", None)
        cand_config = getattr(candidate_run, "scoring_config", None)
        if base_config and cand_config and base_config != cand_config:
            notes.append(f"scoring config discrepancy: baseline used '{base_config}', candidate used '{cand_config}'")

        base_cases = {r.case_identifier for r in baseline_results}
        cand_cases = {r.case_identifier for r in candidate_results}

        missing_in_candidate = base_cases - cand_cases
        extra_in_candidate = cand_cases - base_cases

        if missing_in_candidate or extra_in_candidate:
            if missing_in_candidate:
                notes.append(f"{len(missing_in_candidate)} cases missing in candidate")
            if extra_in_candidate:
                notes.append(f"{len(extra_in_candidate)} extra cases in candidate")
            return True, f"Partial coverage match: {'; '.join(notes)}. Metrics calculated across available cases."

        if notes:
            return True, f"Benchmark comparison notice: {'; '.join(notes)}. Full test case overlap."

        return True, "Full benchmark coverage match: identical test case set evaluated."

    @staticmethod
    def compare_cases(
        baseline_results: List[EvaluationResult],
        candidate_results: List[EvaluationResult],
    ) -> Tuple[List[CaseComparisonResult], Dict[str, int]]:
        """
        Performs per-case comparison between baseline and candidate execution results.
        Returns a list of CaseComparisonResult and summary counts.
        """
        base_map: Dict[str, EvaluationResult] = {r.case_identifier: r for r in baseline_results}
        cand_map: Dict[str, EvaluationResult] = {r.case_identifier: r for r in candidate_results}

        all_keys = list(dict.fromkeys(list(base_map.keys()) + list(cand_map.keys())))
        all_keys.sort()

        comparisons: List[CaseComparisonResult] = []
        counts = {
            "newly_failing": 0,
            "newly_fixed": 0,
            "newly_errored": 0,
            "newly_unscored": 0,
            "persistent_failure": 0,
            "persistent_pass": 0,
            "added": 0,
            "removed": 0,
            "unchanged": 0,
        }

        for key in all_keys:
            base_res = base_map.get(key)
            cand_res = cand_map.get(key)

            base_status = base_res.status if base_res else None
            cand_status = cand_res.status if cand_res else None

            input_prompt = (cand_res.input_prompt if cand_res else base_res.input_prompt) or ""
            expected_output = cand_res.expected_output if cand_res else (base_res.expected_output if base_res else None)

            base_lat = base_res.latency_ms if base_res else None
            cand_lat = cand_res.latency_ms if cand_res else None
            lat_delta = (cand_lat - base_lat) if (cand_lat is not None and base_lat is not None) else None
            if lat_delta is not None and abs(round(lat_delta, 2)) < 0.001:
                lat_delta = 0.0

            if base_res is None:
                outcome_change = "added"
                counts["added"] += 1
            elif cand_res is None:
                outcome_change = "removed"
                counts["removed"] += 1
            elif cand_status == "error" and base_status != "error":
                outcome_change = "newly_errored"
                counts["newly_errored"] += 1
            elif cand_status == "unscored" and base_status != "unscored":
                outcome_change = "newly_unscored"
                counts["newly_unscored"] += 1
            elif base_status == "passed" and cand_status == "failed":
                outcome_change = "newly_failing"
                counts["newly_failing"] += 1
            elif base_status == "failed" and cand_status == "passed":
                outcome_change = "fixed"
                counts["newly_fixed"] += 1
            elif base_status == "failed" and cand_status == "failed":
                outcome_change = "persistent_failure"
                counts["persistent_failure"] += 1
            elif base_status == "passed" and cand_status == "passed":
                outcome_change = "persistent_pass"
                counts["persistent_pass"] += 1
            else:
                outcome_change = "unchanged"
                counts["unchanged"] += 1

            base_score = getattr(base_res, "score", None) if base_res else None
            cand_score = getattr(cand_res, "score", None) if cand_res else None
            sc_method = (
                getattr(cand_res, "scoring_method", None)
                if cand_res
                else (getattr(base_res, "scoring_method", None) if base_res else None)
            )

            comparisons.append(
                CaseComparisonResult(
                    case_identifier=key,
                    input_prompt=input_prompt,
                    expected_output=expected_output,
                    baseline_status=base_status,
                    candidate_status=cand_status,
                    baseline_score=round(base_score, 2) if base_score is not None else None,
                    candidate_score=round(cand_score, 2) if cand_score is not None else None,
                    scoring_method=sc_method,
                    outcome_change=outcome_change,
                    baseline_latency_ms=round(base_lat, 2) if base_lat is not None else None,
                    candidate_latency_ms=round(cand_lat, 2) if cand_lat is not None else None,
                    latency_delta_ms=round(lat_delta, 2) if lat_delta is not None else None,
                    baseline_output=base_res.actual_output if base_res else None,
                    candidate_output=cand_res.actual_output if cand_res else None,
                )
            )

        return comparisons, counts

    @staticmethod
    def classify_regression(
        is_compatible: bool,
        compatibility_notes: Optional[str],
        pass_rate_delta: Optional[float],
        avg_latency_ms_delta: Optional[float],
        p95_latency_ms_delta: Optional[float],
        errored_cases_delta: int,
        newly_failing_count: int,
        newly_fixed_count: int,
        thresholds: RegressionThresholds,
        is_all_mock: bool,
    ) -> Tuple[str, List[str]]:
        """
        Deterministic, transparent regression classifier.
        Calculates status ('improved', 'regressed', 'unchanged', 'mixed', 'inconclusive')
        and compiles explicit list of explanatory reasons.
        """
        reasons: List[str] = []

        if not is_compatible:
            reasons.append(f"Inconclusive: Incompatible benchmark comparison ({compatibility_notes}).")
            return "inconclusive", reasons

        if pass_rate_delta is None:
            reasons.append("Inconclusive: Pass rate metric is missing for one or both runs.")
            return "inconclusive", reasons

        regression_flags = []
        improvement_flags = []

        # 1. Pass Rate Check
        # Decline is baseline - candidate, or -(candidate - baseline)
        if pass_rate_delta < -thresholds.pass_rate_decline_threshold:
            regression_flags.append(
                f"Pass rate declined by {abs(pass_rate_delta):.1f} percentage points "
                f"(threshold: {thresholds.pass_rate_decline_threshold:.1f} pp)"
            )
        elif pass_rate_delta > thresholds.pass_rate_improvement_threshold:
            improvement_flags.append(
                f"Pass rate improved by {pass_rate_delta:.1f} percentage points "
                f"(threshold: {thresholds.pass_rate_improvement_threshold:.1f} pp)"
            )

        # 2. Newly Failing Cases Check
        if newly_failing_count > 0:
            regression_flags.append(f"{newly_failing_count} test case(s) newly failed in candidate run")

        if newly_fixed_count > 0:
            improvement_flags.append(f"{newly_fixed_count} test case(s) newly passed (fixed) in candidate run")

        # 3. Execution Errors Check
        if errored_cases_delta >= thresholds.error_count_increase_threshold:
            regression_flags.append(
                f"Execution error count increased by {errored_cases_delta} "
                f"(threshold: {thresholds.error_count_increase_threshold})"
            )

        # 4. Latency Regressions
        if avg_latency_ms_delta is not None and avg_latency_ms_delta > thresholds.latency_increase_threshold_ms:
            regression_flags.append(
                f"Average latency increased by {avg_latency_ms_delta:.1f} ms "
                f"(threshold: {thresholds.latency_increase_threshold_ms:.1f} ms)"
            )

        if p95_latency_ms_delta is not None and p95_latency_ms_delta > thresholds.p95_latency_increase_threshold_ms:
            regression_flags.append(
                f"P95 latency increased by {p95_latency_ms_delta:.1f} ms "
                f"(threshold: {thresholds.p95_latency_increase_threshold_ms:.1f} ms)"
            )

        # 5. Latency Improvement (only if no pass rate drop and latency significantly lower)
        if avg_latency_ms_delta is not None and avg_latency_ms_delta < -thresholds.latency_increase_threshold_ms:
            improvement_flags.append(
                f"Average latency reduced by {abs(avg_latency_ms_delta):.1f} ms"
            )

        # Coverage Warning if denominators differ
        if compatibility_notes and "Partial coverage match" in compatibility_notes:
            reasons.append(
                f"Coverage notice: {compatibility_notes} Test suites have differing case sets; metric denominators differ."
            )

        if is_all_mock:
            reasons.append(
                "Mock execution detected: identical mock adapter behavior was executed for both runs. "
                "This comparison validates pipeline determinism and regression threshold processing rather than real model capabilities."
            )

        # Overall Status Determination
        if regression_flags and improvement_flags:
            status = "mixed"
            reasons.extend(regression_flags)
            reasons.extend(improvement_flags)
        elif regression_flags:
            status = "regressed"
            reasons.extend(regression_flags)
        elif improvement_flags:
            status = "improved"
            reasons.extend(improvement_flags)
        else:
            status = "unchanged"
            if compatibility_notes and "Partial coverage match" in compatibility_notes:
                reasons.append("Overlapping test cases outcomes remained unchanged within configured thresholds.")
            else:
                reasons.append("All metrics and test-case outcomes remained unchanged within configured thresholds.")

        # Note on empirical nature and run-to-run sampling variance
        reasons.append(
            "Variance notice: LLM outputs naturally vary between runs due to sampling temperature, even with identical model and inputs. "
            "Metric deltas reflect empirical observations across these specific execution runs without claiming asymptotic statistical significance."
        )

        return status, reasons

    @staticmethod
    def compare_runs(
        db: Session,
        candidate_run_id: str,
        baseline_run_id: Optional[str] = None,
        thresholds: Optional[RegressionThresholds] = None,
    ) -> EvaluationComparisonDetailRead:
        """
        Executes a complete benchmark comparison between a baseline and a candidate run.
        If baseline_run_id is omitted, looks up the active baseline for the candidate's dataset.
        Persists the comparison and returns full detailed comparison metrics.
        """
        cand_run = db.get(EvaluationRun, candidate_run_id)
        if not cand_run:
            raise ComparisonValidationError(f"Candidate run '{candidate_run_id}' not found.")

        if cand_run.status != "completed":
            raise ComparisonValidationError(
                f"Candidate run '{candidate_run_id}' status is '{cand_run.status}', expected 'completed'."
            )

        # Resolve Baseline Run
        if baseline_run_id:
            base_run = db.get(EvaluationRun, baseline_run_id)
            if not base_run:
                raise ComparisonValidationError(f"Baseline run '{baseline_run_id}' not found.")
        else:
            # Look up active baseline for this dataset
            active_baseline = (
                db.scalars(
                    select(EvaluationBaseline).where(
                        EvaluationBaseline.dataset_id == cand_run.dataset_id,
                        EvaluationBaseline.is_active == True,  # noqa: E712
                    )
                ).first()
            )
            if not active_baseline:
                raise ComparisonValidationError(
                    f"No active baseline designated for dataset '{cand_run.dataset_id}'. "
                    "Please designate an active baseline first or specify baseline_run_id."
                )
            base_run = db.get(EvaluationRun, active_baseline.run_id)
            if not base_run:
                raise ComparisonValidationError(
                    f"Baseline run '{active_baseline.run_id}' referenced in active baseline not found."
                )

        if base_run.status != "completed":
            raise ComparisonValidationError(
                f"Baseline run '{base_run.id}' status is '{base_run.status}', expected 'completed'."
            )

        active_thresholds = thresholds or RegressionThresholds()

        # Fetch case execution results for both runs
        base_results = list(
            db.scalars(
                select(EvaluationResult)
                .where(EvaluationResult.run_id == base_run.id)
                .order_by(EvaluationResult.case_identifier.asc())
            ).all()
        )
        cand_results = list(
            db.scalars(
                select(EvaluationResult)
                .where(EvaluationResult.run_id == cand_run.id)
                .order_by(EvaluationResult.case_identifier.asc())
            ).all()
        )

        is_compatible, compat_notes = ComparisonService.check_dataset_compatibility(
            base_run, cand_run, base_results, cand_results
        )

        # Metric deltas: Candidate minus Baseline
        pass_rate_delta: Optional[float] = None
        if cand_run.pass_rate is not None and base_run.pass_rate is not None:
            pass_rate_delta = round(cand_run.pass_rate - base_run.pass_rate, 2)
            if abs(pass_rate_delta) < 0.001:
                pass_rate_delta = 0.0

        passed_cases_delta = cand_run.passed_cases - base_run.passed_cases
        failed_cases_delta = cand_run.failed_cases - base_run.failed_cases
        errored_cases_delta = cand_run.errored_cases - base_run.errored_cases
        unscored_cases_delta = cand_run.unscored_cases - base_run.unscored_cases

        avg_lat_delta: Optional[float] = None
        if cand_run.avg_latency_ms is not None and base_run.avg_latency_ms is not None:
            avg_lat_delta = round(cand_run.avg_latency_ms - base_run.avg_latency_ms, 2)
            if abs(avg_lat_delta) < 0.001:
                avg_lat_delta = 0.0

        p95_lat_delta: Optional[float] = None
        if cand_run.p95_latency_ms is not None and base_run.p95_latency_ms is not None:
            p95_lat_delta = round(cand_run.p95_latency_ms - base_run.p95_latency_ms, 2)
            if abs(p95_lat_delta) < 0.001:
                p95_lat_delta = 0.0

        accuracy_delta: Optional[float] = None
        if getattr(cand_run, "accuracy", None) is not None and getattr(base_run, "accuracy", None) is not None:
            accuracy_delta = round(cand_run.accuracy - base_run.accuracy, 2)
            if abs(accuracy_delta) < 0.001:
                accuracy_delta = 0.0

        cost_usd_delta: Optional[float] = None
        if getattr(cand_run, "total_cost_usd", None) is not None and getattr(base_run, "total_cost_usd", None) is not None:
            cost_usd_delta = round(cand_run.total_cost_usd - base_run.total_cost_usd, 6)
            if abs(cost_usd_delta) < 0.000001:
                cost_usd_delta = 0.0

        tokens_delta: Optional[int] = None
        if getattr(cand_run, "total_tokens", None) is not None and getattr(base_run, "total_tokens", None) is not None:
            tokens_delta = cand_run.total_tokens - base_run.total_tokens

        # Per-case comparison
        case_comparisons, case_counts = ComparisonService.compare_cases(base_results, cand_results)

        # Check mock execution
        is_all_mock = all(r.is_mock for r in base_results) and all(r.is_mock for r in cand_results)

        # Classify regression
        status, reasons = ComparisonService.classify_regression(
            is_compatible=is_compatible,
            compatibility_notes=compat_notes,
            pass_rate_delta=pass_rate_delta,
            avg_latency_ms_delta=avg_lat_delta,
            p95_latency_ms_delta=p95_lat_delta,
            errored_cases_delta=errored_cases_delta,
            newly_failing_count=case_counts["newly_failing"],
            newly_fixed_count=case_counts["newly_fixed"],
            thresholds=active_thresholds,
            is_all_mock=is_all_mock,
        )

        # Persist Comparison
        comparison = EvaluationComparison(
            dataset_id=cand_run.dataset_id,
            baseline_run_id=base_run.id,
            candidate_run_id=cand_run.id,
            status=status,
            is_compatible=is_compatible,
            compatibility_notes=compat_notes,
            pass_rate_delta=pass_rate_delta,
            accuracy_delta=accuracy_delta,
            passed_cases_delta=passed_cases_delta,
            failed_cases_delta=failed_cases_delta,
            errored_cases_delta=errored_cases_delta,
            unscored_cases_delta=unscored_cases_delta,
            avg_latency_ms_delta=avg_lat_delta,
            p95_latency_ms_delta=p95_lat_delta,
            cost_usd_delta=cost_usd_delta,
            tokens_delta=tokens_delta,
            newly_failing_count=case_counts["newly_failing"],
            newly_fixed_count=case_counts["newly_fixed"],
            newly_errored_count=case_counts["newly_errored"],
            newly_unscored_count=case_counts["newly_unscored"],
            total_cases_baseline=len(base_results),
            total_cases_candidate=len(cand_results),
            reasons_json=json.dumps(reasons),
            thresholds_json=json.dumps(active_thresholds.model_dump()),
            case_comparisons_json=json.dumps([c.model_dump() for c in case_comparisons]),
            created_at=datetime.now(timezone.utc),
        )
        db.add(comparison)
        db.commit()
        db.refresh(comparison)

        logger.info(
            f"Saved comparison '{comparison.id}': baseline '{base_run.id}', candidate '{cand_run.id}', "
            f"status '{status}', pass_rate_delta '{pass_rate_delta}' pp"
        )

        enriched = ComparisonService._enrich_comparison(db, comparison, include_details=True)
        return EvaluationComparisonDetailRead(**enriched)

    @staticmethod
    def get_by_id(
        db: Session,
        comparison_id: str,
        include_details: bool = False,
    ) -> Optional[dict]:
        """Fetch comparison by ID with optionally parsed per-case details."""
        comp = db.get(EvaluationComparison, comparison_id)
        if not comp:
            return None
        return ComparisonService._enrich_comparison(db, comp, include_details=include_details)

    @staticmethod
    def get_all(
        db: Session,
        dataset_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[EvaluationComparisonRead]:
        """Fetch paginated comparisons, optionally filtered by dataset."""
        stmt = select(EvaluationComparison)
        if dataset_id:
            stmt = stmt.where(EvaluationComparison.dataset_id == dataset_id)
        stmt = stmt.order_by(EvaluationComparison.created_at.desc()).offset(skip).limit(limit)

        comps = list(db.scalars(stmt).all())
        results = []
        for c in comps:
            enriched = ComparisonService._enrich_comparison(db, c, include_details=False)
            results.append(EvaluationComparisonRead(**enriched))
        return results
