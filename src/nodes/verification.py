"""Verification Node - Validates generated code.

Four verification checkpoints:
A. Syntax Check - Python ast.parse validation
B. Import Check - Verify all imports resolve
C. Pytest Collection - pytest --collect-only
D. Test Execution - Actually run the tests and verify they pass

Supports multiple platforms:
- Web (Selenium) - default timeout 120s
- Android (Appium) - timeout 600s (slower device execution)
"""

import ast
import importlib.util
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Any, Tuple, Optional

from ..models.state import AgentState
from ..models.schemas import CheckpointStatus, CheckpointResult, VerificationResults
from ..tools.code_executor import run_pytest

logger = logging.getLogger(__name__)


# =============================================================================
# AST HELPER FUNCTIONS FOR CONSISTENCY CHECKING
# =============================================================================

def _extract_class_name(tree: ast.AST) -> Optional[str]:
    """Extract the main class name from an AST.

    Args:
        tree: Parsed AST

    Returns:
        Class name or None if not found
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            return node.name
    return None


def _extract_public_methods(tree: ast.AST) -> List[str]:
    """Extract public method names from a class in the AST.

    Args:
        tree: Parsed AST

    Returns:
        List of public method names (excluding __dunder__ and _private)
    """
    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Include public methods and exclude __dunder__ methods
                    if not item.name.startswith('_'):
                        methods.append(item.name)
    return methods


def _extract_method_calls_on_pages(tree: ast.AST, page_classes: List[str]) -> Dict[str, List[str]]:
    """Extract method calls made on page object instances.

    This analyzes the AST to find patterns like:
    - page.method_name()
    - self.page.method_name()
    - login_screen.enter_username()

    Args:
        tree: Parsed AST
        page_classes: List of page class names to look for

    Returns:
        Dict mapping page class names to list of method names called
    """
    calls = {}

    # Create lowercase mapping for class names
    class_map = {cls.lower(): cls for cls in page_classes}
    class_map.update({cls.lower().replace('page', ''): cls for cls in page_classes})
    class_map.update({cls.lower().replace('screen', ''): cls for cls in page_classes})

    # Also track variable assignments to map instances to classes
    # e.g., login_screen = LoginScreen(driver) -> login_screen maps to LoginScreen
    instance_to_class = {}

    for node in ast.walk(tree):
        # Track variable assignments of page objects
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        class_name = node.value.func.id
                        if class_name in page_classes:
                            instance_to_class[target.id] = class_name

        # Track method calls
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            method_name = node.func.attr

            # Get the object the method is called on
            obj = node.func.value

            # Handle: instance.method() where instance was assigned a page class
            if isinstance(obj, ast.Name):
                var_name = obj.id
                if var_name in instance_to_class:
                    page_class = instance_to_class[var_name]
                    if page_class not in calls:
                        calls[page_class] = []
                    if method_name not in calls[page_class]:
                        calls[page_class].append(method_name)
                # Also check if variable name matches a page class pattern
                elif var_name.lower() in class_map:
                    page_class = class_map[var_name.lower()]
                    if page_class not in calls:
                        calls[page_class] = []
                    if method_name not in calls[page_class]:
                        calls[page_class].append(method_name)

            # Handle: self.page.method() patterns
            elif isinstance(obj, ast.Attribute):
                attr_name = obj.attr
                if attr_name.lower() in class_map:
                    page_class = class_map[attr_name.lower()]
                    if page_class not in calls:
                        calls[page_class] = []
                    if method_name not in calls[page_class]:
                        calls[page_class].append(method_name)

    return calls

# Platform-specific timeouts
WEB_EXECUTION_TIMEOUT = 120  # 2 minutes for web tests
ANDROID_EXECUTION_TIMEOUT = 600  # 10 minutes for Android tests (slower)


def _check_syntax(code: str, filepath: str) -> Tuple[bool, str]:
    """
    Check Python syntax using ast.parse.
    
    Args:
        code: Python code string
        filepath: File path (for error messages)
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def checkpoint_a_syntax(generated_files: Dict[str, str]) -> CheckpointResult:
    """
    Checkpoint A: Validate Python syntax for all generated files.
    
    Args:
        generated_files: Dict of filepath -> code content
        
    Returns:
        CheckpointResult with syntax validation results
    """
    logger.info("Running Checkpoint A: Syntax Validation...")
    
    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}
    
    for filepath, code in generated_files.items():
        # Only check Python files
        if not filepath.endswith('.py'):
            continue
        
        files_checked.append(filepath)
        
        success, error = _check_syntax(code, filepath)
        
        if success:
            files_passed.append(filepath)
            logger.debug(f"  ✓ {filepath}")
        else:
            files_failed.append(filepath)
            errors[filepath] = error
            logger.warning(f"  ✗ {filepath}: {error}")
    
    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    
    return CheckpointResult(
        checkpoint_name="A",
        checkpoint_description="Python Syntax Validation",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )


