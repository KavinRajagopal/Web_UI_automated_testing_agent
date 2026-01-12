"""Analyze Inputs Node - Validates, loads, and analyzes input files.

This node:
1. Checks if required input files exist
2. Loads and validates module_spec.json
3. Loads and validates testcases.csv
4. Loads and validates element_metadata/*.json
5. Analyzes test cases for duplicates and coverage
6. Prioritizes by P0 > P1 > P2 and caps at 10 tests
7. Builds analysis_summary for human review
"""

import logging
import os
from typing import Dict, List, Any, Tuple
from difflib import SequenceMatcher

from ..models.state import AgentState
from ..models.schemas import ModuleSpec, TestCaseRow, PageMetadata
from ..parsers.module_parser import ModuleParser
from ..parsers.csv_parser import CSVParser
from ..parsers.element_parser import ElementParser
from ..utils.event_logger import add_event_to_state

logger = logging.getLogger(__name__)

# Maximum test cases to generate (cost control)
MAX_TEST_CASES = 10

# Similarity threshold for duplicate detection
DUPLICATE_THRESHOLD = 0.85


class OnboardingError(Exception):
    """Raised when onboarding fails."""
    pass


def _check_inputs_exist(inputs_path: str) -> Dict[str, bool]:
    """
    Check which input files exist.

    Args:
        inputs_path: Path to inputs directory

    Returns:
        Dict with existence status for each input type
    """
    status = {
        "module_spec": False,
        "testcases": False,
        "element_metadata": False,
        "element_files": []
    }

    # Check module_spec.json
    module_spec_path = os.path.join(inputs_path, "module_spec.json")
    status["module_spec"] = os.path.exists(module_spec_path)

    # Check testcases.csv
    testcases_path = os.path.join(inputs_path, "testcases.csv")
    status["testcases"] = os.path.exists(testcases_path)

    # Check element_metadata directory
    element_dir = os.path.join(inputs_path, "element_metadata")
    if os.path.isdir(element_dir):
        json_files = [f for f in os.listdir(element_dir) if f.endswith('.json')]
        status["element_metadata"] = len(json_files) > 0
        status["element_files"] = json_files

    return status


def _load_module_spec(inputs_path: str) -> Tuple[ModuleSpec, List[str]]:
    """
    Load and validate module_spec.json.

    Args:
        inputs_path: Path to inputs directory

    Returns:
        Tuple of (ModuleSpec, list of warnings)
    """
    warnings = []
    parser = ModuleParser()

    module_spec_path = os.path.join(inputs_path, "module_spec.json")
    module_spec = parser.parse(module_spec_path)

    # Validation warnings
    if not module_spec.pages:
        warnings.append("No pages defined in module_spec.json")

    if not module_spec.app_url:
        warnings.append("No app_url defined in module_spec.json")

    return module_spec, warnings


def _load_test_cases(inputs_path: str) -> Tuple[List[TestCaseRow], List[str]]:
    """
    Load and validate testcases.csv.

    Args:
        inputs_path: Path to inputs directory

    Returns:
        Tuple of (list of TestCaseRow, list of warnings)
    """
    warnings = []
    parser = CSVParser()

    testcases_path = os.path.join(inputs_path, "testcases.csv")
    test_cases = parser.parse(testcases_path)

    # Validation warnings
    if not test_cases:
        warnings.append("No test cases found in testcases.csv")

    # Check for missing pages
    pages_used = set(tc.page_name for tc in test_cases if tc.page_name)
    logger.info(f"Test cases reference pages: {pages_used}")

    return test_cases, warnings


