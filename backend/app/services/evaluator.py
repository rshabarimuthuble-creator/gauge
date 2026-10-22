import json
import math
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from app.services.adapters.base import AgentExecutionResult


@dataclass
class CaseEvaluation:
    """
    Standardized per-case evaluation result after applying explicit scoring rules.
    Records actual vs expected output, numeric score, scoring method, status,
    diagnostic explanation, and telemetry.
    """
    status: str  # 'passed', 'failed', 'error', 'unscored'
    actual_output: Optional[str]
    expected_output: Optional[str]
    score: Optional[float]  # 0.0 to 1.0, or None for unscored
    scoring_method: str  # 'exact_match', 'normalized_match', 'structured_output', 'partial_credit', 'llm_judge'
    latency_ms: Optional[float]
    token_usage: Optional[int]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    tokens_estimated: bool
    is_mock: bool
    cost_usd: Optional[float]
    model_provider: Optional[str]
    model_name: Optional[str]
    error_message: Optional[str]
    metadata_json: Optional[str]


def score_exact_match(actual: Optional[str], expected: str) -> Tuple[bool, float, Optional[str]]:
    """
    Exact Match Scorer:
    Compares trimmed string representations directly.
    Returns (is_passed, score, explanation).
    """
    act_trimmed = (actual or "").strip()
    exp_trimmed = expected.strip()
    is_match = (act_trimmed == exp_trimmed)
    return is_match, 1.0 if is_match else 0.0, None if is_match else "Exact string mismatch"


def normalize_text(text: str) -> str:
    """Standardizes casing, internal whitespace, and leading/trailing punctuation."""
    t = text.strip().lower()
    # Remove leading/trailing quotes and common punctuation
    t = re.sub(r"^[\"\'`]+|[\"\'`.,;:!?]+$", "", t)
    # Collapse multiple whitespaces
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def parse_numeric(text: str) -> Optional[float]:
    """Attempts to parse a numerical value from text, stripping currency and commas."""
    cleaned = re.sub(r"[\$,€£¥]", "", text.strip())
    cleaned = cleaned.replace(",", "")
    # Check for percentage
    if cleaned.endswith("%"):
        try:
            return float(cleaned[:-1].strip()) / 100.0
        except ValueError:
            pass
    # Check for fractions like 1/2
    if "/" in cleaned:
        parts = cleaned.split("/")
        if len(parts) == 2:
            try:
                num = float(parts[0].strip())
                den = float(parts[1].strip())
                if den != 0:
                    return num / den
            except ValueError:
                pass
    try:
        return float(cleaned)
    except ValueError:
        return None


def score_normalized_match(actual: Optional[str], expected: str) -> Tuple[bool, float, Optional[str]]:
    """
    Normalized Exact Match Scorer:
    1. Case-insensitivity and punctuation trimming.
    2. Number / currency equivalence (e.g. '42.0' == '42', '$100' == '100').
    3. Boolean equivalence ('true' == 'yes' == '1', 'false' == 'no' == '0').
    """
    if not actual:
        return False, 0.0, "Actual output is empty"

    act_norm = normalize_text(actual)
    exp_norm = normalize_text(expected)

    if act_norm == exp_norm:
        return True, 1.0, None

    # Boolean equivalence check
    bool_map = {
        "true": True, "yes": True, "1": True, "correct": True,
        "false": False, "no": False, "0": False, "incorrect": False,
    }
    if act_norm in bool_map and exp_norm in bool_map:
        if bool_map[act_norm] == bool_map[exp_norm]:
            return True, 1.0, None

    # Numeric equivalence check
    num_act = parse_numeric(act_norm)
    num_exp = parse_numeric(exp_norm)
    if num_act is not None and num_exp is not None:
        if math.isclose(num_act, num_exp, rel_tol=1e-5, abs_tol=1e-7):
            return True, 1.0, None

    return False, 0.0, f"Normalized mismatch: '{act_norm}' != '{exp_norm}'"


def extract_json_payload(text: str) -> Optional[Any]:
    """Extracts JSON object or array from markdown code block or raw text."""
    clean = text.strip()
    # Check for markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean, re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    # Find outermost { ... } or [ ... ]
    first_brace = clean.find("{")
    last_brace = clean.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(clean[first_brace : last_brace + 1])
        except Exception:
            pass

    first_bracket = clean.find("[")
    last_bracket = clean.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        try:
            return json.loads(clean[first_bracket : last_bracket + 1])
        except Exception:
            pass

    try:
        return json.loads(clean)
    except Exception:
        return None