def checkpoint_b_imports(generated_files: Dict[str, str], platform_type: str = "web") -> CheckpointResult:
    """
    Checkpoint B: Verify imports can be resolved.

    Note: This checks standard library and installed packages only.
    Internal imports between generated files are assumed valid.

    Args:
        generated_files: Dict of filepath -> code content
        platform_type: Target platform ('web' or 'android')

    Returns:
        CheckpointResult with import validation results
    """
    logger.info("Running Checkpoint B: Import Validation...")

    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}

    # Known internal modules (generated by us)
    internal_modules = {"pages", "flows", "tests"}

    # Known external modules that should be available
    # Add appium for Android platform
    known_external = {"selenium", "pytest", "allure"}
    if platform_type == "android":
        known_external.add("appium")
    
    for filepath, code in generated_files.items():
        if not filepath.endswith('.py'):
            continue
        
        files_checked.append(filepath)
        file_errors = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Check import statements
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name not in internal_modules and module_name not in known_external:
                            if not _can_import(module_name):
                                file_errors.append(f"Cannot import '{alias.name}'")

                # Check from ... import statements
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name not in internal_modules and module_name not in known_external:
                            if not _can_import(module_name):
                                file_errors.append(f"Cannot import from '{node.module}'")
            
            if file_errors:
                files_failed.append(filepath)
                errors[filepath] = "; ".join(file_errors)
                logger.warning(f"  ✗ {filepath}: {errors[filepath]}")
            else:
                files_passed.append(filepath)
                logger.debug(f"  ✓ {filepath}")
                
        except SyntaxError:
            # Already caught in checkpoint A
            files_passed.append(filepath)
    
    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    
    return CheckpointResult(
        checkpoint_name="B",
        checkpoint_description="Import Resolution",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )


