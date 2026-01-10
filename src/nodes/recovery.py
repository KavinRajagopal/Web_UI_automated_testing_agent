"""Recovery Node - Fixes errors in generated code using LLM.

This node:
1. Analyzes verification errors
2. Uses LLM to generate fixes
3. Applies fixes and re-verifies
4. Tracks retry attempts (max 3)
5. Escalates to human if retries exhausted
"""

import logging
import os
import re
import hashlib
from typing import Dict, List, Any, Tuple, Set

from ..models.state import AgentState
from ..models.schemas import CheckpointStatus
from ..llm.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


def _hash_error(error_message: str) -> str:
    """Create a hash of an error message for tracking."""
    # Use first 500 chars to create a stable hash
    error_key = error_message[:500].strip()
    return hashlib.md5(error_key.encode()).hexdigest()[:16]


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.
    
    Args:
        name: CamelCase string (e.g., "ProductsPage")
        
    Returns:
        snake_case string (e.g., "products_page")
        
    Examples:
        ProductsPage -> products_page
        LoginPage -> login_page
        CartPage -> cart_page
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _detect_circular_dependencies(
    current_file: str,
    error_history: Dict[str, List[Dict[str, Any]]],
    max_same_error: int = 2
) -> bool:
    """
    Detect if we're stuck in a loop trying to fix the same error.
    Returns True if we should skip this file.
    """
    if current_file not in error_history:
        return False
    
    file_errors = error_history[current_file]
    if len(file_errors) < max_same_error:
        return False
    
    # Check if we've seen the same error hash multiple times
    recent_hashes = [e["error_hash"] for e in file_errors[-max_same_error:]]
    
    # If all recent errors have the same hash, we're stuck
    if len(set(recent_hashes)) == 1:
        logger.warning(f"Circular dependency detected for {current_file}: same error after {max_same_error} attempts")
        return True
    
    return False


class ErrorCategory:
    """Error categories for targeted recovery strategies."""
    MISSING_METHOD = "missing_method"
    WRONG_METHOD_NAME = "wrong_method_name"
    WRONG_PARAMETERS = "wrong_parameters"
    MISSING_IMPORT = "missing_import"
    PAGE_OBJECT_STRUCTURE = "page_object_structure"
    SELECTOR_ISSUE = "selector_issue"
    ASSERTION_ERROR = "assertion_error"
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    UNKNOWN = "unknown"


def categorize_error(error_message: str, error_type: str, checkpoint: str) -> str:
    """
    Categorize error for targeted recovery.
    
    Args:
        error_message: Error message text
        error_type: Error type (e.g., "AttributeError", "Checkpoint D2")
        checkpoint: Checkpoint name
        
    Returns:
        Error category string
    """
    error_lower = error_message.lower()
    
    # Checkpoint-specific categorization
    if checkpoint == "D1":
        return ErrorCategory.PAGE_OBJECT_STRUCTURE
    
    if checkpoint == "D2":
        if "has no attribute" in error_lower or "doesn't exist" in error_lower:
            return ErrorCategory.MISSING_METHOD
        if "called but" in error_lower or "wrong method" in error_lower:
            return ErrorCategory.WRONG_METHOD_NAME
    
    if checkpoint == "D3":
        return ErrorCategory.WRONG_PARAMETERS
    
    # Error type-based categorization
    if "AttributeError" in error_type or "has no attribute" in error_lower:
        if "object has no attribute" in error_lower:
            return ErrorCategory.MISSING_METHOD
        return ErrorCategory.WRONG_METHOD_NAME
    
    if "AssertionError" in error_type or "assert" in error_lower:
        if "failed to load" in error_lower or "page" in error_lower:
            return ErrorCategory.SELECTOR_ISSUE
        return ErrorCategory.ASSERTION_ERROR
    
    if "ImportError" in error_type or "cannot import" in error_lower:
        return ErrorCategory.MISSING_IMPORT
    
    if "SyntaxError" in error_type or "syntax" in error_lower:
        return ErrorCategory.SYNTAX_ERROR
    
    if "selector" in error_lower or "element not found" in error_lower:
        return ErrorCategory.SELECTOR_ISSUE
    
    return ErrorCategory.UNKNOWN


def _validate_fix(code: str, filepath: str) -> bool:
    """
    Validate that a fix doesn't reintroduce known issues.
    Returns True if the fix is valid, False otherwise.
    """
    # Check for Playwright usage (should use Selenium)
    if "from playwright" in code.lower() or "import playwright" in code.lower():
        logger.warning(f"Validation failed for {filepath}: Still uses Playwright")
        return False
    
    # Check for wait_for_* methods in page objects (should use find_* from BasePage)
    if filepath.startswith("pages/") and filepath != "pages/base_page.py":
        if "wait_for_element" in code or "wait_for_selector" in code:
            logger.warning(f"Validation failed for {filepath}: Still uses wait_for_* methods")
            return False
    
    # Check for expect() from Playwright
    if "expect(" in code and filepath.startswith("tests/"):
        # Make sure it's not from pytest or a custom expect
        if "from playwright" in code or "playwright.sync_api" in code:
            logger.warning(f"Validation failed for {filepath}: Still uses Playwright expect")
            return False
    
    # Basic syntax check - must have valid Python structure
    if not code.strip():
        logger.warning(f"Validation failed for {filepath}: Empty code")
        return False
    
    # Must have class or function definition for actual code files
    if filepath.endswith(".py") and not filepath.endswith("__init__.py"):
        if "def " not in code and "class " not in code:
            logger.warning(f"Validation failed for {filepath}: No functions or classes defined")
            return False
    
    logger.debug(f"Validation passed for {filepath}")
    return True


RECOVERY_SYSTEM_PROMPT = """You are an expert Python developer debugging test automation code.
Your task is to fix errors in generated code.

RULES:
1. Fix ONLY the specific error mentioned
2. Preserve the overall structure and logic
3. Return the COMPLETE fixed file content
4. Do not add unnecessary changes
5. Ensure the fix is syntactically correct
6. Return ONLY the Python code, no explanations"""


RECOVERY_PROMPT_TEMPLATE = """Fix the following Python file that has an error:

FILE: {filepath}
CHECKPOINT: {checkpoint}
ERROR TYPE: {error_type}
ERROR MESSAGE: {error_message}

ORIGINAL CODE:
```python
{code}
```

{test_context}

{related_context}

CRITICAL FOR ASSERTION ERRORS:
- If you see "AssertionError: Login page failed to load" or similar:
  1. Check if page navigation is working (driver.get() called correctly)
  2. Verify page load verification methods (is_page_loaded, is_on_page) are implemented correctly
  3. Ensure selectors match the actual page elements
  4. Add proper waits if elements load slowly
  5. Check if BasePage methods are being called correctly (find_* not wait_for_*)
- Review the test code in the error message to understand what it expects
- Review related page objects to see what methods are available
- Ensure page object methods return correct values/types for assertions

BASE PAGE CLASS (for reference - these are the available methods):
```python
class BasePage:
    def find_element(self, by: By, value: str) -> WebElement
    def find_element_clickable(self, by: By, value: str) -> WebElement
    def find_element_visible(self, by: By, value: str) -> WebElement
    def get_element_text(self, by: By, value: str) -> str
    def is_element_present(self, by: By, value: str, timeout: int = 5) -> bool
    def enter_text(self, by: By, value: str, text: str)
    def click(self, by: By, value: str)
```

CRITICAL: This project uses SELENIUM, NOT Playwright!
- Replace ALL Playwright imports with Selenium imports
- Replace `from playwright.sync_api import Page, expect` with `from selenium.webdriver.remote.webdriver import WebDriver`
- Replace `page.locator()` with Selenium WebDriver methods
- Replace `page.goto()` with `driver.get()`
- Replace `expect()` assertions with Selenium assertions

CRITICAL: Method Name Fixes Required!
- Replace `wait_for_element_visible()` with `find_element_visible()`
- Replace `wait_for_element_clickable()` with `find_element_clickable()`
- Replace `wait_for_element()` with `find_element()`
- Replace `wait_for_elements()` with `find_elements()` (if it exists) or use `find_element()` in a loop
- The BasePage class does NOT have `wait_for_*` methods - only `find_*` methods!

CONTEXT:
- If Checkpoint A (Syntax) failed: The code has basic Python syntax errors.
- If Checkpoint B (Imports) failed: There are unresolvable import statements. **CRITICAL: Replace Playwright with Selenium imports!**
- If Checkpoint C (Collection) failed: Pytest could not discover tests, possibly due to syntax or import issues.
- If Checkpoint D (Test Execution) failed: The code has runtime errors (e.g., AttributeError, AssertionError, Selenium exceptions).

Common issues:
- Wrong imports (Playwright instead of Selenium) - REPLACE ALL Playwright code with Selenium
- Wrong method names: `wait_for_element_visible` → `find_element_visible`, `wait_for_element_clickable` → `find_element_clickable`, `wait_for_element` → `find_element`
- Wrong method signatures (e.g., expecting tuple vs separate args: find_element_visible(by, value) not find_element_visible((by, value)))
- Missing method implementations in base class
- Logic errors in assertions
- Incorrect selector usage

IMPORTANT:
- **ALL `wait_for_*` methods must be replaced with `find_*` methods from BasePage**
- Check the base class (BasePage) for available methods - use ONLY the methods listed above
- Match method names exactly
- Use correct method signatures (separate by and value arguments, not tuples)
- Preserve all existing functionality
- **USE SELENIUM, NOT PLAYWRIGHT!**

Provide the COMPLETE fixed code. Return ONLY the Python code, no markdown or explanation."""