def score_structured_output(
    actual: Optional[str],
    expected: str,
    criteria: Optional[str] = None,
) -> Tuple[bool, float, Optional[str]]:
    """
    Structured Output Scorer:
    Validates JSON output against expected JSON structure and values.
    Supports strict equality or subset matching if criteria specifies 'subset'.
    """
    if not actual or not actual.strip():
        return False, 0.0, "Actual output is empty"

    act_json = extract_json_payload(actual)
    if act_json is None:
        return False, 0.0, "Output is not valid JSON"

    exp_json = extract_json_payload(expected)
    if exp_json is None:
        # If expected is not JSON, exact string compare
        return (actual.strip() == expected.strip()), 1.0 if actual.strip() == expected.strip() else 0.0, None

    is_subset_mode = criteria and "subset" in criteria.lower()

    if isinstance(exp_json, dict) and isinstance(act_json, dict):
        if is_subset_mode:
            # Check all expected keys exist and match in actual
            missing_or_mismatched = []
            for k, v in exp_json.items():
                if k not in act_json:
                    missing_or_mismatched.append(f"Missing key '{k}'")
                elif act_json[k] != v:
                    missing_or_mismatched.append(f"Value mismatch for '{k}': expected {v}, got {act_json[k]}")
            if missing_or_mismatched:
                return False, 0.0, f"Structured subset failure: {'; '.join(missing_or_mismatched)}"
            return True, 1.0, None
        else:
            # Full dictionary comparison
            if act_json == exp_json:
                return True, 1.0, None
            diffs = []
            for k in set(exp_json.keys()).union(set(act_json.keys())):
                if k not in act_json:
                    diffs.append(f"missing key '{k}'")
                elif k not in exp_json:
                    diffs.append(f"extra key '{k}'")
                elif act_json[k] != exp_json[k]:
                    diffs.append(f"key '{k}' mismatch ({act_json[k]} != {exp_json[k]})")
            return False, 0.0, f"Structured JSON mismatch: {', '.join(diffs[:3])}"

    if isinstance(exp_json, list) and isinstance(act_json, list):
        if act_json == exp_json:
            return True, 1.0, None
        # Check unordered match if criteria permits
        if criteria and "unordered" in criteria.lower():
            try:
                if sorted(act_json, key=str) == sorted(exp_json, key=str):
                    return True, 1.0, None
            except Exception:
                pass
        return False, 0.0, f"Structured array mismatch: length {len(act_json)} vs {len(exp_json)}"

    if act_json == exp_json:
        return True, 1.0, None

    return False, 0.0, "Structured value mismatch"


def score_partial_credit(
    actual: Optional[str],
    expected: str,
    criteria: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, float, Optional[str]]:
    """
    Partial-Credit Scorer:
    Explicit and testable scoring rule for multi-part questions or item lists.
    Extracts expected items from metadata['expected_items'], metadata['rubric'],
    or comma/newline-separated expected_output.
    Calculates proportion of matched items.
    Passed if score >= pass_threshold (default 0.70 / 70%).
    """
    if not actual or not actual.strip():
        return False, 0.0, "Actual output is empty"

    meta = metadata or {}
    items: List[str] = []

    if isinstance(meta.get("expected_items"), list):
        items = [str(i).strip() for i in meta["expected_items"] if str(i).strip()]
    elif isinstance(meta.get("rubric"), list):
        items = [str(i).strip() for i in meta["rubric"] if str(i).strip()]
    else:
        # Split expected by semicolon, comma, or newline if multiple items present
        if ";" in expected:
            items = [p.strip() for p in expected.split(";") if p.strip()]
        elif "\n" in expected:
            items = [re.sub(r"^[-*•\d.]+\s*", "", p).strip() for p in expected.split("\n") if p.strip()]
        elif "," in expected:
            items = [p.strip() for p in expected.split(",") if p.strip()]
        else:
            items = [expected.strip()]

    if not items:
        items = [expected.strip()]

    act_norm = actual.lower()
    matched_count = 0
    missing_items = []

    for it in items:
        it_norm = it.lower()
        if it_norm in act_norm:
            matched_count += 1
        else:
            missing_items.append(it)

    score = round(matched_count / len(items), 2)
    threshold = float(meta.get("pass_threshold", 0.70))
    is_passed = score >= threshold

    explanation = (
        f"Partial credit: {matched_count}/{len(items)} items matched ({int(score * 100)}%). "
        f"Pass threshold: {int(threshold * 100)}%."
    )
    if missing_items:
        explanation += f" Missing: {', '.join(missing_items[:3])}"

    return is_passed, score, explanation