def _load_element_metadata(inputs_path: str) -> Tuple[Dict[str, PageMetadata], List[str]]:
    """
    Load and validate element_metadata/*.json files.

    Args:
        inputs_path: Path to inputs directory

    Returns:
        Tuple of (dict of page_name -> PageMetadata, list of warnings)
    """
    warnings = []
    parser = ElementParser()

    element_dir = os.path.join(inputs_path, "element_metadata")

    if not os.path.isdir(element_dir):
        return {}, ["element_metadata directory not found"]

    page_metadata = parser.parse_directory(element_dir)

    # Validation
    if not page_metadata:
        warnings.append("No element metadata files found")

    # Check for unstable selectors
    for page_name, page in page_metadata.items():
        unstable = parser.find_unstable_selectors(page)
        if unstable:
            for selector_info in unstable:
                warnings.append(
                    f"Unstable selector in {page_name}: {selector_info['element_name']} "
                    f"uses {selector_info['selector_type']}"
                )

    return page_metadata, warnings


def _calculate_similarity(text1: str, text2: str) -> float:
    """Calculate text similarity ratio between two strings."""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def _get_test_text(tc: Dict[str, Any]) -> str:
    """Get comparable text from a test case for similarity comparison."""
    parts = []
    if tc.get("test_name"):
        parts.append(tc["test_name"])
    if tc.get("description"):
        parts.append(tc["description"])
    if tc.get("steps"):
        # Handle steps as list or string
        steps = tc["steps"]
        if isinstance(steps, list):
            parts.extend(steps)
        else:
            parts.append(str(steps))
    return " ".join(parts)