def _extract_errors_to_fix(state: AgentState) -> List[Dict[str, Any]]:
    """
    Extract all errors that need fixing from verification results.
    
    Args:
        state: Current agent state
        
    Returns:
        List of error dicts with filepath, error_type, error_message
    """
    errors_to_fix = []
    results = state.get("verification_results", {})
    generated_files = state.get("generated_files", {})
    output_dir = state.get("output_path", "")
    processed_files = set()  # Track files we've already added to avoid duplicates
    
    # Check each checkpoint for errors (prioritize D checkpoints - most actionable)
    # Check D checkpoints first (D4 > D2 > D1 > D3) since they have the most actionable errors
    checkpoint_priority = ["checkpoint_d4", "checkpoint_d2", "checkpoint_d1", "checkpoint_d3", 
                          "checkpoint_d", "checkpoint_a", "checkpoint_b", "checkpoint_c"]
    
    for checkpoint_key in checkpoint_priority:
        checkpoint = results.get(checkpoint_key, {})
        
        if not checkpoint:
            continue
        
        status = checkpoint.get("status", "")
        if status != "failed":
            continue
        
        checkpoint_name = checkpoint.get("checkpoint_name", checkpoint_key)
        checkpoint_errors = checkpoint.get("errors", {})
        
        for filepath, error_msg in checkpoint_errors.items():
            # Handle both string and list error messages
            if isinstance(error_msg, list):
                error_msg = '\n\n'.join(error_msg)
            
            # Special handling for "collection" key from Checkpoint C
            if filepath == "collection":
                # Try to extract file names from the error message
                file_matches = re.findall(r'([^/\s]+\.py)', error_msg)
                if file_matches:
                    # Try to map to actual files
                    for filename in set(file_matches):
                        # Try different mappings
                        potential_paths = []
                        if filename.startswith('test_'):
                            potential_paths.append(f"tests/{filename}")
                        if 'page' in filename.lower():
                            potential_paths.append(f"pages/{filename}")
                            # Also try with _page suffix
                            if not filename.endswith('_page.py'):
                                potential_paths.append(f"pages/{filename.replace('.py', '_page.py')}")
                        if 'flow' in filename.lower():
                            potential_paths.append(f"flows/{filename}")
                        
                        # Also try direct match in generated_files
                        for gen_file in generated_files.keys():
                            if filename in gen_file or gen_file.endswith(filename):
                                potential_paths.append(gen_file)
                        
                        # Use first match that exists
                        for potential_path in potential_paths:
                            if potential_path in generated_files:
                                # Create error entry for this file
                                errors_to_fix.append({
                                    "filepath": potential_path,
                                    "error_type": f"Checkpoint {checkpoint_name}",
                                    "error_message": f"Pytest collection failed: {error_msg[:500]}",
                                    "code": generated_files[potential_path],
                                    "checkpoint": checkpoint_name
                                })
                                logger.info(f"Mapped collection error to {potential_path}")
                                break
                
                # If we couldn't map, try test files as fallback
                if not any(e.get("filepath", "").startswith("tests/") for e in errors_to_fix):
                    test_files = [f for f in generated_files.keys() if f.startswith("tests/")]
                    if test_files:
                        errors_to_fix.append({
                            "filepath": test_files[0],
                            "error_type": f"Checkpoint {checkpoint_name}",
                            "error_message": f"Pytest collection failed: {error_msg[:500]}",
                            "code": generated_files[test_files[0]],
                            "checkpoint": checkpoint_name
                        })
                        logger.info(f"Mapped collection error to test file: {test_files[0]}")
                
                continue  # Skip the normal processing for "collection" key
            
            # Map test file errors to source files if needed
            actual_filepath = filepath
            related_files = []  # Track related files (test -> page objects)
            page_object_detected = False  # Flag to track if we've identified a page object issue
            
            logger.debug(f"Processing error for filepath: {filepath}, checkpoint: {checkpoint_key}")
            logger.debug(f"Error message preview: {error_msg[:200]}")
            
            # Check for AssertionError patterns that indicate page object method failures
            # Pattern: "Login page failed to load" with is_page_loaded() call
            # Pattern: "<pages.login_page.LoginPage object>.is_page_loaded"
            # Handle D4 errors - they may be stored under "test_execution" key
            if checkpoint_key in ["checkpoint_d", "checkpoint_d4"]:
                # Check if errors are stored under "test_execution" key (from D4 checkpoint)
                checkpoint_errors = checkpoint.get("errors", {})
                if "test_execution" in checkpoint_errors:
                    test_execution_error = checkpoint_errors["test_execution"]
                    # Try to extract file paths from the error message
                    # Look for file references in traceback
                    file_matches = re.findall(r'File "([^"]+\.py)"', test_execution_error)
                    for file_match in file_matches:
                        # Extract relative path
                        if output_dir in file_match:
                            rel_path = file_match.replace(output_dir + '/', '')
                        else:
                            # Extract just the filename and try to match
                            filename = os.path.basename(file_match)
                            rel_path = None
                            for gen_file in generated_files.keys():
                                if filename in gen_file or gen_file.endswith(filename):
                                    rel_path = gen_file
                                    break
                        
                        if rel_path and rel_path in generated_files:
                            if rel_path not in processed_files:
                                processed_files.add(rel_path)
                                # Extract error details
                                error_type_match = re.search(r'(TypeError|AttributeError|AssertionError|ValueError|KeyError)', test_execution_error)
                                error_type = error_type_match.group(1) if error_type_match else "RuntimeError"
                                
                                errors_to_fix.append({
                                    "filepath": rel_path,
                                    "error_type": f"Checkpoint {checkpoint_name}",
                                    "error_message": test_execution_error[:2000],  # Limit to 2000 chars
                                    "code": generated_files[rel_path],
                                    "checkpoint": checkpoint_name,
                                    "related_files": []
                                })
                                logger.info(f"Mapped test_execution error to: {rel_path}")
                    
                    # If we couldn't map to specific files, try to extract from test names
                    test_matches = re.findall(r'([^/\s]+\.py)::(test_\w+)', test_execution_error)
                    for test_file, test_name in test_matches:
                        test_file_path = f"tests/{test_file}" if not test_file.startswith("tests/") else test_file
                        if test_file_path in generated_files and test_file_path not in processed_files:
                            processed_files.add(test_file_path)
                            errors_to_fix.append({
                                "filepath": test_file_path,
                                "error_type": f"Checkpoint {checkpoint_name}",
                                "error_message": test_execution_error[:2000],
                                "code": generated_files[test_file_path],
                                "checkpoint": checkpoint_name,
                                "related_files": []
                            })
                            logger.info(f"Mapped test_execution error to test file: {test_file_path}")
            
            # Handle both checkpoint_d (backward compat) and checkpoint_d4
            if checkpoint_key in ["checkpoint_d", "checkpoint_d4"]:
                # FIRST: Check for AttributeError patterns (these are critical page object issues)
                # Pattern: "'ProductsPage' object has no attribute 'is_title_displayed'"
                page_class_match = re.search(r"'(\w+Page)' object has no attribute '?(\w+)'?", error_msg)
                if page_class_match:
                    page_class = page_class_match.group(1)
                    missing_attr = page_class_match.group(2)
                    logger.debug(f"Found AttributeError: {page_class}.{missing_attr}")
                    # Map to page file: ProductsPage -> pages/products_page.py (using proper camel to snake conversion)
                    snake_name = _camel_to_snake(page_class)  # ProductsPage -> products_page
                    page_file = f"pages/{snake_name}.py"
                    logger.debug(f"Trying page file: {page_file}")
                    logger.debug(f"Available files: {list(generated_files.keys())[:5]}")
                    if page_file in generated_files:
                        actual_filepath = page_file
                        page_object_detected = True
                        logger.info(f"✓ Mapped AttributeError ({page_class}.{missing_attr}) to page object: {page_file}")
                    else:
                        # Try without camel case conversion (direct lowercase)
                        page_file = f"pages/{page_class.lower()}.py"
                        logger.debug(f"Trying alternative: {page_file}")
                        if page_file in generated_files:
                            actual_filepath = page_file
                            page_object_detected = True
                            logger.info(f"✓ Mapped AttributeError ({page_class}.{missing_attr}) to page object: {page_file}")
                        else:
                            logger.warning(f"✗ Could not map {page_class} to any generated file")
                
                # SECOND: Check if error involves a page object method call
                if not page_object_detected:
                    page_method_match = re.search(r'<pages\.(\w+_page)\.(\w+Page) object.*?>\.(\w+)', error_msg)
                    if page_method_match:
                        module_name = page_method_match.group(1)
                        class_name = page_method_match.group(2)
                        method_name = page_method_match.group(3)
                        page_file = f"pages/{module_name}.py"
                        
                        if page_file in generated_files:
                            # This is a page object method failure - fix the page object, not the test
                            actual_filepath = page_file
                            page_object_detected = True
                            logger.info(f"Mapped page object method failure ({class_name}.{method_name}) to: {page_file}")
                            # Also check for common assertion patterns
                            if "failed to load" in error_msg.lower() or "should be loaded" in error_msg.lower():
                                if method_name in ["is_page_loaded", "is_on_page", "is_login_page_displayed"]:
                                    logger.info(f"Detected page load failure - will fix {page_file}")
                
                # THIRD: Check for patterns like "Login page failed to load" with page object references
                if not page_object_detected:
                    page_name_match = re.search(r'(\w+)\s+page\s+(?:failed|should)', error_msg, re.IGNORECASE)
                    if page_name_match:
                        page_name = page_name_match.group(1).lower()
                        # Try to map to page file
                        potential_page_file = f"pages/{page_name}_page.py"
                        if potential_page_file in generated_files:
                            actual_filepath = potential_page_file
                            page_object_detected = True
                            logger.info(f"Mapped page load assertion error to page object: {potential_page_file}")
            
            if filepath not in generated_files:
                
                # If still not found, try matching by filename
                if actual_filepath not in generated_files:
                    for gen_file in generated_files.keys():
                        if filepath in gen_file or gen_file in filepath:
                            actual_filepath = gen_file
                            break
                    else:
                        # Skip if we can't find the file
                        logger.warning(f"Could not map error in {filepath} to a generated file")
                        continue
            
            # For checkpoint_d1: Page object structure errors - fix page objects
            if checkpoint_key == "checkpoint_d1":
                # These are page object structure issues - fix the page object
                if filepath.startswith("pages/") and filepath in generated_files:
                    category = categorize_error(error_msg, f"Checkpoint {checkpoint_name}", checkpoint_name)
                    errors_to_fix.append({
                        "filepath": filepath,
                        "error_type": f"Checkpoint {checkpoint_name}",
                        "error_message": f"Page object structure issue: {error_msg}",
                        "code": generated_files[filepath],
                        "checkpoint": checkpoint_name,
                        "related_files": [],
                        "category": category  # NEW: Error category for targeted recovery
                    })
                    logger.info(f"Added page object structure error to fix list: {filepath} (category: {category})")
                    continue
            
            # For checkpoint_d2: Method contract errors - add missing methods or fix calls
            if checkpoint_key == "checkpoint_d2":
                # These are method contract issues
                if filepath.startswith("tests/") and filepath in generated_files:
                    # Extract missing methods from error message
                    missing_methods = re.findall(r"(\w+Page)\.(\w+)\(\)", error_msg)
                    if missing_methods:
                        for page_class, method_name in missing_methods:
                            # Find the page object file
                            snake_name = _camel_to_snake(page_class)
                            page_file = f"pages/{snake_name}.py"
                            if page_file in generated_files:
                                # Add method to page object
                                category = categorize_error(error_msg, f"Checkpoint {checkpoint_name}", checkpoint_name)
                                errors_to_fix.append({
                                    "filepath": page_file,
                                    "error_type": f"Checkpoint {checkpoint_name}",
                                    "error_message": f"Missing method {method_name}() in {page_class}. Error: {error_msg}",
                                    "code": generated_files[page_file],
                                    "checkpoint": checkpoint_name,
                                    "related_files": [filepath],
                                    "category": category  # NEW: Error category
                                })
                                logger.info(f"Added missing method {method_name} to fix list for {page_file} (category: {category})")
                    else:
                        # Fallback: fix the test file
                        errors_to_fix.append({
                            "filepath": filepath,
                            "error_type": f"Checkpoint {checkpoint_name}",
                            "error_message": error_msg,
                            "code": generated_files[filepath],
                            "checkpoint": checkpoint_name,
                            "related_files": []
                        })
                    continue
            
            # For checkpoint_d4 (and checkpoint_d for backward compat), enhance with test code context
            if checkpoint_key in ["checkpoint_d", "checkpoint_d4"]:
                logger.debug(f"Checkpoint D processing: page_object_detected={page_object_detected}, actual_filepath={actual_filepath}")
                # If we detected a page object method failure, prioritize fixing the page object
                if page_object_detected and actual_filepath.startswith("pages/") and actual_filepath in generated_files:
                    logger.info(f"→ Page object issue detected, will fix {actual_filepath} instead of test file")
                    # This is a page object issue - add it to fix list with enhanced error message
                    page_code = generated_files[actual_filepath]
                    
                    # Enhance error message with context about what failed
                    if "is_page_loaded" in error_msg or "failed to load" in error_msg.lower():
                        error_msg = (
                            f"CRITICAL: Page object method is_page_loaded() is returning False. "
                            f"This usually means:\n"
                            f"1. Selectors are incorrect (check element IDs/selectors match actual page)\n"
                            f"2. Elements are not found (wrong selector type or value)\n"
                            f"3. Page navigation hasn't completed (need to wait for page load)\n\n"
                            f"Original error: {error_msg}"
                        )
                    elif "has no attribute" in error_msg:
                        # AttributeError - method is missing
                        attr_match = re.search(r"has no attribute '?(\w+)'?", error_msg)
                        missing_method = attr_match.group(1) if attr_match else "unknown"
                        error_msg = (
                            f"CRITICAL: Page object is missing method '{missing_method}'. "
                            f"This usually means:\n"
                            f"1. Method was not generated or was removed\n"
                            f"2. Method name mismatch between test and page object\n"
                            f"3. Method should be added to the page object class\n\n"
                            f"You MUST add the missing method to this page object class.\n\n"
                            f"Original error: {error_msg}"
                        )
                    
                    errors_to_fix.append({
                        "filepath": actual_filepath,
                        "error_type": f"Checkpoint {checkpoint_name}",
                        "error_message": error_msg,
                        "code": page_code,
                        "checkpoint": checkpoint_name,
                        "related_files": []
                    })
                    logger.info(f"✓ Added page object to fix list: {actual_filepath}")
                    continue  # Skip adding test file, we're fixing the page object
                else:
                    logger.debug(f"→ Not a page object issue, will process as test file error")
                
                # Otherwise, if it's a test file, enhance with context
                # Check both with and without "tests/" prefix
                test_file = None
                if actual_filepath.startswith("tests/"):
                    test_file = actual_filepath
                elif filepath.startswith("tests/"):
                    test_file = filepath
                elif filepath.startswith("test_") or actual_filepath.startswith("test_"):
                    # Try to find the test file in generated_files
                    test_name = actual_filepath if actual_filepath.startswith("test_") else filepath
                    potential_test_file = f"tests/{test_name}"
                    if potential_test_file in generated_files:
                        test_file = potential_test_file
                    elif test_name in generated_files:
                        test_file = test_name
                
                if test_file and test_file in generated_files:
                    # Get the test code
                    test_code = generated_files.get(test_file, "")
                    
                    # Extract test function names from error message
                    test_matches = re.findall(r'::(test_\w+)', error_msg)
                    
                    # Get related page objects from test code
                    page_imports = re.findall(r'from pages\.(\w+_page) import (\w+Page)', test_code)
                    for module_name, class_name in page_imports:
                        page_file = f"pages/{module_name}.py"
                        if page_file in generated_files:
                            related_files.append(page_file)
                    
                    # Get flow imports too
                    flow_imports = re.findall(r'from flows\.(\w+_flow) import (\w+Flow)', test_code)
                    for module_name, class_name in flow_imports:
                        flow_file = f"flows/{module_name}.py"
                        if flow_file in generated_files:
                            related_files.append(flow_file)
                    
                    # Add test code context to error message
                    if test_matches:
                        # Extract specific test function code
                        for test_name in test_matches:
                            test_func_match = re.search(
                                rf'def {test_name}\(.*?\):.*?(?=\n\ndef |\n@pytest|$)',
                                test_code,
                                re.DOTALL
                            )
                            if test_func_match:
                                test_func_code = test_func_match.group(0)
                                error_msg += f"\n\n--- TEST CODE THAT FAILED ({test_name}) ---\n{test_func_code}"
                    
                    # Add related page object code (limit to first 2000 chars each)
                    if related_files:
                        error_msg += "\n\n--- RELATED PAGE OBJECTS (for reference) ---"
                        for rel_file in related_files[:3]:  # Limit to 3 files
                            rel_code = generated_files.get(rel_file, "")
                            error_msg += f"\n\n{rel_file}:\n{rel_code[:2000]}"
            
            if actual_filepath in generated_files:
                category = categorize_error(error_msg, f"Checkpoint {checkpoint_name}", checkpoint_name)
                errors_to_fix.append({
                    "filepath": actual_filepath,
                    "error_type": f"Checkpoint {checkpoint_name}",
                    "error_message": error_msg,  # FULL error message, no truncation
                    "code": generated_files[actual_filepath],
                    "checkpoint": checkpoint_name,
                    "related_files": related_files,  # NEW: Track related files
                    "category": category  # NEW: Error category for targeted recovery
                })
    
    # Deduplicate errors
    seen_errors = set()
    unique_errors = []
    for error in errors_to_fix:
        # Use filepath + first 300 chars of error as key
        error_key = (error["filepath"], error["error_message"][:300])
        if error_key not in seen_errors:
            seen_errors.add(error_key)
            unique_errors.append(error)
    
    return unique_errors


def _fix_file_with_llm(
    filepath: str,
    error_type: str,
    error_message: str,
    code: str,
    llm: BedrockClient,
    checkpoint: str = "Unknown",
    related_files: List[str] = None,
    generated_files: Dict[str, str] = None,
    category: str = None
) -> Tuple[str, bool]:
    """
    Fix a file using LLM based on error information.
    
    Args:
        filepath: Path to the file to fix
        error_type: Type of error (e.g., "SyntaxError", "AttributeError")
        error_message: Detailed error message
        code: Current code content
        llm: BedrockClient instance for LLM calls
        checkpoint: Checkpoint name where error occurred
        related_files: List of related file paths for context
        generated_files: Dict of all generated files for context
        category: Error category for targeted fixes
        
    Returns:
        Tuple of (fixed_code, success_flag)
    """
    """
    Use LLM to fix a file with an error.
    Enhanced to include related file context and error category.
    
    Args:
        filepath: Path to the file
        error_type: Type of error (checkpoint name)
        error_message: Error message
        code: Current code content
        llm: Bedrock client
        checkpoint: Checkpoint name (A, B, C, D1, D2, D3, or D4)
        related_files: List of related file paths (e.g., page objects used by test)
        generated_files: Dict of all generated files (for accessing related file code)
        category: Error category for targeted recovery strategy
        
    Returns:
        Tuple of (fixed_code, success)
    """
    # Add related file context to prompt
    related_context = ""
    if related_files and generated_files:
        related_context = "\n\n--- RELATED FILES (for context) ---\n"
        for rel_file in related_files[:2]:  # Limit to 2 files
            rel_code = generated_files.get(rel_file, "")
            related_context += f"\n{rel_file}:\n```python\n{rel_code[:1500]}\n```\n"
    
    # Extract test context if present in error message
    test_context = ""
    if "--- TEST CODE THAT FAILED" in error_message:
        # Test context is already in error_message, just mark it
        test_context = ""
    elif "--- RELATED PAGE OBJECTS" in error_message:
        # Page object context is already in error_message
        test_context = ""
    
    # Add category-specific guidance
    category_guidance = ""
    if category:
        if category == ErrorCategory.MISSING_METHOD:
            category_guidance = "\n\nCATEGORY: MISSING_METHOD\n" \
                              "ACTION REQUIRED: Add the missing method to the page object class.\n" \
                              "- Extract method name from error message\n" \
                              "- Determine method signature from how it's called in tests\n" \
                              "- Implement the method using BasePage methods (find_*, click, enter_text)\n" \
                              "- Ensure method returns appropriate value (bool for checks, str for getters, None for actions)\n"
        elif category == ErrorCategory.WRONG_METHOD_NAME:
            category_guidance = "\n\nCATEGORY: WRONG_METHOD_NAME\n" \
                              "ACTION REQUIRED: Fix method name to match what exists in page object.\n" \
                              "- Check available methods in the page object\n" \
                              "- Update the method call to use the correct name\n" \
                              "- Ensure method signature matches (parameters, return type)\n"
        elif category == ErrorCategory.PAGE_OBJECT_STRUCTURE:
            category_guidance = "\n\nCATEGORY: PAGE_OBJECT_STRUCTURE\n" \
                              "ACTION REQUIRED: Fix page object structure issues.\n" \
                              "- Ensure class inherits from BasePage\n" \
                              "- Add missing required methods (is_page_loaded, etc.)\n" \
                              "- Define locators as class attributes\n" \
                              "- Fix any structural issues\n"
        elif category == ErrorCategory.SELECTOR_ISSUE:
            category_guidance = "\n\nCATEGORY: SELECTOR_ISSUE\n" \
                              "ACTION REQUIRED: Fix selector issues.\n" \
                              "- Verify selector values match actual page elements\n" \
                              "- Check selector types (id, data-testid, name, etc.)\n" \
                              "- Ensure selectors are stable (not dynamic)\n" \
                              "- Add proper waits if elements load slowly\n"
    
    prompt = RECOVERY_PROMPT_TEMPLATE.format(
        filepath=filepath,
        checkpoint=checkpoint,
        error_type=error_type,
        error_message=error_message + related_context + category_guidance,  # Add context and category guidance
        code=code,
        test_context=test_context,
        related_context=""  # Already included in error_message if present
    )
    
    try:
        response = llm.chat(
            user_message=prompt,
            system=RECOVERY_SYSTEM_PROMPT
        )
        
        # Clean up response
        fixed_code = response.strip()
        if fixed_code.startswith("```python"):
            fixed_code = fixed_code[9:]
        elif fixed_code.startswith("```"):
            fixed_code = fixed_code[3:]
        if fixed_code.endswith("```"):
            fixed_code = fixed_code[:-3]
        
        fixed_code = fixed_code.strip()
        
        # Basic validation - ensure it's not empty
        if not fixed_code or len(fixed_code) < 10:
            logger.warning(f"LLM returned empty or too short code for {filepath}")
            return code, False
        
        # Verify the fix actually addressed the issue
        # Check if it's an import error and verify Playwright is removed
        if "import" in error_message.lower() or "playwright" in error_message.lower():
            if "playwright" in fixed_code.lower() and "selenium" not in fixed_code.lower():
                logger.warning(f"Fix still contains Playwright imports - not actually fixed")
                return code, False
        
        # Check if it's a wait_for_* method error and verify they're replaced
        if "wait_for_" in error_message.lower() or "has no attribute" in error_message.lower():
            # Count wait_for_* method calls in fixed code
            wait_for_calls = re.findall(r'wait_for_\w+\(', fixed_code)
            if wait_for_calls:
                logger.warning(f"Fix still contains wait_for_* methods: {wait_for_calls[:3]} - not actually fixed")
                return code, False
        
        # Quick syntax check
        try:
            import ast
            ast.parse(fixed_code)
        except SyntaxError as e:
            logger.warning(f"Fixed code has syntax errors: {e}")
            return code, False
        
        return fixed_code, True
        
    except Exception as e:
        logger.error(f"LLM recovery failed for {filepath}: {e}")
        return code, False


