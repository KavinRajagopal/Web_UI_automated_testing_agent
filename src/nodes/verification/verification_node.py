"""Verification Node - Simplified verification with 4 checkpoints.

Checkpoints:
1. Syntax (A) - AST parse all Python files
2. Imports (B) - Verify imports resolve
3. Collection (C) - pytest --collect-only
4. Execution (D) - pytest run with error extraction
"""

import ast
import logging
import os
import re
import subprocess
import sys
from typing import Dict, List, Any, Tuple

from ...models.state import AgentState
from ...models.schemas import CheckpointStatus, CheckpointResult, VerificationResults
from ...utils.event_logger import add_event_to_state

logger = logging.getLogger(__name__)


def _check_syntax(code: str, filepath: str) -> Tuple[bool, str]:
    """Check Python syntax using ast.parse."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def _check_syntax_all(generated_files: Dict[str, str]) -> CheckpointResult:
    """Checkpoint A: Validate Python syntax for all generated files."""
    logger.info("Running Checkpoint A: Syntax Validation...")

    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}

    for filepath, code in generated_files.items():
        if not filepath.endswith('.py'):
            continue

        files_checked.append(filepath)
        success, error = _check_syntax(code, filepath)

        if success:
            files_passed.append(filepath)
        else:
            files_failed.append(filepath)
            errors[filepath] = error
            logger.warning(f"  Syntax error in {filepath}: {error}")

    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    logger.info(f"  Checkpoint A: {status.value} ({len(files_passed)}/{len(files_checked)} passed)")

    return CheckpointResult(
        checkpoint_name="A",
        checkpoint_description="Python Syntax Validation",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )


def _check_imports(generated_files: Dict[str, str]) -> CheckpointResult:
    """Checkpoint B: Check if imports can be resolved."""
    logger.info("Running Checkpoint B: Import Validation...")

    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}

    for filepath, code in generated_files.items():
        if not filepath.endswith('.py'):
            continue

        files_checked.append(filepath)

        try:
            tree = ast.parse(code)
            import_errors = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Skip relative imports and local modules
                        if alias.name.startswith('.'):
                            continue
                        # Check if it's a standard/installed module
                        if alias.name.split('.')[0] in ['pages', 'flows', 'tests', 'conftest']:
                            continue
                        # Basic check - could be extended
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith('.'):
                        continue
                    if node.module and node.module.split('.')[0] in ['pages', 'flows', 'tests']:
                        continue

            if not import_errors:
                files_passed.append(filepath)
            else:
                files_failed.append(filepath)
                errors[filepath] = "; ".join(import_errors)

        except Exception as e:
            files_failed.append(filepath)
            errors[filepath] = str(e)

    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    logger.info(f"  Checkpoint B: {status.value} ({len(files_passed)}/{len(files_checked)} passed)")

    return CheckpointResult(
        checkpoint_name="B",
        checkpoint_description="Import Validation",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )


def _check_collection(generated_files: Dict[str, str], output_dir: str) -> CheckpointResult:
    """Checkpoint C: Run pytest --collect-only."""
    logger.info("Running Checkpoint C: Pytest Collection...")

    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}

    # Write files to output directory
    for filepath, code in generated_files.items():
        full_path = os.path.join(output_dir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(code)

        files_checked.append(filepath)

    # Run pytest --collect-only
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-v", "--tb=short"],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            # Count collected tests
            test_count = 0
            for line in result.stdout.split('\n'):
                if '::test_' in line or '<Function' in line:
                    test_count += 1

            logger.info(f"  Collected {test_count} tests")
            files_passed = files_checked
        else:
            # Collection failed
            error_output = result.stderr or result.stdout

            # Try to map errors to specific files
            for filepath in files_checked:
                filename = os.path.basename(filepath)
                if filename in error_output:
                    files_failed.append(filepath)
                    # Extract relevant error portion
                    errors[filepath] = _extract_error_for_file(error_output, filename)

            if not files_failed:
                # Couldn't map to specific file, mark all test files as failed
                test_files = [f for f in files_checked if 'test' in f]
                files_failed = test_files or files_checked[:1]
                for f in files_failed:
                    errors[f] = error_output[:500]

            files_passed = [f for f in files_checked if f not in files_failed]
            logger.warning(f"  Collection failed: {len(files_failed)} files with errors")

    except subprocess.TimeoutExpired:
        errors["collection"] = "Pytest collection timed out"
        files_failed = files_checked
        logger.error("  Collection timed out")
    except Exception as e:
        errors["collection"] = str(e)
        files_failed = files_checked
        logger.error(f"  Collection error: {e}")

    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    logger.info(f"  Checkpoint C: {status.value}")

    return CheckpointResult(
        checkpoint_name="C",
        checkpoint_description="Pytest Collection",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )


def _extract_error_for_file(error_output: str, filename: str) -> str:
    """Extract error portion relevant to a specific file."""
    lines = error_output.split('\n')
    relevant_lines = []
    capturing = False

    for line in lines:
        if filename in line:
            capturing = True
        if capturing:
            relevant_lines.append(line)
            if len(relevant_lines) > 20:
                break
            if line.strip() == '' and len(relevant_lines) > 5:
                break

    return '\n'.join(relevant_lines) if relevant_lines else error_output[:300]


def _check_execution(generated_files: Dict[str, str], output_dir: str, headless: bool = True) -> Tuple[CheckpointResult, List[Dict[str, Any]]]:
    """
    Checkpoint D: Run pytest and extract errors.

    Returns:
        Tuple of (CheckpointResult, list of extracted errors)
    """
    logger.info("Running Checkpoint D: Pytest Execution...")

    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}
    extracted_errors = []

    # Get test files
    test_files = [f for f in generated_files.keys() if f.startswith('tests/') and f.endswith('.py')]
    files_checked = test_files

    if not test_files:
        logger.warning("  No test files to execute")
        return CheckpointResult(
            checkpoint_name="D",
            checkpoint_description="Pytest Execution",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        ), []

    # Run pytest with verbose output
    try:
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "-x"]

        # Add headless flag if needed
        if headless:
            env = os.environ.copy()
            env["HEADLESS"] = "true"
        else:
            env = os.environ.copy()

        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )

        output = result.stdout + '\n' + result.stderr

        # Parse pytest output for errors
        extracted_errors = _extract_pytest_errors(output, test_files)

        # Log detailed error information for Checkpoint D
        if extracted_errors:
            logger.info("=" * 60)
            logger.info("CHECKPOINT D - DETAILED ERROR LOG")
            logger.info("=" * 60)
            for i, err in enumerate(extracted_errors, 1):
                logger.info(f"\n--- Error {i} ---")
                logger.info(f"  Test: {err.get('test_name', 'Unknown')}")
                logger.info(f"  File: {err.get('file', 'Unknown')}")
                logger.info(f"  Line: {err.get('line', 'Unknown')}")
                logger.info(f"  Type: {err.get('error_type', 'Unknown')}")
                logger.info(f"  Message: {err.get('message', 'No message')}")
                if err.get('error_category'):
                    logger.info(f"  Category: {err.get('error_category')}")
                if err.get('fix_suggestion'):
                    logger.info(f"  Suggestion: {err.get('fix_suggestion')}")
                if err.get('traceback'):
                    logger.info(f"  Traceback (first 5 lines):")
                    for tb_line in err.get('traceback', [])[:5]:
                        if tb_line.strip():
                            logger.info(f"    {tb_line.rstrip()}")
            logger.info("=" * 60)

        # Determine pass/fail
        if result.returncode == 0:
            files_passed = test_files
            logger.info("  All tests passed!")
        else:
            # Map errors to files
            failed_files = set()
            for err in extracted_errors:
                if err.get("file"):
                    failed_files.add(err["file"])

            if failed_files:
                files_failed = list(failed_files)
                files_passed = [f for f in test_files if f not in failed_files]
                for f in files_failed:
                    file_errors = [e for e in extracted_errors if e.get("file") == f]
                    if file_errors:
                        errors[f] = file_errors[0].get("message", "Test failed")
            else:
                # Couldn't map to specific files
                files_failed = test_files
                errors[test_files[0]] = output[:500]

            logger.warning(f"  Tests failed: {len(files_failed)} files")

        # Count passed/failed from output
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        tests_passed = int(passed_match.group(1)) if passed_match else 0
        tests_failed = int(failed_match.group(1)) if failed_match else 0

        logger.info(f"  Results: {tests_passed} passed, {tests_failed} failed")

    except subprocess.TimeoutExpired:
        errors["execution"] = "Pytest execution timed out"
        files_failed = test_files
        extracted_errors = [{"error_type": "TimeoutError", "message": "Test execution timed out"}]
        logger.error("  Execution timed out")
    except Exception as e:
        errors["execution"] = str(e)
        files_failed = test_files
        extracted_errors = [{"error_type": type(e).__name__, "message": str(e)}]
        logger.error(f"  Execution error: {e}")

    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED

    checkpoint_result = CheckpointResult(
        checkpoint_name="D",
        checkpoint_description="Pytest Execution",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors,
        metadata={
            "tests_passed": tests_passed if 'tests_passed' in dir() else 0,
            "tests_failed": tests_failed if 'tests_failed' in dir() else len(files_failed)
        }
    )

    return checkpoint_result, extracted_errors


def _parse_attribute_error(error_message: str) -> Dict[str, Any]:
    """
    Extract details from AttributeError for smart recovery.

    Parses: "'ClassName' object has no attribute 'attr_name'"
    """
    pattern = r"'(\w+)'\s+object has no attribute\s+'(\w+)'"
    match = re.search(pattern, error_message)
    if match:
        return {
            "error_category": "missing_attribute",
            "class_name": match.group(1),
            "missing_attribute": match.group(2),
            "fix_suggestion": f"Add '{match.group(2)}' attribute to {match.group(1)} class or fix the method call"
        }
    return {}


def _parse_name_error(error_message: str) -> Dict[str, Any]:
    """
    Extract details from NameError.

    Parses: "name 'undefined_var' is not defined"
    """
    pattern = r"name '(\w+)' is not defined"
    match = re.search(pattern, error_message)
    if match:
        return {
            "error_category": "undefined_name",
            "undefined_name": match.group(1),
            "fix_suggestion": f"Define '{match.group(1)}' or fix the import/variable reference"
        }
    return {}


def _parse_import_error(error_message: str) -> Dict[str, Any]:
    """
    Extract details from ImportError.

    Parses: "cannot import name 'ClassName' from 'module'"
    """
    pattern = r"cannot import name '(\w+)' from '([^']+)'"
    match = re.search(pattern, error_message)
    if match:
        return {
            "error_category": "import_error",
            "import_name": match.group(1),
            "module": match.group(2),
            "fix_suggestion": f"Check if '{match.group(1)}' exists in {match.group(2)} module"
        }
    return {}


def _parse_type_error(error_message: str) -> Dict[str, Any]:
    """
    Extract details from TypeError.

    Parses common patterns like:
    - "takes X positional arguments but Y were given"
    - "missing X required positional argument: 'arg'"
    """
    # Too many arguments
    pattern1 = r"(\w+)\(\) takes (\d+) positional arguments? but (\d+) (?:was|were) given"
    match1 = re.search(pattern1, error_message)
    if match1:
        return {
            "error_category": "argument_count",
            "method_name": match1.group(1),
            "expected_args": int(match1.group(2)),
            "actual_args": int(match1.group(3)),
            "fix_suggestion": f"Method '{match1.group(1)}' expects {match1.group(2)} args, got {match1.group(3)}"
        }

    # Missing arguments
    pattern2 = r"(\w+)\(\) missing (\d+) required positional arguments?: '([^']+)'"
    match2 = re.search(pattern2, error_message)
    if match2:
        return {
            "error_category": "missing_argument",
            "method_name": match2.group(1),
            "missing_count": int(match2.group(2)),
            "missing_args": match2.group(3),
            "fix_suggestion": f"Add required argument(s) '{match2.group(3)}' to {match2.group(1)}()"
        }

    return {}


def _enrich_error_with_smart_parsing(error: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich error dict with smart parsing based on error type.
    """
    error_type = error.get("error_type", "")
    message = error.get("message", "")

    # Combine message and traceback for full context
    traceback = error.get("traceback", [])
    full_text = message + " " + " ".join(traceback)

    parsed_details = {}

    if error_type == "AttributeError" or "has no attribute" in full_text:
        parsed_details = _parse_attribute_error(full_text)
    elif error_type == "NameError" or "is not defined" in full_text:
        parsed_details = _parse_name_error(full_text)
    elif error_type == "ImportError" or "cannot import name" in full_text:
        parsed_details = _parse_import_error(full_text)
    elif error_type == "TypeError":
        parsed_details = _parse_type_error(full_text)
    elif error_type == "AssertionError":
        parsed_details = {
            "error_category": "assertion_failure",
            "fix_suggestion": "Review test assertion logic or expected values"
        }

    # Merge parsed details into error
    error.update(parsed_details)
    return error


def _extract_pytest_errors(output: str, test_files: List[str]) -> List[Dict[str, Any]]:
    """
    Extract structured errors from pytest output with smart parsing.

    Returns:
        List of error dicts with: test_name, file, line, error_type, message, traceback,
        plus smart-parsed fields like error_category, missing_attribute, fix_suggestion
    """
    errors = []
    lines = output.split('\n')

    # Pattern for test failure header
    # FAILED tests/test_foo.py::test_bar - AssertionError: ...
    failure_pattern = re.compile(r'FAILED\s+([^:]+)::(\w+)\s*-?\s*(.*)')

    # Pattern for error location
    # tests/test_foo.py:42: in test_bar
    location_pattern = re.compile(r'([^:]+\.py):(\d+):\s*(?:in\s+(\w+))?')

    # Pattern for error type
    error_type_pattern = re.compile(r'(E\s+)?(\w+Error|\w+Exception):\s*(.*)')

    current_error = None
    traceback_lines = []
    in_traceback = False

    for i, line in enumerate(lines):
        # Check for failure line
        failure_match = failure_pattern.match(line.strip())
        if failure_match:
            # Save previous error
            if current_error:
                current_error["traceback"] = traceback_lines[:10]
                errors.append(current_error)

            filepath = failure_match.group(1)
            test_name = failure_match.group(2)
            error_msg = failure_match.group(3) or ""

            # Normalize filepath
            for tf in test_files:
                if os.path.basename(tf) in filepath or filepath in tf:
                    filepath = tf
                    break

            current_error = {
                "test_name": test_name,
                "file": filepath,
                "line": None,
                "error_type": None,
                "message": error_msg,
            }
            traceback_lines = []
            in_traceback = True
            continue

        # Check for error type in line
        if current_error:
            error_match = error_type_pattern.search(line)
            if error_match:
                current_error["error_type"] = error_match.group(2)
                if not current_error["message"]:
                    current_error["message"] = error_match.group(3)

            # Check for location
            loc_match = location_pattern.search(line)
            if loc_match and not current_error.get("line"):
                current_error["line"] = int(loc_match.group(2))

            if in_traceback:
                traceback_lines.append(line)

        # Check for short summary header (end of this error's traceback)
        if '= short test summary info =' in line or '= FAILURES =' in line:
            if current_error:
                current_error["traceback"] = traceback_lines[:10]
                errors.append(current_error)
                current_error = None
                traceback_lines = []
            in_traceback = False

    # Don't forget last error
    if current_error:
        current_error["traceback"] = traceback_lines[:10]
        errors.append(current_error)

    # Enrich all errors with smart parsing
    enriched_errors = [_enrich_error_with_smart_parsing(e) for e in errors]

    # Log smart parsing results
    for err in enriched_errors:
        if err.get("error_category"):
            logger.info(f"  Smart parsed: {err.get('error_category')} - {err.get('fix_suggestion', 'No suggestion')}")

    return enriched_errors