def score_case_execution(
    expected_output: Optional[str],
    execution: AgentExecutionResult,
    extra_metadata: Optional[Dict[str, Any]] = None,
    default_scoring_method: str = "exact_match",
    criteria: Optional[str] = None,
) -> CaseEvaluation:
    """
    Standardized per-case evaluation dispatcher:
    1. Execution errors: If the adapter encountered an error, status is strictly 'error'
       and score is 0.0. Errors are NEVER counted as correct.
    2. Unscored: If expected_output is None or empty whitespace, status is 'unscored'
       and score is None. Unscored cases are NEVER counted as correct.
    3. Method resolution: Resolves scoring method from metadata or criteria:
       - 'exact_match': Strict character-exact string comparison.
       - 'normalized_match': Case-insensitive, punctuation-tolerant, and numeric equivalence.
       - 'structured_output' / 'structured_json': Deep JSON parsing and structural comparison.
       - 'partial_credit': Explicit, testable rubric checking item proportions.
    """
    meta_dict = dict(extra_metadata or {})
    if execution.model_provider:
        meta_dict["provider"] = execution.model_provider
    if execution.model_name:
        meta_dict["model"] = execution.model_name
    if execution.prompt_tokens is not None:
        meta_dict["prompt_tokens"] = execution.prompt_tokens
    if execution.completion_tokens is not None:
        meta_dict["completion_tokens"] = execution.completion_tokens
    if execution.cost_usd is not None:
        meta_dict["cost_usd"] = execution.cost_usd
    if execution.raw_response:
        meta_dict["raw_response"] = execution.raw_response
        if isinstance(execution.raw_response, dict) and execution.raw_response.get("groq_timings"):
            meta_dict["groq_timings"] = execution.raw_response["groq_timings"]

    # Rule 1: Execution error handling
    if execution.is_error or execution.error_message:
        meta_dict["error_details"] = execution.error_message or "Execution exception occurred"
        return CaseEvaluation(
            status="error",
            actual_output=execution.output,
            expected_output=expected_output,
            score=0.0,
            scoring_method=default_scoring_method,
            latency_ms=execution.latency_ms,
            token_usage=execution.token_usage,
            prompt_tokens=execution.prompt_tokens,
            completion_tokens=execution.completion_tokens,
            tokens_estimated=execution.tokens_estimated,
            is_mock=execution.is_mock,
            cost_usd=execution.cost_usd,
            model_provider=execution.model_provider,
            model_name=execution.model_name,
            error_message=execution.error_message or "Execution exception occurred",
            metadata_json=json.dumps(meta_dict) if meta_dict else None,
        )

    # Rule 2: Unscored case handling (missing expected reference output)
    if expected_output is None or expected_output.strip() == "":
        meta_dict["scoring_note"] = "No expected reference answer provided; case marked unscored."
        return CaseEvaluation(
            status="unscored",
            actual_output=execution.output,
            expected_output=expected_output,
            score=None,
            scoring_method="unscored",
            latency_ms=execution.latency_ms,
            token_usage=execution.token_usage,
            prompt_tokens=execution.prompt_tokens,
            completion_tokens=execution.completion_tokens,
            tokens_estimated=execution.tokens_estimated,
            is_mock=execution.is_mock,
            cost_usd=execution.cost_usd,
            model_provider=execution.model_provider,
            model_name=execution.model_name,
            error_message=None,
            metadata_json=json.dumps(meta_dict) if meta_dict else None,
        )

    # Rule 3: Resolve scoring method
    method = (
        meta_dict.get("scoring_method")
        or meta_dict.get("task_type")
        or default_scoring_method
    ).lower().strip()

    if "json" in method or "structured" in method:
        method = "structured_output"
        is_passed, score, explanation = score_structured_output(
            execution.output, expected_output, criteria=criteria
        )
    elif "partial" in method or "credit" in method or "multi_part" in method:
        method = "partial_credit"
        is_passed, score, explanation = score_partial_credit(
            execution.output, expected_output, criteria=criteria, metadata=meta_dict
        )
    elif "norm" in method:
        method = "normalized_match"
        is_passed, score, explanation = score_normalized_match(execution.output, expected_output)
    else:
        method = "exact_match"
        is_passed, score, explanation = score_exact_match(execution.output, expected_output)

    if explanation:
        meta_dict["score_explanation"] = explanation

    meta_str = json.dumps(meta_dict) if meta_dict else None

    return CaseEvaluation(
        status="passed" if is_passed else "failed",
        actual_output=execution.output,
        expected_output=expected_output,
        score=score,
        scoring_method=method,
        latency_ms=execution.latency_ms,
        token_usage=execution.token_usage,
        prompt_tokens=execution.prompt_tokens,
        completion_tokens=execution.completion_tokens,
        tokens_estimated=execution.tokens_estimated,
        is_mock=execution.is_mock,
        cost_usd=execution.cost_usd,
        model_provider=execution.model_provider,
        model_name=execution.model_name,
        error_message=None,
        metadata_json=meta_str,
    )


