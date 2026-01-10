"""Checkpoint D2: Method Contract Validation."""

import ast
import logging
from typing import Dict

from ...models.schemas import CheckpointStatus, CheckpointResult
from ...tools.method_extractor import (
    extract_method_calls,
    extract_methods_from_files
)

logger = logging.getLogger(__name__)


def checkpoint_d2_method_contracts(generated_files: Dict[str, str]) -> CheckpointResult:
    """
    Checkpoint D2: Validate method contracts between tests and page objects.
    
    Validates:
    - All method calls in tests have matching definitions in page objects
    - Method names match exactly
    - No typos in method names
    
    Args:
        generated_files: Dict of filepath -> code content
        
    Returns:
        CheckpointResult with method contract validation results
    """
    logger.info("Running Checkpoint D2: Method Contract Validation...")
    
    files_checked = []
    files_passed = []
    files_failed = []
    errors = {}
    
    # Extract methods from page objects
    page_methods = extract_methods_from_files(generated_files)
    
    # Build page import mapping (import_name -> page_file)
    page_imports = {}
    for filepath, code in generated_files.items():
        if filepath.startswith("pages/") and filepath.endswith(".py"):
            # Extract class name from file
            class_name = None
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        break
            except:
                continue
            
            if class_name:
                # Map class name to file
                page_imports[class_name] = filepath
    
    # Check test files
    test_files = [f for f in generated_files.keys() if f.startswith("tests/") and f.endswith(".py")]
    
    for test_file in test_files:
        files_checked.append(test_file)
        test_code = generated_files[test_file]
        
        # Extract method calls from test
        calls = extract_method_calls(test_code)
        
        missing_methods = []
        for call in calls:
            class_name = call.get("class_name")
            method_name = call.get("method_name")
            
            if not class_name or not method_name:
                continue
            
            # Find page file for this class
            page_file = None
            for cls, file_path in page_imports.items():
                if class_name and class_name.lower() == cls.lower():
                    page_file = file_path
                    break
            
            if page_file and page_file in page_methods:
                # Check if method exists
                found = False
                available_methods = []
                
                for cls_name, methods in page_methods[page_file].items():
                    if class_name and class_name.lower() == cls_name.lower():
                        if method_name in methods:
                            found = True
                        else:
                            available_methods = methods
                        break
                
                if not found:
                    # Suggest similar methods
                    suggestions = []
                    if available_methods:
                        # Find similar method names
                        for avail_method in available_methods:
                            if method_name.lower() in avail_method.lower() or avail_method.lower() in method_name.lower():
                                suggestions.append(avail_method)
                    
                    error_msg = f"{class_name}.{method_name}() called but doesn't exist"
                    if suggestions:
                        error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"
                    if available_methods:
                        error_msg += f"\nAvailable methods: {', '.join(available_methods[:10])}"
                    
                    missing_methods.append({
                        "class": class_name,
                        "method": method_name,
                        "line": call.get("line"),
                        "error": error_msg
                    })
        
        if missing_methods:
            files_failed.append(test_file)
            error_messages = []
            for mm in missing_methods:
                error_messages.append(f"Line {mm['line']}: {mm['error']}")
            errors[test_file] = "\n".join(error_messages)
            logger.warning(f"  ✗ {test_file}: {len(missing_methods)} missing method(s)")
        else:
            files_passed.append(test_file)
            logger.debug(f"  ✓ {test_file}")
    
    status = CheckpointStatus.PASSED if not files_failed else CheckpointStatus.FAILED
    
    return CheckpointResult(
        checkpoint_name="D2",
        checkpoint_description="Method Contract Validation",
        status=status,
        files_checked=files_checked,
        files_passed=files_passed,
        files_failed=files_failed,
        errors=errors
    )