def _can_import(module_name: str) -> bool:
    """Check if a module can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ModuleNotFoundError, ValueError):
        return False


def checkpoint_b5_consistency(
    generated_files: Dict[str, str],
    base_page_methods: Optional[List[str]] = None
) -> CheckpointResult:
    """
    Checkpoint B.5: Check method consistency between page objects and tests.

    This runs BEFORE the expensive Checkpoint D test execution to catch
    method mismatches early. Uses AST analysis to:
    1. Extract methods from all generated page objects
    2. Extract method calls from test files
    3. Detect calls to methods that don't exist

    Args:
        generated_files: Dict of filepath -> code content
        base_page_methods: Optional list of BasePage method names (for inclusion)

    Returns:
        CheckpointResult with consistency validation results
    """
    logger.info("Running Checkpoint B.5: Method Consistency...")

    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}

    # Default BasePage methods available to all page objects
    if base_page_methods is None:
        base_page_methods = [
            # Common methods in both Web and Android BasePage
            'find_element', 'find_element_clickable', 'find_element_visible',
            'is_element_present', 'get_element_text', 'enter_text', 'click',
            # Android-specific
            'tap', 'long_press', 'hide_keyboard', 'is_keyboard_shown',
            'swipe', 'swipe_up', 'swipe_down', 'scroll_to_element',
            'get_current_activity', 'get_current_package', 'wait_for_activity',
            'background_app', 'launch_app', 'close_app', 'clear_text',
            # Web-specific
            'navigate',
        ]

    # 1. Extract methods from all page objects
    page_methods = {}
    for filepath, code in generated_files.items():
        if filepath.startswith("pages/") and filepath != "pages/base_page.py" and filepath.endswith(".py"):
            if filepath == "pages/__init__.py":
                continue

            files_checked.append(filepath)

            try:
                tree = ast.parse(code)
                class_name = _extract_class_name(tree)
                if class_name:
                    methods = _extract_public_methods(tree)
                    # Include inherited BasePage methods
                    all_methods = list(set(methods + base_page_methods))
                    page_methods[class_name] = all_methods
                    logger.debug(f"  {class_name}: {len(methods)} methods defined")
            except SyntaxError as e:
                # Syntax errors are caught in Checkpoint A
                logger.debug(f"  Skipping {filepath} due to syntax error: {e}")
                continue

    if not page_methods:
        logger.info("  No page objects found to validate")
        return CheckpointResult(
            checkpoint_name="B.5",
            checkpoint_description="Method Consistency",
            status=CheckpointStatus.PASSED,
            files_checked=files_checked,
            files_passed=files_checked,
            files_failed=[],
            errors={}
        )

    # 2. Extract method calls from tests and check consistency
    for filepath, code in generated_files.items():
        if filepath.startswith("tests/test_") and filepath.endswith(".py"):
            files_checked.append(filepath)

            try:
                tree = ast.parse(code)
                calls = _extract_method_calls_on_pages(tree, list(page_methods.keys()))

                file_errors = []
                for page_class, called_methods in calls.items():
                    available = set(page_methods.get(page_class, []))
                    for method in called_methods:
                        if method not in available:
                            file_errors.append(
                                f"Test calls undefined method '{method}()' on {page_class}. "
                                f"Available methods: {sorted(list(available)[:10])}..."
                            )

                if file_errors:
                    files_failed.append(filepath)
                    errors[filepath] = "\n".join(file_errors)
                    logger.warning(f"  ✗ {filepath}: {len(file_errors)} method mismatches")
                    for err in file_errors[:3]:  # Show first 3 errors
                        logger.warning(f"    - {err[:100]}")
                else:
                    files_passed.append(filepath)
                    logger.debug(f"  ✓ {filepath}")

            except SyntaxError as e:
                # Syntax errors are caught in Checkpoint A
                logger.debug(f"  Skipping {filepath} due to syntax error: {e}")
                continue

    # Mark page files as passed (they were checked for method extraction)
    for filepath in files_checked:
        if filepath.startswith("pages/") and filepath not in files_failed:
            if filepath not in files_passed:
                files_passed.append(filepath)

    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED

    if status == CheckpointStatus.PASSED:
        logger.info(f"  ✓ All method calls are consistent")
    else:
        logger.warning(f"  ✗ Found method mismatches in {len(files_failed)} files")

    return CheckpointResult(
        checkpoint_name="B.5",
        checkpoint_description="Method Consistency",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors,
        metadata={
            "page_classes_analyzed": len(page_methods),
            "method_mismatches_found": len(errors)
        }
    )


def checkpoint_c_collect(
    generated_files: Dict[str, str],
    output_dir: str
) -> CheckpointResult:
    """
    Checkpoint C: Run pytest --collect-only to verify test discovery.
    
    Writes files to temp directory and runs pytest collection.
    
    Args:
        generated_files: Dict of filepath -> code content
        output_dir: Output directory to write files
        
    Returns:
        CheckpointResult with collection results
    """
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
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Parse collected tests
            output_lines = result.stdout.strip().split('\n')
            test_count = 0
            for line in output_lines:
                if '::test_' in line or line.strip().startswith('<Function'):
                    test_count += 1
            
            logger.info(f"  Collected {test_count} tests")
            files_passed = files_checked
            
        else:
            # Collection failed
            error_msg = result.stderr or result.stdout
            errors["collection"] = error_msg[:500]  # Truncate long errors
            files_failed = [f for f in files_checked if f.endswith('.py') and 'test' in f]
            files_passed = [f for f in files_checked if f not in files_failed]
            logger.warning(f"  Collection failed: {error_msg[:200]}")
            
    except subprocess.TimeoutExpired:
        errors["collection"] = "Pytest collection timed out"
        files_failed = files_checked
        logger.error("  Collection timed out")
    except Exception as e:
        errors["collection"] = str(e)
        files_failed = files_checked
        logger.error(f"  Collection error: {e}")
    
    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    
    return CheckpointResult(
        checkpoint_name="C",
        checkpoint_description="Pytest Collection",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )


def _extract_error_type(error_line: str) -> Optional[str]:
    """Extract error type from pytest error line."""
    error_patterns = [
        r'AttributeError: (.+)',
        r'AssertionError: (.+)',
        r'NameError: (.+)',
        r'TypeError: (.+)',
        r'ImportError: (.+)',
        r'TimeoutException: (.+)',
        r'NoSuchElementException: (.+)',
        r'WebDriverException: (.+)',
        r'TimeoutError: (.+)'
    ]
    
    for pattern in error_patterns:
        match = re.search(pattern, error_line)
        if match:
            return match.group(0)
    return None


def checkpoint_d_execution(
    generated_files: Dict[str, str],
    output_dir: str,
    timeout: int = None,
    platform_type: str = "web"
) -> CheckpointResult:
    """
    Checkpoint D: Actually run the tests and verify they pass.

    This catches runtime errors like:
    - AttributeError (wrong method names)
    - AssertionError (test logic failures)
    - Import errors at runtime
    - Selenium/WebDriver issues (web)
    - Appium issues (Android)

    Args:
        generated_files: Dict of filepath -> code content
        output_dir: Output directory with test files
        timeout: Max execution time in seconds (auto-detected if None)
        platform_type: Target platform ('web' or 'android')

    Returns:
        CheckpointResult with test execution results
    """
    # Set platform-appropriate timeout if not specified
    if timeout is None:
        if platform_type == "android":
            timeout = ANDROID_EXECUTION_TIMEOUT
            logger.info(f"Running Checkpoint D: Test Execution (Android, timeout={timeout}s)...")
        else:
            timeout = WEB_EXECUTION_TIMEOUT
            logger.info(f"Running Checkpoint D: Test Execution (Web, timeout={timeout}s)...")
    else:
        logger.info(f"Running Checkpoint D: Test Execution (timeout={timeout}s)...")
    start_time = time.time()
    
    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}
    
    # Ensure all files are written
    for filepath, code in generated_files.items():
        full_path = os.path.join(output_dir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(code)
        if filepath.endswith('.py'):
            files_checked.append(filepath)
    
    # Run pytest
    try:
        result = run_pytest(
            test_dir=output_dir,
            collect_only=False,
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if result["success"] and result["failed"] == 0:
            # All tests passed!
            logger.info(f"  ✓ All {result['passed']} tests passed in {duration:.2f}s")
            files_passed = files_checked
            status = CheckpointStatus.PASSED
            
            return CheckpointResult(
                checkpoint_name="D",
                checkpoint_description="Test Execution",
                status=status,
                files_checked=files_checked,
                files_passed=files_passed,
                files_failed=files_failed,
                errors=errors,
                duration_seconds=duration,
                metadata={
                    "tests_passed": result.get("passed", 0),
                    "tests_failed": result.get("failed", 0),
                    "tests_errors": result.get("errors", 0)
                }
            )
        else:
            # Tests failed - parse errors
            status = CheckpointStatus.FAILED
            output = result["output"]
            
            logger.warning(f"  ✗ {result['failed']} tests failed, {result['passed']} passed")
            
            # Parse pytest output to extract failures
            # Improved parsing to handle various pytest output formats
            current_test = None
            current_file = None
            error_lines = []
            in_traceback = False
            error_type = None
            
            lines = output.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Detect test name and file (multiple formats)
                # Format 1: "tests/test_saucedemo.py::test_name FAILED"
                # Format 2: "FAILED tests/test_saucedemo.py::test_name"
                # Format 3: "test_name FAILED"
                if ('::test_' in line or '::Test' in line) and ('FAILED' in line or 'ERROR' in line):
                    # Extract file and test name
                    test_match = re.search(r'([^/\s]+\.py)::([^\s]+)', line)
                    if test_match:
                        current_file = test_match.group(1)
                        current_test = test_match.group(2)
                        error_lines = []
                        in_traceback = False
                        error_type = None
                        logger.debug(f"Found failed test: {current_file}::{current_test}")
                
                # Detect error type (look for "E   " lines)
                if line.startswith('E   ') and not in_traceback:
                    extracted_type = _extract_error_type(line)
                    if extracted_type:
                        error_type = extracted_type
                        in_traceback = True
                        error_lines.append(line.strip())
                        logger.debug(f"Found error type: {error_type}")
                
                # Collect traceback
                if in_traceback:
                    if line.startswith('E   ') or (line.startswith(' ') and len(line.strip()) > 0 and not line.strip().startswith('=')):
                        error_lines.append(line.strip())
                    elif line.strip() and not line.startswith('=') and not line.startswith('-') and 'FAILED' not in line:
                        # End of traceback - save the error
                        if current_file and error_lines:
                            # Limit error message length
                            error_msg = '\n'.join(error_lines[:20])
                            
                            # Map to actual source file (test file or page file)
                            # If error is in a page object, find that file
                            source_file = current_file
                            for error_line in error_lines:
                                # Check if error references a page file
                                # Pattern: File "/path/to/pages/login_page.py", line X
                                page_match = re.search(r'File "([^"]+(?:pages|flows)/[^"]+\.py)"', error_line)
                                if page_match:
                                    full_path = page_match.group(1)
                                    # Extract relative path from output_dir
                                    if output_dir in full_path:
                                        source_file = full_path.replace(output_dir + '/', '')
                                    else:
                                        # Extract just the relative path
                                        # Try to find pages/ or flows/ in path
                                        path_parts = full_path.split('/')
                                        if 'pages' in path_parts or 'flows' in path_parts:
                                            idx = max(path_parts.index('pages') if 'pages' in path_parts else -1,
                                                    path_parts.index('flows') if 'flows' in path_parts else -1)
                                            if idx >= 0:
                                                source_file = '/'.join(path_parts[idx:])
                                    logger.debug(f"Mapped error to source file: {source_file}")
                                    break
                            
                            if source_file not in errors:
                                errors[source_file] = []
                            
                            error_summary = f"{current_test}: {error_type or 'Error'}"
                            errors[source_file].append(f"{error_summary}\n{error_msg}")
                            logger.debug(f"Added error for {source_file}: {error_summary[:50]}")
                        
                        in_traceback = False
                        error_lines = []
                
                i += 1
            
            # Handle any remaining error in traceback
            if in_traceback and current_file and error_lines:
                error_msg = '\n'.join(error_lines[:20])
                source_file = current_file
                for error_line in error_lines:
                    page_match = re.search(r'File "([^"]+(?:pages|flows)/[^"]+\.py)"', error_line)
                    if page_match:
                        full_path = page_match.group(1)
                        if output_dir in full_path:
                            source_file = full_path.replace(output_dir + '/', '')
                        else:
                            path_parts = full_path.split('/')
                            if 'pages' in path_parts or 'flows' in path_parts:
                                idx = max(path_parts.index('pages') if 'pages' in path_parts else -1,
                                        path_parts.index('flows') if 'flows' in path_parts else -1)
                                if idx >= 0:
                                    source_file = '/'.join(path_parts[idx:])
                        break
                
                if source_file not in errors:
                    errors[source_file] = []
                error_summary = f"{current_test or 'Unknown'}: {error_type or 'Error'}"
                errors[source_file].append(f"{error_summary}\n{error_msg}")
            
            # Convert error lists to strings for storage
            for filepath, error_list in errors.items():
                if isinstance(error_list, list):
                    errors[filepath] = '\n\n'.join(error_list)
            
            # If we couldn't parse, use raw output
            if not errors:
                logger.warning("Could not parse pytest errors, using raw output")
                errors["test_execution"] = output[:2000]  # Truncate long output
            else:
                logger.info(f"Parsed {len(errors)} files with errors: {list(errors.keys())}")
            
            files_failed = list(errors.keys())
            files_passed = [f for f in files_checked if f not in files_failed]
            
            # Ensure status is FAILED if there are errors or test failures
            if errors or result.get("failed", 0) > 0 or result.get("errors", 0) > 0:
                status = CheckpointStatus.FAILED
                logger.warning(f"  ✗ Checkpoint D FAILED: {result.get('failed', 0)} tests failed, {result.get('passed', 0)} passed")
            else:
                status = CheckpointStatus.PASSED
                logger.info(f"  ✓ Checkpoint D PASSED: {result.get('passed', 0)} tests passed")
            
            return CheckpointResult(
                checkpoint_name="D",
                checkpoint_description="Test Execution",
                status=status,
                files_checked=files_checked,
                files_passed=files_passed,
                files_failed=files_failed,
                errors=errors,
                duration_seconds=duration,
                metadata={
                    "tests_passed": result.get("passed", 0),
                    "tests_failed": result.get("failed", 0),
                    "tests_errors": result.get("errors", 0)
                }
            )
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  Checkpoint D error: {e}")
        errors["test_execution"] = str(e)
        files_failed = files_checked
        
        return CheckpointResult(
            checkpoint_name="D",
            checkpoint_description="Test Execution",
            status=CheckpointStatus.FAILED,
            files_checked=files_checked,
            files_passed=[],
            files_failed=files_failed,
            errors=errors,
            duration_seconds=duration
        )


def verification_node(state: AgentState) -> AgentState:
    """
    Verification node - runs all verification checkpoints.

    Supports multiple platforms:
    - Web (Selenium)
    - Android (Appium) - uses longer timeout

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

    generated_files = state.get("generated_files", {})
    output_path = state.get("output_path", "")

    # Get platform type
    module_spec = state.get("module_spec", {})
    platform_type = state.get("platform_type", module_spec.get("platform_type", "web"))

    logger.info(f"Platform: {platform_type}")

    if not generated_files:
        logger.warning("No generated files to verify")
        state["verification_passed"] = False
        return state

    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)

    # Run checkpoints
    checkpoint_a = checkpoint_a_syntax(generated_files)
    logger.info(f"Checkpoint A: {checkpoint_a.status.value} ({len(checkpoint_a.files_passed)}/{len(checkpoint_a.files_checked)} passed)")

    checkpoint_b = checkpoint_b_imports(generated_files, platform_type=platform_type)
    logger.info(f"Checkpoint B: {checkpoint_b.status.value} ({len(checkpoint_b.files_passed)}/{len(checkpoint_b.files_checked)} passed)")

    # Run Checkpoint B.5: Method Consistency (only if A and B passed)
    # This catches method mismatches BEFORE the expensive test execution
    checkpoint_b5 = None
    if (checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED):

        checkpoint_b5 = checkpoint_b5_consistency(generated_files)
        logger.info(f"Checkpoint B.5: {checkpoint_b5.status.value} ({len(checkpoint_b5.files_passed)}/{len(checkpoint_b5.files_checked)} passed)")
    else:
        logger.info("Checkpoint B.5: SKIPPED (previous checkpoints failed)")
        checkpoint_b5 = CheckpointResult(
            checkpoint_name="B.5",
            checkpoint_description="Method Consistency",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        )

    checkpoint_c = checkpoint_c_collect(generated_files, output_path)
    logger.info(f"Checkpoint C: {checkpoint_c.status.value}")

    # Run Checkpoint D: Test Execution (only if A, B, B.5, C passed)
    checkpoint_d = None
    if (checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_b5.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED):

        checkpoint_d = checkpoint_d_execution(
            generated_files, output_path, platform_type=platform_type
        )
        test_info = checkpoint_d.metadata.get("tests_passed", 0)
        test_failed = checkpoint_d.metadata.get("tests_failed", 0)
        logger.info(f"Checkpoint D: {checkpoint_d.status.value} ({test_info} passed, {test_failed} failed)")
    else:
        logger.info("Checkpoint D: SKIPPED (previous checkpoints failed)")
        # Create a skipped checkpoint D
        checkpoint_d = CheckpointResult(
            checkpoint_name="D",
            checkpoint_description="Test Execution",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        )
    
    # Build verification results
    results = VerificationResults(
        checkpoint_a=checkpoint_a,
        checkpoint_b=checkpoint_b,
        checkpoint_b5=checkpoint_b5,
        checkpoint_c=checkpoint_c,
        checkpoint_d=checkpoint_d,
        all_passed=False
    )

    # Check if all passed (including B.5 and D)
    all_passed = (
        checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_b5.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED and
        checkpoint_d.status == CheckpointStatus.PASSED
    )
    results.all_passed = all_passed
    
    # Update state
    state["verification_results"] = results.model_dump()
    state["verification_passed"] = all_passed
    
    # Log summary
    logger.info("-" * 40)
    logger.info("VERIFICATION SUMMARY")
    logger.info(f"  Checkpoint A (Syntax): {checkpoint_a.status.value}")
    logger.info(f"  Checkpoint B (Imports): {checkpoint_b.status.value}")
    logger.info(f"  Checkpoint B.5 (Consistency): {checkpoint_b5.status.value}")
    logger.info(f"  Checkpoint C (Collection): {checkpoint_c.status.value}")
    logger.info(f"  Checkpoint D (Execution): {checkpoint_d.status.value}")
    if checkpoint_d.metadata:
        logger.info(f"    Tests: {checkpoint_d.metadata.get('tests_passed', 0)} passed, "
                   f"{checkpoint_d.metadata.get('tests_failed', 0)} failed")
    logger.info(f"  Overall: {'PASSED' if all_passed else 'FAILED'}")
    logger.info("-" * 40)

    # Collect all errors for recovery
    if not all_passed:
        all_errors = {}
        for cp in [checkpoint_a, checkpoint_b, checkpoint_b5, checkpoint_c, checkpoint_d]:
            if cp and cp.errors:
                all_errors.update(cp.errors)
        
        if all_errors:
            logger.warning("Errors found:")
            for filepath, error in all_errors.items():
                # Handle both string and list errors
                error_str = error if isinstance(error, str) else '\n'.join(error) if isinstance(error, list) else str(error)
                logger.warning(f"  {filepath}: {error_str[:200]}")
    
    return state
