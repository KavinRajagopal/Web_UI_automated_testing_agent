"""Checkpoint A: Python Syntax Validation."""

import ast
import logging
from typing import Dict, Tuple

from ...models.schemas import CheckpointStatus, CheckpointResult

logger = logging.getLogger(__name__)


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
