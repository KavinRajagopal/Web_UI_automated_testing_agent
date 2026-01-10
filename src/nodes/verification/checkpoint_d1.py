"""Checkpoint D1: Page Object Structure Validation."""

import logging
from typing import Dict

from ...models.schemas import CheckpointStatus, CheckpointResult
from ...tools.method_extractor import extract_page_object_structure

logger = logging.getLogger(__name__)


def checkpoint_d1_page_object_structure(generated_files: Dict[str, str]) -> CheckpointResult:
    """
    Checkpoint D1: Validate page object structure.
    
    Validates:
    - Page objects inherit from BasePage
    - Required methods exist (is_page_loaded, etc.)
    - Locators are defined
    - No structural issues
    
    Args:
        generated_files: Dict of filepath -> code content
        
    Returns:
        CheckpointResult with structure validation results
    """
    logger.info("Running Checkpoint D1: Page Object Structure Validation...")
    
    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}
    
    page_files = [
        f for f in generated_files.keys()
        if f.startswith("pages/") and f.endswith(".py") 
        and "base_page" not in f 
        and "__init__" not in f  # Exclude __init__.py files
    ]
    
    for filepath in page_files:
        files_checked.append(filepath)
        code = generated_files[filepath]
        
        structure = extract_page_object_structure(code)
        
        if not structure.get("valid", False):
            files_failed.append(filepath)
            errors[filepath] = structure.get("error", "Invalid structure")
            logger.warning(f"  ✗ {filepath}: {errors[filepath]}")
            continue
        
        # Check inheritance
        if not structure.get("inherits_base", False):
            files_failed.append(filepath)
            errors[filepath] = "Page object does not inherit from BasePage"
            logger.warning(f"  ✗ {filepath}: Does not inherit from BasePage")
            continue
        
        # Check required methods
        missing_methods = []
        for method, exists in structure.get("required_methods", {}).items():
            if not exists:
                missing_methods.append(method)
        
        if missing_methods:
            files_failed.append(filepath)
            errors[filepath] = f"Missing required methods: {', '.join(missing_methods)}"
            logger.warning(f"  ✗ {filepath}: Missing methods: {', '.join(missing_methods)}")
            continue
        
        files_passed.append(filepath)
        logger.debug(f"  ✓ {filepath}")
    
    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    
    return CheckpointResult(
        checkpoint_name="D1",
        checkpoint_description="Page Object Structure Validation",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )
