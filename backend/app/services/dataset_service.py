import json
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.models.dataset import EvaluationDataset
from app.models.test_case import EvaluationTestCase
from app.schemas.dataset import EvaluationDatasetCreate, EvaluationDatasetUpdate
from app.schemas.test_case import EvaluationTestCaseCreate
from app.core.logging import logger


class DatasetValidationError(Exception):
    """Raised when dataset payload is malformed or invalid."""
    pass


class DatasetDuplicateError(DatasetValidationError):
    """Raised when duplicate test case identifiers are detected."""
    pass


class DatasetService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[EvaluationDataset]:
        """Fetch all evaluation datasets ordered by creation date descending with test cases loaded."""
        stmt = (
            select(EvaluationDataset)
            .options(selectinload(EvaluationDataset.test_cases))
            .order_by(EvaluationDataset.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        datasets = list(db.scalars(stmt).all())
        for d in datasets:
            setattr(d, "test_cases_count", len(d.test_cases))
        return datasets

    @staticmethod
    def get_by_id(db: Session, dataset_id: str) -> Optional[EvaluationDataset]:
        """Fetch an evaluation dataset by its unique ID with test cases loaded."""
        stmt = (
            select(EvaluationDataset)
            .options(selectinload(EvaluationDataset.test_cases))
            .where(EvaluationDataset.id == dataset_id)
        )
        dataset = db.scalars(stmt).first()
        if dataset:
            setattr(dataset, "test_cases_count", len(dataset.test_cases))
        return dataset

    @staticmethod
    def create(db: Session, dataset_in: EvaluationDatasetCreate) -> EvaluationDataset:
        """Create a new evaluation dataset and any initial test cases provided, validating duplicate IDs."""
        # Validate duplicate IDs in initial test cases
        if dataset_in.test_cases:
            seen_ids = set()
            for idx, tc in enumerate(dataset_in.test_cases, start=1):
                case_id = (tc.case_identifier or f"case-{idx}").strip()
                if case_id in seen_ids:
                    raise DatasetDuplicateError(f"Duplicate case_identifier '{case_id}' in dataset creation payload.")
                seen_ids.add(case_id)

        dataset = EvaluationDataset(
            name=dataset_in.name,
            description=dataset_in.description,
            version=getattr(dataset_in, "version", "v1.0.0") or "v1.0.0",
        )
        db.add(dataset)
        db.flush()

        if dataset_in.test_cases:
            for idx, tc_in in enumerate(dataset_in.test_cases, start=1):
                case_identifier = tc_in.case_identifier or f"case-{idx}"
                tc = EvaluationTestCase(
                    dataset_id=dataset.id,
                    case_identifier=case_identifier,
                    input_prompt=tc_in.input_prompt,
                    expected_output=tc_in.expected_output,
                    criteria=tc_in.criteria,
                    category=getattr(tc_in, "category", None),
                    difficulty=getattr(tc_in, "difficulty", None),
                    scoring_method=getattr(tc_in, "scoring_method", "exact_match") or "exact_match",
                    metadata_json=tc_in.metadata_json,
                )
                db.add(tc)

        db.commit()
        db.refresh(dataset)
        setattr(dataset, "test_cases_count", len(dataset.test_cases))
        logger.info(
            "Created evaluation dataset '%s' (id: %s, version: %s) with %d test cases",
            dataset.name,
            dataset.id,
            dataset.version,
            len(dataset.test_cases),
        )
        return dataset

    @staticmethod
    def add_test_case(db: Session, dataset_id: str, case_in: EvaluationTestCaseCreate) -> EvaluationTestCase:
        """Add an individual test case to an existing dataset, validating for duplicate IDs."""
        dataset = db.get(EvaluationDataset, dataset_id)
        if not dataset:
            raise DatasetValidationError(f"Dataset with ID '{dataset_id}' not found.")

        existing_count = db.scalar(
            select(func.count()).select_from(EvaluationTestCase).where(EvaluationTestCase.dataset_id == dataset_id)
        ) or 0
        case_identifier = (case_in.case_identifier or f"case-{existing_count + 1}").strip()

        # Check for duplicate within this dataset
        existing_case = db.scalar(
            select(EvaluationTestCase).where(
                EvaluationTestCase.dataset_id == dataset_id,
                EvaluationTestCase.case_identifier == case_identifier,
            )
        )
        if existing_case:
            raise DatasetDuplicateError(
                f"Test case with identifier '{case_identifier}' already exists in dataset '{dataset.name}'."
            )

        if not case_in.input_prompt or not case_in.input_prompt.strip():
            raise DatasetValidationError("Test case input_prompt cannot be empty.")

        test_case = EvaluationTestCase(
            dataset_id=dataset_id,
            case_identifier=case_identifier,
            input_prompt=case_in.input_prompt,
            expected_output=case_in.expected_output,
            criteria=case_in.criteria,
            category=getattr(case_in, "category", None),
            difficulty=getattr(case_in, "difficulty", None),
            scoring_method=getattr(case_in, "scoring_method", "exact_match") or "exact_match",
            metadata_json=case_in.metadata_json,
        )
        db.add(test_case)
        db.commit()
        db.refresh(test_case)
        logger.info("Added test case '%s' (id: %s) to dataset %s", test_case.case_identifier, test_case.id, dataset_id)
        return test_case

    @staticmethod
    def parse_raw_cases(raw_text: str) -> Tuple[Optional[str], Optional[str], Optional[str], List[Dict[str, Any]]]:
        """
        Parses JSON or JSONL format.
        Returns (name, version, description, list_of_case_dicts).
        Raises DatasetValidationError if syntax is malformed.
        """
        stripped = raw_text.strip()
        if not stripped:
            raise DatasetValidationError("Import payload is empty.")

        dataset_name = None
        dataset_version = None
        dataset_description = None
        cases: List[Dict[str, Any]] = []

        # Attempt 1: Standard JSON array or dataset object
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    cases = parsed
                elif isinstance(parsed, dict):
                    dataset_name = parsed.get("name")
                    dataset_version = parsed.get("version")
                    dataset_description = parsed.get("description")
                    cases = parsed.get("test_cases", [])
                else:
                    raise DatasetValidationError("Invalid JSON structure: expected list or object.")
            except json.JSONDecodeError as exc:
                # If JSON decode fails, try JSONL
                cases = []

        # Attempt 2: JSONL (one JSON object per line)
        if not cases:
            lines = [l.strip() for l in stripped.splitlines() if l.strip()]
            for idx, line in enumerate(lines, start=1):
                try:
                    case_obj = json.loads(line)
                    if not isinstance(case_obj, dict):
                        raise DatasetValidationError(f"Malformed JSONL line {idx}: expected JSON object.")
                    cases.append(case_obj)
                except json.JSONDecodeError as err:
                    raise DatasetValidationError(f"Malformed JSON/JSONL at line {idx}: {str(err)}")

        if not cases:
            raise DatasetValidationError("No test cases found in payload.")

        return dataset_name, dataset_version, dataset_description, cases

    @staticmethod
    def import_dataset(db: Session, raw_text: str, default_name: Optional[str] = None) -> EvaluationDataset:
        """
        Parses JSON/JSONL, validates case uniqueness and required fields, and creates a new dataset.
        """
        name, version, description, raw_cases = DatasetService.parse_raw_cases(raw_text)
        final_name = name or default_name or f"Imported Dataset {func.now()}"
        final_version = version or "v1.0.0"

        # Validate duplicates within raw_cases
        seen_ids = set()
        validated_cases: List[EvaluationTestCaseCreate] = []
        for idx, item in enumerate(raw_cases, start=1):
            if not isinstance(item, dict):
                raise DatasetValidationError(f"Item {idx} must be a dictionary.")
            c_id = item.get("case_identifier") or f"case-{idx}"
            if c_id in seen_ids:
                raise DatasetDuplicateError(f"Duplicate case_identifier '{c_id}' in import payload at item {idx}.")
            seen_ids.add(c_id)

            prompt = item.get("input_prompt")
            if not prompt or not str(prompt).strip():
                raise DatasetValidationError(f"Item {idx} (case '{c_id}') is missing required 'input_prompt'.")

            meta_val = item.get("metadata_json")
            if isinstance(meta_val, dict):
                meta_val = json.dumps(meta_val)

            validated_cases.append(
                EvaluationTestCaseCreate(
                    case_identifier=c_id,
                    input_prompt=str(prompt),
                    expected_output=item.get("expected_output"),
                    criteria=item.get("criteria"),
                    category=item.get("category"),
                    difficulty=item.get("difficulty"),
                    scoring_method=item.get("scoring_method", "exact_match"),
                    metadata_json=meta_val,
                )
            )

        create_in = EvaluationDatasetCreate(
            name=final_name,
            version=final_version,
            description=description or "Imported benchmark dataset",
            test_cases=validated_cases,
        )
        return DatasetService.create(db, create_in)

    @staticmethod
    def import_cases_into_dataset(db: Session, dataset_id: str, raw_text: str) -> List[EvaluationTestCase]:
        """
        Imports test cases into an existing dataset with duplicate ID validation.
        """
        dataset = db.get(EvaluationDataset, dataset_id)
        if not dataset:
            raise DatasetValidationError(f"Dataset with ID '{dataset_id}' not found.")

        _, _, _, raw_cases = DatasetService.parse_raw_cases(raw_text)

        # Fetch existing case identifiers
        existing_ids = set(
            db.scalars(
                select(EvaluationTestCase.case_identifier).where(EvaluationTestCase.dataset_id == dataset_id)
            ).all()
        )

        seen_in_payload = set()
        added_cases = []

        for idx, item in enumerate(raw_cases, start=1):
            if not isinstance(item, dict):
                raise DatasetValidationError(f"Item {idx} must be a JSON object.")
            c_id = item.get("case_identifier") or f"case-{len(existing_ids) + idx}"

            if c_id in seen_in_payload:
                raise DatasetDuplicateError(f"Duplicate case_identifier '{c_id}' within import payload.")
            if c_id in existing_ids:
                raise DatasetDuplicateError(f"Case identifier '{c_id}' already exists in dataset '{dataset.name}'.")

            prompt = item.get("input_prompt")
            if not prompt or not str(prompt).strip():
                raise DatasetValidationError(f"Item {idx} (case '{c_id}') missing required 'input_prompt'.")

            seen_in_payload.add(c_id)
            existing_ids.add(c_id)

            meta_val = item.get("metadata_json")
            if isinstance(meta_val, dict):
                meta_val = json.dumps(meta_val)

            case_in = EvaluationTestCaseCreate(
                case_identifier=c_id,
                input_prompt=str(prompt),
                expected_output=item.get("expected_output"),
                criteria=item.get("criteria"),
                category=item.get("category"),
                difficulty=item.get("difficulty"),
                scoring_method=item.get("scoring_method", "exact_match"),
                metadata_json=meta_val,
            )
            created_case = DatasetService.add_test_case(db, dataset_id, case_in)
            added_cases.append(created_case)

        return added_cases

    @staticmethod
    def seed_curated_benchmark_if_needed(db: Session) -> Optional[EvaluationDataset]:
        """
        Seeds the curated 36-case benchmark suite if it does not already exist.
        """
        curated_name = "Gauge General Reasoning & Capabilities Suite"
        existing = db.scalars(select(EvaluationDataset).where(EvaluationDataset.name == curated_name)).first()
        if existing:
            return existing

        fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "curated_benchmark_dataset.json"
        if not fixture_path.exists():
            logger.warning("Curated benchmark dataset fixture not found at %s", str(fixture_path))
            return None

        with open(fixture_path, "r", encoding="utf-8") as f:
            content = f.read()

        return DatasetService.import_dataset(db, content)

    @staticmethod
    def get_test_cases(db: Session, dataset_id: str, skip: int = 0, limit: int = 100) -> List[EvaluationTestCase]:
        """Fetch test cases belonging to a dataset."""
        stmt = (
            select(EvaluationTestCase)
            .where(EvaluationTestCase.dataset_id == dataset_id)
            .order_by(EvaluationTestCase.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def count(db: Session) -> int:
        """Count total datasets."""
        stmt = select(EvaluationDataset)
        return len(list(db.scalars(stmt).all()))
