"""Code execution tools for the agent.

These tools allow the agent to test generated code
and understand errors before fixing them.
"""

import ast
import re
import subprocess
import sys
import tempfile
import os
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


def validate_syntax(code: str) -> Tuple[bool, str]:
    """
    Validate Python syntax.
    
    Args:
        code: Python code string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def execute_python(code: str, timeout: int = 30) -> Dict[str, str]:
    """
    Execute Python code and return output/errors.
    
    Args:
        code: Python code to execute
        timeout: Max execution time in seconds
        
    Returns:
        Dict with 'stdout', 'stderr', 'returncode', 'success'
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds",
            "returncode": -1,
            "success": False
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "success": False
        }


def run_pytest(
    test_dir: str,
    test_file: Optional[str] = None,
    collect_only: bool = False,
    timeout: int = 60
) -> Dict[str, any]:
    """
    Run pytest on generated tests.
    
    Args:
        test_dir: Directory containing tests
        test_file: Specific test file (optional)
        collect_only: Just collect tests, don't run
        timeout: Max execution time
        
    Returns:
        Dict with test results
    """
    cmd = [sys.executable, "-m", "pytest"]
    
    if collect_only:
        cmd.append("--collect-only")
    
    cmd.extend(["-v", "--tb=short"])
    
    if test_file:
        cmd.append(test_file)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Parse results - handle multiple pytest output formats
        output = result.stdout + result.stderr
        passed = failed = errors = 0
        
        # Try to find test summary line (various formats)
        # Format 1: "10 passed, 2 failed in 5.23s"
        # Format 2: "10 passed"
        # Format 3: "FAILED test_file.py::test_name"
        # Format 4: "= 10 passed, 2 failed ="
        
        for line in output.split('\n'):
            line_lower = line.lower().strip()
            
            # Match patterns like "10 passed", "2 failed", "1 error"
            # Match "X passed" or "passed = X" or "X passed in"
            passed_match = re.search(r'(\d+)\s+passed', line_lower)
            if passed_match:
                try:
                    passed = int(passed_match.group(1))
                except:
                    pass
            
            # Match "X failed" or "failed = X"
            failed_match = re.search(r'(\d+)\s+failed', line_lower)
            if failed_match:
                try:
                    failed = int(failed_match.group(1))
                except:
                    pass
            
            # Match "X error" or "errors = X"
            error_match = re.search(r'(\d+)\s+error', line_lower)
            if error_match:
                try:
                    errors = int(error_match.group(1))
                except:
                    pass
        
        # If we couldn't parse but returncode != 0, assume failures
        if result.returncode != 0 and passed == 0 and failed == 0:
            # Try to count FAILED lines
            failed = len([l for l in output.split('\n') if 'FAILED' in l])
            if failed == 0:
                failed = 1  # At least one failure if returncode != 0
        
        return {
            "output": output,
            "returncode": result.returncode,
            "success": result.returncode == 0,
            "passed": passed,
            "failed": failed,
            "errors": errors
        }
        
    except subprocess.TimeoutExpired:
        return {
            "output": f"Pytest timed out after {timeout} seconds",
            "returncode": -1,
            "success": False,
            "passed": 0,
            "failed": 0,
            "errors": 1
        }
    except Exception as e:
        return {
            "output": str(e),
            "returncode": -1,
            "success": False,
            "passed": 0,
            "failed": 0,
            "errors": 1
        }


def lint_file(code: str, filepath: str = "test.py") -> Dict[str, any]:
    """
    Run basic linting on Python code.
    
    Args:
        code: Python code
        filepath: Filename for error messages
        
    Returns:
        Dict with lint results
    """
    issues = []
    
    # Check syntax
    valid, error = validate_syntax(code)
    if not valid:
        issues.append({
            "type": "syntax_error",
            "message": error,
            "severity": "error"
        })
        return {"valid": False, "issues": issues}
    
    # Parse and check common issues
    try:
        tree = ast.parse(code)
        
        # Check for unused imports (basic)
        imports = set()
        names_used = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add(alias.asname or alias.name)
            elif isinstance(node, ast.Name):
                names_used.add(node.id)
        
        # Check for undefined names (very basic)
        builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
        
    except Exception as e:
        issues.append({
            "type": "parse_error",
            "message": str(e),
            "severity": "error"
        })
    
    return {
        "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
        "issues": issues
    }


def test_import(code: str, output_dir: str) -> Dict[str, any]:
    """
    Test if generated code can be imported without errors.
    
    Args:
        code: Python code
        output_dir: Directory to write temp file
        
    Returns:
        Dict with import test results
    """
    # Write to temp file
    temp_file = os.path.join(output_dir, "_import_test.py")
    
    try:
        with open(temp_file, 'w') as f:
            f.write(code)
        
        # Try to import
        result = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, '{output_dir}'); import _import_test"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "success": result.returncode == 0,
            "error": result.stderr if result.returncode != 0 else ""
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)