def recovery_node(state: AgentState) -> AgentState:
    """
    Recovery node - attempts to fix errors in generated code.
    Supports stage-specific recovery for incremental verification.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with fixed files
    """
    logger.info("=" * 60)
    logger.info("RECOVERY NODE")
    logger.info("=" * 60)
    
    state["current_node"] = "recovery"
    state["node_history"] = state.get("node_history", []) + ["recovery"]
    
    # Check recovery stage
    recovery_stage = state.get("recovery_stage", None)
    if recovery_stage:
        logger.info(f"Recovering Stage {recovery_stage} errors")
    
    # Check if recovery is needed
    if state.get("verification_passed", False) and not recovery_stage:
        logger.info("No recovery needed - verification passed")
        return state
    
    # Check retry limit
    current_attempts = state.get("recovery_attempts", 0)
    max_attempts = state.get("max_recovery_attempts", 3)
    
    if current_attempts >= max_attempts:
        logger.warning(f"Max recovery attempts ({max_attempts}) reached")
        state["needs_human_intervention"] = True
        return state
    
    # Increment attempt counter
    state["recovery_attempts"] = current_attempts + 1
    logger.info(f"Recovery attempt {state['recovery_attempts']} of {max_attempts}")
    
    # Extract errors to fix
    errors_to_fix = _extract_errors_to_fix(state)
    
    # Filter errors by recovery stage if specified
    recovery_stage = state.get("recovery_stage", None)
    if recovery_stage:
        logger.info(f"Filtering errors for Stage {recovery_stage} recovery")
        if recovery_stage == 1:
            # Only fix page object errors
            errors_to_fix = [e for e in errors_to_fix if e["filepath"].startswith("pages/")]
            logger.info(f"  Filtered to {len(errors_to_fix)} page object errors")
        elif recovery_stage == 2:
            # Only fix flow errors
            errors_to_fix = [e for e in errors_to_fix if e["filepath"].startswith("flows/")]
            logger.info(f"  Filtered to {len(errors_to_fix)} flow errors")
        elif recovery_stage == 3:
            # Only fix test errors
            errors_to_fix = [e for e in errors_to_fix if e["filepath"].startswith("tests/")]
            logger.info(f"  Filtered to {len(errors_to_fix)} test errors")
    
    if not errors_to_fix:
        logger.info("No specific errors to fix for this stage")
        # If stage-specific recovery found no errors, mark stage as passed
        if recovery_stage:
            state["needs_recovery"] = False
            state["recovery_stage"] = None
        return state
    
    # If we have AttributeErrors about wait_for_* methods, check all page objects
    generated_files = state.get("generated_files", {})
    wait_for_errors = [e for e in errors_to_fix if "wait_for_" in e.get("error_message", "").lower() or "has no attribute" in e.get("error_message", "").lower()]
    
    if wait_for_errors:
        # Find all page object files that might have the same issue
        for page_file in generated_files.keys():
            if page_file.startswith("pages/") and page_file.endswith(".py") and page_file != "pages/base_page.py":
                # Check if this file uses wait_for_* methods
                if "wait_for_" in generated_files[page_file]:
                    # Check if we're already fixing this file
                    if not any(e["filepath"] == page_file for e in errors_to_fix):
                        # Add it to the list to fix
                        errors_to_fix.append({
                            "filepath": page_file,
                            "error_type": "Checkpoint D",
                            "error_message": f"Uses wait_for_* methods that don't exist in BasePage. Replace with find_* methods.",
                            "code": generated_files[page_file],
                            "checkpoint": "D"
                        })
                        logger.info(f"Added {page_file} to fix list (uses wait_for_* methods)")
    
    logger.info(f"Found {len(errors_to_fix)} files with errors")
    
    # Initialize LLM with higher token limit and reasoning for recovery
    llm = BedrockClient(
        model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        region_name=state.get("llm_region", "us-east-2"),
        profile_name=state.get("llm_profile", "bedrock-user"),
        max_tokens=32768,  # Increased from 16384
        enable_reasoning=True  # Enable reasoning for better fixes
    )
    
    # Track recovery results
    recovered_files = state.get("recovered_files", [])
    unrecoverable_files = state.get("unrecoverable_files", [])
    generated_files = state.get("generated_files", {})
    
    # NEW: Track error history to detect loops
    error_history = state.get("error_history", {})
    if not isinstance(error_history, dict):
        error_history = {}
    
    # Attempt to fix each file
    for error in errors_to_fix:
        filepath = error["filepath"]
        error_message = error["error_message"]
        
        # Skip if already marked as unrecoverable
        if filepath in unrecoverable_files:
            logger.info(f"Skipping {filepath} (marked as unrecoverable)")
            continue
        
        # NEW: Check for circular dependencies (same error repeating)
        if _detect_circular_dependencies(filepath, error_history, max_same_error=2):
            logger.warning(f"Skipping {filepath} - stuck in error loop")
            if filepath not in unrecoverable_files:
                unrecoverable_files.append(filepath)
            continue
        
        logger.info(f"Attempting to fix: {filepath}")
        # Log full error (not truncated) - show first 500 chars
        logger.info(f"  Error: {error_message[:500]}...")
        
        # NEW: Create error hash for tracking
        error_hash = _hash_error(error_message)
        
        # Initialize error history for this file
        if filepath not in error_history:
            error_history[filepath] = []
        
        # Enhance error message for Playwright issues
        enhanced_error_message = error_message
        if "playwright" in error_message.lower() or "playwright" in error["code"].lower():
            enhanced_error_message = f"CRITICAL: This file uses Playwright but the project uses Selenium! {error_message}\n\nYou MUST replace ALL Playwright code with Selenium equivalents."
            logger.warning(f"  Detected Playwright usage - will enforce Selenium replacement")
        
        fixed_code, success = _fix_file_with_llm(
            filepath=filepath,
            error_type=error["error_type"],
            error_message=enhanced_error_message,
            code=error["code"],
            llm=llm,
            checkpoint=error.get("checkpoint", "Unknown"),
            related_files=error.get("related_files", []),
            generated_files=generated_files,
            category=error.get("category")  # NEW: Pass error category for targeted recovery
        )
        
        if success:
            # Validate the fix doesn't reintroduce known issues
            if _validate_fix(fixed_code, filepath):
                generated_files[filepath] = fixed_code
                if filepath not in recovered_files:
                    recovered_files.append(filepath)
                logger.info(f"  ✓ Fixed successfully")
                
                # Record successful fix in history
                error_history[filepath].append({
                    "error_hash": error_hash,
                    "error_type": error["error_type"],
                    "attempt": state["recovery_attempts"],
                    "success": True
                })
            else:
                logger.warning(f"  ✗ Fix validation failed - rejected")
                if filepath not in unrecoverable_files:
                    unrecoverable_files.append(filepath)
                
                # Record failed validation
                error_history[filepath].append({
                    "error_hash": error_hash,
                    "error_type": error["error_type"],
                    "attempt": state["recovery_attempts"],
                    "success": False,
                    "reason": "validation_failed"
                })
        else:
            if filepath not in unrecoverable_files:
                unrecoverable_files.append(filepath)
            logger.warning(f"  ✗ Could not fix")
            
            # Record failure in history
            error_history[filepath].append({
                "error_hash": error_hash,
                "error_type": error["error_type"],
                "attempt": state["recovery_attempts"],
                "success": False,
                "reason": "llm_failed"
            })
    
    # Update state
    state["generated_files"] = generated_files
    state["recovered_files"] = recovered_files
    state["unrecoverable_files"] = unrecoverable_files
    state["error_history"] = error_history  # NEW: Track error history for loop detection
    
    # Update LLM usage
    usage = llm.get_usage_stats()
    state["llm_calls"] = state.get("llm_calls", 0) + usage["call_count"]
    state["llm_input_tokens"] = state.get("llm_input_tokens", 0) + usage["total_input_tokens"]
    state["llm_output_tokens"] = state.get("llm_output_tokens", 0) + usage["total_output_tokens"]
    
    # Log summary
    logger.info("-" * 40)
    logger.info("RECOVERY SUMMARY")
    logger.info(f"  Files attempted: {len(errors_to_fix)}")
    logger.info(f"  Recovered: {len(recovered_files)}")
    logger.info(f"  Unrecoverable: {len(unrecoverable_files)}")
    logger.info(f"  LLM calls: {usage['call_count']}")
    
    # Log error history statistics (NEW)
    if error_history:
        logger.info(f"  Files in error history: {len(error_history)}")
        for filepath, history in error_history.items():
            successes = sum(1 for h in history if h.get("success", False))
            failures = len(history) - successes
            logger.debug(f"    {filepath}: {successes} successes, {failures} failures")
    
    logger.info("-" * 40)
    
    # Store errors for progress tracking (NEW)
    current_errors = {}
    results = state.get("verification_results", {})
    for checkpoint_key in ["checkpoint_a", "checkpoint_b", "checkpoint_c", 
                           "checkpoint_d1", "checkpoint_d2", "checkpoint_d3", "checkpoint_d4", "checkpoint_d"]:
        checkpoint = results.get(checkpoint_key, {})
        if checkpoint and checkpoint.get("status") == "failed":
            current_errors[checkpoint_key] = checkpoint.get("errors", {})
    
    state["previous_verification_errors"] = current_errors
    
    # Check if human intervention needed
    if unrecoverable_files and current_attempts + 1 >= max_attempts:
        state["needs_human_intervention"] = True
        logger.warning("Human intervention required for unrecoverable files")
    
    # Update scratchpad with recovery decision
    scratchpad = state.get("scratchpad")
    if scratchpad:
        recovery_stage = state.get("recovery_stage")
        stage_info = f"Stage {recovery_stage}" if recovery_stage else "Final"
        scratchpad.add_decision(
            f"Recovery attempt {state['recovery_attempts']} completed",
            f"Fixed {len(recovered_files)} files in {stage_info}"
        )
        scratchpad.update_progress(state)
    
    # Clear recovery stage flag if we fixed all errors
    if not errors_to_fix or len(recovered_files) > 0:
        # Keep recovery_stage so we know which verification to run next
        pass
    
    return state


