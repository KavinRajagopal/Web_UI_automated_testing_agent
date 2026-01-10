"""Checkpoint D4: Test Execution Validation."""

import logging
import os
import re
import time
from typing import Dict

from ...models.schemas import CheckpointStatus, CheckpointResult
from ...tools.code_executor import run_pytest
from .utils import extract_error_type

logger = logging.getLogger(__name__)


def checkpoint_d4_execution(
    generated_files: Dict[str, str],
    output_dir: str,
    timeout: int = 120
) -> CheckpointResult:
    """
    Checkpoint D4: Actually run the tests and verify they pass.
    
    This catches runtime errors like:
    - AttributeError (wrong method names) - should be rare if D2 passed
    - AssertionError (test logic failures)
    - Import errors at runtime
    - Selenium/WebDriver issues
    
    Args:
        generated_files: Dict of filepath -> code content
        output_dir: Output directory with test files
        timeout: Max execution time in seconds
        
    Returns:
        CheckpointResult with test execution results
    """
    logger.info("Running Checkpoint D4: Test Execution...")
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
                checkpoint_name="D4",
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
            test_errors = {}  # test_name -> full error details
            current_test = None
            current_file = None
            error_lines = []
            full_traceback = []
            in_traceback = False
            error_type = None
            
            lines = output.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Detect test name and file (multiple formats)
                if ('::test_' in line or '::Test' in line) and ('FAILED' in line or 'ERROR' in line):
                    # Save previous test error if exists
                    if current_test and error_lines:
                        test_key = f"{current_file}::{current_test}"
                        test_errors[test_key] = {
                            "file": current_file,
                            "test": current_test,
                            "error_type": error_type,
                            "error_lines": error_lines.copy(),
                            "full_traceback": full_traceback.copy()
                        }
                    
                    # Extract file and test name
                    test_match = re.search(r'([^/\s]+\.py)::([^\s]+)', line)
                    if test_match:
                        current_file = test_match.group(1)
                        current_test = test_match.group(2)
                        error_lines = []
                        full_traceback = []
                        in_traceback = False
                        error_type = None
                        logger.debug(f"Found failed test: {current_file}::{current_test}")
                
                # Detect error type (look for "E   " lines)
                if line.startswith('E   ') and not in_traceback:
                    extracted_type = extract_error_type(line)
                    if extracted_type:
                        error_type = extracted_type
                        in_traceback = True
                        error_lines.append(line.strip())
                        full_traceback.append(line)
                        logger.debug(f"Found error type: {error_type}")
                
                # Collect traceback
                if in_traceback:
                    full_traceback.append(line)
                    if line.startswith('E   ') or (line.startswith(' ') and len(line.strip()) > 0 and not line.strip().startswith('=')):
                        error_lines.append(line.strip())
                    elif line.strip() and not line.startswith('=') and not line.startswith('-') and 'FAILED' not in line:
                        # End of traceback - save the error
                        if current_file and error_lines:
                            error_msg = '\n'.join(error_lines[:100])
                            full_error_msg = '\n'.join(full_traceback[:150])
                            
                            # Map to actual source file (test file or page file)
                            source_file = current_file
                            referenced_files = []
                            
                            for error_line in full_traceback:
                                # Check if error references a page file
                                page_match = re.search(r'File "([^"]+(?:pages|flows)/[^"]+\.py)"', error_line)
                                if page_match:
                                    full_path = page_match.group(1)
                                    if output_dir in full_path:
                                        rel_path = full_path.replace(output_dir + '/', '')
                                    else:
                                        path_parts = full_path.split('/')
                                        if 'pages' in path_parts or 'flows' in path_parts:
                                            idx = max(path_parts.index('pages') if 'pages' in path_parts else -1,
                                                    path_parts.index('flows') if 'flows' in path_parts else -1)
                                            if idx >= 0:
                                                rel_path = '/'.join(path_parts[idx:])
                                            else:
                                                rel_path = None
                                        else:
                                            rel_path = None
                                    
                                    if rel_path and rel_path not in referenced_files:
                                        referenced_files.append(rel_path)
                                    
                                    if source_file.startswith("tests/") and rel_path:
                                        source_file = rel_path
                                        logger.debug(f"Mapped error to source file: {source_file}")
                                        break
                            
                            if source_file not in errors:
                                errors[source_file] = []
                            
                            error_summary = f"{current_test}: {error_type or 'Error'}"
                            enhanced_error = f"{error_summary}\n{full_error_msg}"
                            if referenced_files:
                                enhanced_error += f"\n\nReferenced files: {', '.join(referenced_files)}"
                            
                            errors[source_file].append(enhanced_error)
                            logger.debug(f"Added error for {source_file}: {error_summary[:50]}")
                        
                        in_traceback = False
                        error_lines = []
                        full_traceback = []
                
                i += 1
            
            # Handle any remaining error in traceback
            if in_traceback and current_file and error_lines:
                error_msg = '\n'.join(error_lines[:100])
                full_error_msg = '\n'.join(full_traceback[:150])
                source_file = current_file
                referenced_files = []
                
                for error_line in full_traceback:
                    page_match = re.search(r'File "([^"]+(?:pages|flows)/[^"]+\.py)"', error_line)
                    if page_match:
                        full_path = page_match.group(1)
                        if output_dir in full_path:
                            rel_path = full_path.replace(output_dir + '/', '')
                        else:
                            path_parts = full_path.split('/')
                            if 'pages' in path_parts or 'flows' in path_parts:
                                idx = max(path_parts.index('pages') if 'pages' in path_parts else -1,
                                        path_parts.index('flows') if 'flows' in path_parts else -1)
                                if idx >= 0:
                                    rel_path = '/'.join(path_parts[idx:])
                                else:
                                    rel_path = None
                            else:
                                rel_path = None
                        
                        if rel_path and rel_path not in referenced_files:
                            referenced_files.append(rel_path)
                        
                        if source_file.startswith("tests/") and rel_path:
                            source_file = rel_path
                            break
                
                if source_file not in errors:
                    errors[source_file] = []
                error_summary = f"{current_test or 'Unknown'}: {error_type or 'Error'}"
                enhanced_error = f"{error_summary}\n{full_error_msg}"
                if referenced_files:
                    enhanced_error += f"\n\nReferenced files: {', '.join(referenced_files)}"
                errors[source_file].append(enhanced_error)
            
            # Save final test error if exists
            if current_test and error_lines:
                test_key = f"{current_file}::{current_test}"
                test_errors[test_key] = {
                    "file": current_file,
                    "test": current_test,
                    "error_type": error_type,
                    "error_lines": error_lines.copy(),
                    "full_traceback": full_traceback.copy()
                }
            
            # Also extract all FAILED test names from output (in case parsing missed some)
            failed_test_pattern = re.compile(r'([^/\s]+\.py)::(test_\w+)\s+FAILED')
            for match in failed_test_pattern.finditer(output):
                test_file = match.group(1)
                test_name = match.group(2)
                test_key = f"{test_file}::{test_name}"
                if test_key not in test_errors:
                    # Add as failed test even if we didn't capture full error details
                    test_errors[test_key] = {
                        "file": test_file,
                        "test": test_name,
                        "error_type": "Unknown",
                        "error_lines": ["Test failed but error details not captured"],
                        "full_traceback": []
                    }
            
            # Convert error lists to strings and deduplicate
            for filepath, error_list in errors.items():
                if isinstance(error_list, list):
                    unique_errors = []
                    seen = set()
                    for err in error_list:
                        err_key = err[:200]
                        if err_key not in seen:
                            seen.add(err_key)
                            unique_errors.append(err)
                    errors[filepath] = '\n\n---\n\n'.join(unique_errors)
            
            # If we couldn't parse, use raw output
            if not errors:
                logger.warning("Could not parse pytest errors, using raw output")
                errors["test_execution"] = output[:2000]
            else:
                logger.info(f"Parsed {len(errors)} files with errors: {list(errors.keys())}")
            
            files_failed = list(errors.keys())
            files_passed = [f for f in files_checked if f not in files_failed]
            
            if errors or result.get("failed", 0) > 0 or result.get("errors", 0) > 0:
                status = CheckpointStatus.FAILED
                logger.warning(f"  ✗ Checkpoint D4 FAILED: {result.get('failed', 0)} tests failed, {result.get('passed', 0)} passed")
            else:
                status = CheckpointStatus.PASSED
                logger.info(f"  ✓ Checkpoint D4 PASSED: {result.get('passed', 0)} tests passed")
            
            return CheckpointResult(
                checkpoint_name="D4",
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
                    "tests_errors": result.get("errors", 0),
                    "test_error_details": test_errors
                }
            )
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  Checkpoint D4 error: {e}")
        errors["test_execution"] = str(e)
        files_failed = files_checked
        
        return CheckpointResult(
            checkpoint_name="D4",
            checkpoint_description="Test Execution",
            status=CheckpointStatus.FAILED,
            files_checked=files_checked,
            files_passed=[],
            files_failed=files_failed,
            errors=errors,
            duration_seconds=duration
        )
