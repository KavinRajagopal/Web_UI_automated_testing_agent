"""Checkpoint C: Pytest Collection Validation."""

import logging
import os
import re
import subprocess
import sys
from typing import Dict

from ...models.schemas import CheckpointStatus, CheckpointResult
from .utils import extract_error_type

logger = logging.getLogger(__name__)


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
    
    # Run pytest --collect-only with verbose output for better error details
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-v", "--tb=short"],
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
            # Collection failed - parse errors to map to specific files
            error_output = result.stderr or result.stdout
            full_output = error_output
            
            # Parse pytest collection errors to find specific files
            parsed_errors = {}
            current_file = None
            error_lines = []
            collecting_error = False
            
            lines = full_output.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Pattern 1: "ERROR collecting tests/test_file.py" or "ERROR collecting file.py"
                error_collect_match = re.search(r'ERROR collecting\s+([^\s]+\.py)', line)
                if error_collect_match:
                    file_path = error_collect_match.group(1)
                    # Normalize path (pytest might show relative or absolute)
                    if '/' in file_path:
                        filename = os.path.basename(file_path)
                    else:
                        filename = file_path
                    
                    # Map to our file structure
                    if filename.startswith('test_'):
                        current_file = f"tests/{filename}"
                    elif 'page' in filename.lower():
                        for gen_file in generated_files.keys():
                            if filename in gen_file or gen_file.endswith(filename):
                                current_file = gen_file
                                break
                        if not current_file:
                            current_file = f"pages/{filename}"
                    elif 'flow' in filename.lower():
                        for gen_file in generated_files.keys():
                            if filename in gen_file or gen_file.endswith(filename):
                                current_file = gen_file
                                break
                        if not current_file:
                            current_file = f"flows/{filename}"
                    else:
                        for gen_file in generated_files.keys():
                            if filename in gen_file:
                                current_file = gen_file
                                break
                    
                    collecting_error = True
                    error_lines = [line]
                    i += 1
                    continue
                
                # Pattern 2: "file.py:line: in <module>" or "file.py::test_name"
                if not current_file:
                    file_match = re.search(r'([^/\s]+\.py)(?:::\w+|:\d+)', line)
                    if file_match:
                        filename = file_match.group(1)
                        if filename.startswith('test_'):
                            current_file = f"tests/{filename}"
                        else:
                            for gen_file in generated_files.keys():
                                if filename in gen_file:
                                    current_file = gen_file
                                    break
                        collecting_error = True
                        error_lines = [line]
                        i += 1
                        continue
                
                # Collect error lines
                if collecting_error:
                    error_lines.append(line)
                    
                    # Detect error type
                    if 'Error' in line or 'Exception' in line:
                        error_type = extract_error_type(line)
                        if error_type:
                            if current_file and current_file in generated_files:
                                error_msg = '\n'.join(error_lines[:15])
                                parsed_errors[current_file] = f"{error_type}\n{error_msg}"
                                logger.debug(f"  Mapped collection error to {current_file}: {error_type}")
                            collecting_error = False
                            current_file = None
                            error_lines = []
                    elif (not line.strip() or line.startswith('=') or 
                          line.startswith('-') or 'collected' in line.lower()):
                        if current_file and error_lines and current_file in generated_files:
                            error_msg = '\n'.join(error_lines[:15])
                            parsed_errors[current_file] = error_msg
                        collecting_error = False
                        current_file = None
                        error_lines = []
                
                i += 1
            
            # Handle any remaining error
            if collecting_error and current_file and error_lines and current_file in generated_files:
                error_msg = '\n'.join(error_lines[:15])
                parsed_errors[current_file] = error_msg
            
            # If we parsed specific file errors, use those
            if parsed_errors:
                errors.update(parsed_errors)
                files_failed = list(parsed_errors.keys())
                files_passed = [f for f in files_checked if f not in files_failed]
                logger.warning(f"  Collection failed: {len(parsed_errors)} files with errors: {list(parsed_errors.keys())}")
            else:
                # Fallback: try to extract file names from error output
                file_matches = re.findall(r'([^/\s]+\.py)', full_output)
                if file_matches:
                    potential_files = []
                    for f in set(file_matches):
                        if f.startswith('test_'):
                            potential_files.append(f"tests/{f}")
                        else:
                            for gen_file in generated_files.keys():
                                if f in gen_file or gen_file.endswith(f):
                                    potential_files.append(gen_file)
                                    break
                    
                    files_failed = [f for f in potential_files if f in generated_files]
                    if files_failed:
                        for f in files_failed:
                            errors[f] = f"Pytest collection failed. Error output:\n{full_output[:500]}"
                    else:
                        test_files = [f for f in files_checked if f.endswith('.py') and 'test' in f]
                        files_failed = test_files
                        if test_files:
                            errors[test_files[0]] = f"Pytest collection failed. Error output:\n{full_output[:500]}"
                        else:
                            errors["collection"] = full_output[:1000]
                else:
                    test_files = [f for f in files_checked if f.endswith('.py') and 'test' in f]
                    files_failed = test_files
                    if test_files:
                        errors[test_files[0]] = f"Pytest collection failed. Error output:\n{full_output[:500]}"
                    else:
                        errors["collection"] = full_output[:1000]
                
                files_passed = [f for f in files_checked if f not in files_failed]
                logger.warning(f"  Collection failed: {full_output[:200]}")
            
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