def should_retry_verification(state: AgentState) -> bool:
    """
    Check if verification should be retried via recovery.
    Enhanced to allow more retries if progress is being made.
    
    Called AFTER verification fails to decide: recovery or human gate?
    
    Args:
        state: Current agent state
        
    Returns:
        True if should attempt recovery
    """
    # Don't retry if already passed
    if state.get("verification_passed", False):
        logger.debug("should_retry: False - verification already passed")
        return False
    
    # Check retry limit with progress tracking
    recovery_attempts = state.get("recovery_attempts", 0)
    base_max_attempts = state.get("max_recovery_attempts", 6)
    
    # Check if we're making progress
    previous_errors = state.get("previous_verification_errors", {})
    current_results = state.get("verification_results", {})
    
    # Count current errors
    current_error_count = 0
    previous_error_count = 0
    
    for checkpoint_key in ["checkpoint_a", "checkpoint_b", "checkpoint_c", 
                           "checkpoint_d1", "checkpoint_d2", "checkpoint_d3", "checkpoint_d4", "checkpoint_d"]:
        checkpoint = current_results.get(checkpoint_key, {})
        if checkpoint.get("status") == "failed":
            errors = checkpoint.get("errors", {})
            current_error_count += len(errors)
        
        # Count previous errors
        if checkpoint_key in previous_errors:
            prev_errors = previous_errors[checkpoint_key]
            if isinstance(prev_errors, dict):
                previous_error_count += len(prev_errors)
            else:
                previous_error_count += 1
    
    # Calculate progress
    progress_made = False
    if previous_error_count > 0:
        error_reduction = previous_error_count - current_error_count
        progress_percentage = (error_reduction / previous_error_count) * 100 if previous_error_count > 0 else 0
        progress_made = error_reduction > 0 or progress_percentage > 10  # At least 10% reduction or any reduction
        
        if progress_made:
            logger.info(f"Progress detected: {error_reduction} errors fixed ({progress_percentage:.1f}% reduction)")
    
    # Dynamic retry limit: extend if progress is being made
    effective_max = base_max_attempts
    if progress_made and recovery_attempts < base_max_attempts:
        # Allow up to 2x base limit if making progress
        effective_max = min(base_max_attempts * 2, base_max_attempts + 6)
        logger.info(f"Progress detected - extending retry limit from {base_max_attempts} to {effective_max}")
    
    if recovery_attempts >= effective_max:
        logger.debug(f"should_retry: False - max attempts reached ({recovery_attempts}/{effective_max})")
        return False
    
    # Don't retry if human intervention flagged
    if state.get("needs_human_intervention", False):
        logger.debug("should_retry: False - human intervention needed")
        return False
    
    # Check if there are errors that CAN be fixed
    results = state.get("verification_results", {})
    has_errors = False
    
    # Check all checkpoints, prioritizing D checkpoints
    for checkpoint_key in ["checkpoint_d4", "checkpoint_d2", "checkpoint_d1", "checkpoint_d3",
                           "checkpoint_d", "checkpoint_a", "checkpoint_b", "checkpoint_c"]:
        checkpoint = results.get(checkpoint_key, {})
        if not checkpoint:
            continue
        
        status = checkpoint.get("status", "")
        if status == "failed":
            checkpoint_errors = checkpoint.get("errors", {})
            if checkpoint_errors:
                has_errors = True
                logger.debug(f"should_retry: Found errors in {checkpoint_key}")
                break
    
    if has_errors:
        logger.debug(f"should_retry: True - errors found, attempt {recovery_attempts + 1}/{effective_max}")
        return True
    
    logger.debug("should_retry: False - no errors to fix")
    return False