def _detect_duplicates(test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect duplicate test cases using text similarity.

    Args:
        test_cases: List of test case dicts

    Returns:
        List of duplicate info dicts
    """
    duplicates = []
    seen_ids = set()

    for i, tc1 in enumerate(test_cases):
        tc1_id = tc1.get("test_id", f"TC_{i}")
        if tc1_id in seen_ids:
            continue

        tc1_text = _get_test_text(tc1)

        for j, tc2 in enumerate(test_cases[i + 1:], start=i + 1):
            tc2_id = tc2.get("test_id", f"TC_{j}")
            if tc2_id in seen_ids:
                continue

            tc2_text = _get_test_text(tc2)
            similarity = _calculate_similarity(tc1_text, tc2_text)

            if similarity >= DUPLICATE_THRESHOLD:
                duplicates.append({
                    "test_id": tc2_id,
                    "duplicate_of": tc1_id,
                    "similarity": round(similarity * 100, 1),
                    "recommendation": "merge" if similarity > 0.95 else "review"
                })
                seen_ids.add(tc2_id)

    return duplicates


def _normalize_priority(priority: Any) -> str:
    """Normalize priority value to P0/P1/P2."""
    if priority is None:
        return "P2"

    priority_str = str(priority).upper().strip()

    # Handle various priority formats
    if priority_str in ["P0", "0", "CRITICAL", "BLOCKER", "HIGH"]:
        return "P0"
    elif priority_str in ["P1", "1", "MAJOR", "MEDIUM"]:
        return "P1"
    else:
        return "P2"


def _prioritize_and_cap_tests(
    test_cases: List[Dict[str, Any]],
    duplicates: List[Dict[str, Any]],
    max_tests: int = MAX_TEST_CASES
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Prioritize test cases by priority and cap at max_tests.

    Args:
        test_cases: All test cases
        duplicates: List of duplicate info
        max_tests: Maximum number of tests to select

    Returns:
        Tuple of (selected tests, priority counts)
    """
    # Get IDs of duplicates to exclude
    duplicate_ids = {d["test_id"] for d in duplicates}

    # Filter out duplicates
    unique_tests = [tc for tc in test_cases if tc.get("test_id") not in duplicate_ids]

    # Categorize by priority
    by_priority = {"P0": [], "P1": [], "P2": []}
    for tc in unique_tests:
        priority = _normalize_priority(tc.get("priority"))
        by_priority[priority].append(tc)

    # Select tests: P0 first, then P1, then P2
    selected = []
    remaining = max_tests

    for priority in ["P0", "P1", "P2"]:
        available = by_priority[priority]
        take = min(len(available), remaining)
        selected.extend(available[:take])
        remaining -= take
        if remaining <= 0:
            break

    # Count by priority
    priority_counts = {
        "P0": len(by_priority["P0"]),
        "P1": len(by_priority["P1"]),
        "P2": len(by_priority["P2"])
    }

    return selected, priority_counts


def analyze_inputs_node(state: AgentState) -> AgentState:
    """
    Analyze inputs node - loads, validates, and analyzes all inputs.

    This is the first node in the agent pipeline. It:
    1. Loads module_spec.json, testcases.csv, element_metadata
    2. Detects duplicate test cases
    3. Prioritizes by P0 > P1 > P2
    4. Caps at 10 tests
    5. Builds analysis_summary for human gate

    Args:
        state: Current agent state

    Returns:
        Updated state with loaded inputs and analysis
    """
    logger.info("=" * 60)
    logger.info("ANALYZE INPUTS NODE")
    logger.info("=" * 60)

    inputs_path = state.get("inputs_path", "")
    errors = []
    warnings = []

    # Update current node
    state["current_node"] = "analyze_inputs"
    state["node_history"] = state.get("node_history", []) + ["analyze_inputs"]

    # Log node start
    add_event_to_state(state, "node_start", "analyze_inputs")

    # Step 1: Check what exists
    logger.info(f"Checking inputs at: {inputs_path}")
    input_status = _check_inputs_exist(inputs_path)

    logger.info(f"  module_spec.json: {'Y' if input_status['module_spec'] else 'N'}")
    logger.info(f"  testcases.csv: {'Y' if input_status['testcases'] else 'N'}")
    logger.info(f"  element_metadata/: {'Y' if input_status['element_metadata'] else 'N'}")

    # Step 2: Load module_spec.json (REQUIRED)
    if not input_status["module_spec"]:
        errors.append("module_spec.json is required but not found")
        state["input_validation_errors"] = errors
        state["errors"] = state.get("errors", []) + errors
        add_event_to_state(state, "error", "analyze_inputs", {
            "error_type": "missing_file",
            "message": "module_spec.json required"
        })
        logger.error("ANALYZE INPUTS FAILED: module_spec.json required")
        return state

    try:
        module_spec, spec_warnings = _load_module_spec(inputs_path)
        warnings.extend(spec_warnings)
        state["module_spec"] = module_spec.model_dump()
        logger.info(f"Loaded module_spec: {module_spec.module_name}")
    except Exception as e:
        errors.append(f"Failed to load module_spec.json: {e}")
        state["input_validation_errors"] = errors
        add_event_to_state(state, "error", "analyze_inputs", {
            "error_type": "parse_error",
            "message": str(e)
        })
        logger.error(f"ANALYZE INPUTS FAILED: {e}")
        return state

    # Step 3: Load testcases.csv (REQUIRED)
    if not input_status["testcases"]:
        errors.append("testcases.csv is required but not found")
        state["input_validation_errors"] = errors
        add_event_to_state(state, "error", "analyze_inputs", {
            "error_type": "missing_file",
            "message": "testcases.csv required"
        })
        logger.error("ANALYZE INPUTS FAILED: testcases.csv required")
        return state

    try:
        test_cases_loaded, tc_warnings = _load_test_cases(inputs_path)
        warnings.extend(tc_warnings)
        test_cases_dicts = [tc.model_dump() for tc in test_cases_loaded]
        state["test_cases"] = test_cases_dicts
        logger.info(f"Loaded {len(test_cases_loaded)} test cases")
    except Exception as e:
        errors.append(f"Failed to load testcases.csv: {e}")
        state["input_validation_errors"] = errors
        add_event_to_state(state, "error", "analyze_inputs", {
            "error_type": "parse_error",
            "message": str(e)
        })
        logger.error(f"ANALYZE INPUTS FAILED: {e}")
        return state

    # Step 4: Load element_metadata (REQUIRED)
    if not input_status["element_metadata"]:
        errors.append("element_metadata/ directory is required but not found")
        state["input_validation_errors"] = errors
        add_event_to_state(state, "error", "analyze_inputs", {
            "error_type": "missing_file",
            "message": "element_metadata required"
        })
        logger.error("ANALYZE INPUTS FAILED: element_metadata required")
        return state

    try:
        page_metadata, elem_warnings = _load_element_metadata(inputs_path)
        warnings.extend(elem_warnings)
        state["page_metadata"] = {
            name: page.model_dump() for name, page in page_metadata.items()
        }
        logger.info(f"Loaded element metadata for {len(page_metadata)} pages")
    except Exception as e:
        errors.append(f"Failed to load element_metadata: {e}")
        state["input_validation_errors"] = errors
        add_event_to_state(state, "error", "analyze_inputs", {
            "error_type": "parse_error",
            "message": str(e)
        })
        logger.error(f"ANALYZE INPUTS FAILED: {e}")
        return state

    # Step 5: Analyze test cases
    logger.info("=" * 60)
    logger.info("TEST CASE ANALYSIS")
    logger.info("=" * 60)

    # Detect duplicates
    duplicates = _detect_duplicates(test_cases_dicts)
    logger.info(f"Duplicates found: {len(duplicates)}")

    # Prioritize and cap at 10 tests
    selected_tests, priority_counts = _prioritize_and_cap_tests(
        test_cases_dicts,
        duplicates,
        max_tests=MAX_TEST_CASES
    )
    logger.info(f"Selected {len(selected_tests)} tests (capped at {MAX_TEST_CASES})")

    # Build analysis summary
    analysis_summary = {
        "total_tests": len(test_cases_dicts),
        "duplicates": duplicates,
        "duplicates_count": len(duplicates),
        "by_priority": priority_counts,
        "selected_tests": selected_tests,
        "selected_count": len(selected_tests),
        "capped_at": MAX_TEST_CASES
    }

    state["analysis_summary"] = analysis_summary
    state["approved_tests"] = selected_tests  # Pre-populate, human gate can modify

    # Log analysis event
    add_event_to_state(state, "analysis_complete", "analyze_inputs", {
        "total_tests": len(test_cases_dicts),
        "duplicates_found": len(duplicates),
        "by_priority": priority_counts,
        "selected_count": len(selected_tests),
        "capped_at": MAX_TEST_CASES
    })

    # Step 6: Store validation results
    state["input_validation_errors"] = errors
    state["input_validation_warnings"] = warnings

    # Log summary
    logger.info("-" * 40)
    logger.info("ANALYSIS SUMMARY")
    logger.info(f"  Total test cases: {len(test_cases_dicts)}")
    logger.info(f"  Duplicates found: {len(duplicates)}")
    logger.info(f"  By priority: P0={priority_counts['P0']}, P1={priority_counts['P1']}, P2={priority_counts['P2']}")
    logger.info(f"  Selected tests: {len(selected_tests)} (max {MAX_TEST_CASES})")
    logger.info("-" * 40)

    # Log duplicates
    if duplicates:
        logger.warning("DUPLICATE TEST CASES:")
        for dup in duplicates[:5]:
            logger.warning(
                f"  {dup['test_id']} <- {dup['duplicate_of']} "
                f"({dup['similarity']}% similar) - {dup['recommendation']}"
            )
        if len(duplicates) > 5:
            logger.warning(f"  ... and {len(duplicates) - 5} more")

    # Log selected tests
    logger.info("SELECTED TESTS:")
    for i, tc in enumerate(selected_tests[:10], 1):
        priority = _normalize_priority(tc.get("priority"))
        logger.info(f"  {i}. [{priority}] {tc.get('test_id', 'N/A')} - {tc.get('test_name', 'N/A')}")

    if warnings:
        logger.info("WARNINGS:")
        for w in warnings[:5]:
            logger.warning(f"  {w}")

    # Log node complete
    add_event_to_state(state, "node_complete", "analyze_inputs")

    return state


# Keep old name as alias for backwards compatibility
onboarding_node = analyze_inputs_node