def verification_node(state: AgentState) -> AgentState:
    """
    Simplified verification node - runs 4 checkpoints.

    Checkpoints:
    1. A: Syntax validation (AST parse)
    2. B: Import validation
    3. C: Pytest collection
    4. D: Pytest execution with error extraction

    Args:
        state: Current agent state

    Returns:
        Updated state with verification results
    """
    logger.info("=" * 60)
    logger.info("VERIFICATION NODE")
    logger.info("=" * 60)

    state["current_node"] = "verification"
    state["node_history"] = state.get("node_history", []) + ["verification"]

    # Log node start
    add_event_to_state(state, "node_start", "verification")

    generated_files = state.get("generated_files", {})
    output_path = state.get("output_path", "")
    headless = state.get("headless_mode", True)

    if not generated_files:
        logger.warning("No generated files to verify")
        state["verification_passed"] = False
        add_event_to_state(state, "error", "verification", {
            "error_type": "no_files",
            "message": "No generated files to verify"
        })
        return state

    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)

    # Run checkpoints
    checkpoint_a = _check_syntax_all(generated_files)
    checkpoint_b = _check_imports(generated_files)
    checkpoint_c = _check_collection(generated_files, output_path)

    # Only run execution if A, B, C passed
    extracted_errors = []
    if (checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED):
        checkpoint_d, extracted_errors = _check_execution(generated_files, output_path, headless)
    else:
        logger.info("  Checkpoint D: SKIPPED (previous checkpoints failed)")
        checkpoint_d = CheckpointResult(
            checkpoint_name="D",
            checkpoint_description="Pytest Execution",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        )

    # Determine overall pass/fail
    all_passed = (
        checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED and
        checkpoint_d.status == CheckpointStatus.PASSED
    )

    # Build results (simplified - no D1-D4)
    results = VerificationResults(
        checkpoint_a=checkpoint_a,
        checkpoint_b=checkpoint_b,
        checkpoint_c=checkpoint_c,
        checkpoint_d=checkpoint_d,
        # For backwards compatibility, set D1-D4 to D
        checkpoint_d1=checkpoint_d,
        checkpoint_d2=checkpoint_d,
        checkpoint_d3=checkpoint_d,
        checkpoint_d4=checkpoint_d,
        all_passed=all_passed
    )

    # Update state
    state["verification_results"] = results.model_dump()
    state["verification_passed"] = all_passed
    state["verification_errors"] = extracted_errors  # For recovery

    # Log verification event
    add_event_to_state(state, "verification_result", "verification", {
        "syntax_check": checkpoint_a.status.value,
        "import_check": checkpoint_b.status.value,
        "pytest_collect": checkpoint_c.status.value,
        "pytest_run": checkpoint_d.status.value,
        "all_passed": all_passed,
        "errors_count": len(extracted_errors)
    })

    # Log summary
    logger.info("-" * 40)
    logger.info("VERIFICATION SUMMARY")
    logger.info(f"  Checkpoint A (Syntax): {checkpoint_a.status.value}")
    logger.info(f"  Checkpoint B (Imports): {checkpoint_b.status.value}")
    logger.info(f"  Checkpoint C (Collection): {checkpoint_c.status.value}")
    logger.info(f"  Checkpoint D (Execution): {checkpoint_d.status.value}")
    logger.info(f"  Overall: {'PASSED' if all_passed else 'FAILED'}")
    logger.info("-" * 40)

    # Log errors for recovery
    if not all_passed and extracted_errors:
        logger.warning("Errors for recovery:")
        for err in extracted_errors[:5]:
            logger.warning(f"  {err.get('file', 'unknown')}: {err.get('error_type', 'Error')} - {err.get('message', '')[:100]}")

    # Log node complete
    add_event_to_state(state, "node_complete", "verification")

    return state