def compute_aggregate_metrics(
    evaluations: List[CaseEvaluation],
    dataset_total_cases: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Computes rigorous aggregate metrics with documented numerators and denominators:
    - total_cases: Total count of cases executed in the run (N_run)
    - passed_cases: Count with status == 'passed' (N_pass)
    - failed_cases: Count with status == 'failed' (N_fail)
    - errored_cases: Count with status == 'error' (N_err)
    - unscored_cases: Count with status == 'unscored' (N_unscored)
    - eligible_cases: N_pass + N_fail
    - pass_rate: (passed_cases / eligible_cases) * 100.0 if eligible_cases > 0 else None
        Numerator: passed_cases
        Denominator: eligible_cases (passed_cases + failed_cases)
        Strictly excludes errors and unscored cases.
    - accuracy: (passed_cases / total_cases) * 100.0 if total_cases > 0 else None
        Numerator: passed_cases
        Denominator: total_cases (execution errors and failures reduce accuracy)
    - error_rate: (errored_cases / total_cases) * 100.0 if total_cases > 0 else 0.0
        Numerator: errored_cases
        Denominator: total_cases
    - dataset_coverage: (total_cases / dataset_total_cases) * 100.0
        Numerator: total_cases executed
        Denominator: dataset_total_cases (total cases in dataset snapshot)
    - total_cost_usd: Arithmetic sum of reliable costs across cases (None if all unavailable)
    - total_tokens, prompt_tokens, completion_tokens: Summed token consumption
    - latency statistics: arithmetic mean, min, max, p95 (95th percentile nearest rank)
    """
    total_cases = len(evaluations)
    passed_cases = sum(1 for e in evaluations if e.status == "passed")
    failed_cases = sum(1 for e in evaluations if e.status == "failed")
    errored_cases = sum(1 for e in evaluations if e.status == "error")
    unscored_cases = sum(1 for e in evaluations if e.status == "unscored")

    eligible_cases = passed_cases + failed_cases
    pass_rate = round((passed_cases / eligible_cases) * 100.0, 2) if eligible_cases > 0 else None
    accuracy = round((passed_cases / total_cases) * 100.0, 2) if total_cases > 0 else None
    error_rate = round((errored_cases / total_cases) * 100.0, 2) if total_cases > 0 else 0.0

    target_total = dataset_total_cases if (dataset_total_cases and dataset_total_cases > 0) else total_cases
    dataset_coverage = round((total_cases / target_total) * 100.0, 2) if target_total > 0 else 100.0

    # Token and cost calculations
    costs = [e.cost_usd for e in evaluations if e.cost_usd is not None]
    total_cost_usd = round(sum(costs), 6) if costs else None

    prompt_tokens_list = [e.prompt_tokens for e in evaluations if e.prompt_tokens is not None]
    completion_tokens_list = [e.completion_tokens for e in evaluations if e.completion_tokens is not None]
    token_usage_list = [e.token_usage for e in evaluations if e.token_usage is not None]

    prompt_tokens = sum(prompt_tokens_list) if prompt_tokens_list else None
    completion_tokens = sum(completion_tokens_list) if completion_tokens_list else None
    total_tokens = sum(token_usage_list) if token_usage_list else None

    # Latency statistics
    latencies = [e.latency_ms for e in evaluations if e.latency_ms is not None]
    if latencies:
        avg_latency_ms = round(sum(latencies) / len(latencies), 2)
        min_latency_ms = round(min(latencies), 2)
        max_latency_ms = round(max(latencies), 2)
        sorted_latencies = sorted(latencies)
        p95_idx = min(len(sorted_latencies) - 1, int(0.95 * len(sorted_latencies)))
        p95_latency_ms = round(sorted_latencies[p95_idx], 2)
    else:
        avg_latency_ms = None
        min_latency_ms = None
        max_latency_ms = None
        p95_latency_ms = None

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "errored_cases": errored_cases,
        "unscored_cases": unscored_cases,
        "eligible_cases": eligible_cases,
        "pass_rate": pass_rate,
        "accuracy": accuracy,
        "error_rate": error_rate,
        "dataset_coverage": dataset_coverage,
        "total_cost_usd": total_cost_usd,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "avg_latency_ms": avg_latency_ms,
        "min_latency_ms": min_latency_ms,
        "max_latency_ms": max_latency_ms,
        "p95_latency_ms": p95_latency_ms,
    }
