"""Recovery Node - Fixes errors in generated code using LLM.

This node:
1. Analyzes verification errors
2. Uses LLM to generate fixes
3. Applies fixes and re-verifies
4. Tracks retry attempts (max 3)
5. Escalates to human if retries exhausted
"""

import logging
import re
from typing import Dict, List, Any, Tuple

from ..models.state import AgentState
from ..models.schemas import CheckpointStatus
from ..llm.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


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
    
    # Check each checkpoint for errors (prioritize checkpoint_d - runtime errors)
    # Check checkpoint_d first since it has the most actionable errors
    checkpoint_priority = ["checkpoint_d", "checkpoint_a", "checkpoint_b", "checkpoint_c"]
    
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
            
            # Map test file errors to source files if needed
            actual_filepath = filepath
            if filepath not in generated_files:
                # Try to find the actual source file
                # Checkpoint D might reference test files, but errors are in page files
                
                # Check for AttributeError patterns that indicate page object issues
                # Pattern: "'LoginPage' object has no attribute 'wait_for_element_visible'"
                page_class_match = re.search(r"'(\w+Page)' object has no attribute", error_msg)
                if page_class_match:
                    page_class = page_class_match.group(1)
                    # Map to page file: LoginPage -> pages/login_page.py
                    page_file = f"pages/{page_class.lower()}_page.py"
                    if page_file in generated_files:
                        actual_filepath = page_file
                        logger.info(f"Mapped AttributeError to page object: {page_file}")
                    else:
                        # Try alternative naming
                        page_file = f"pages/{page_class.lower()}.py"
                        if page_file in generated_files:
                            actual_filepath = page_file
                            logger.info(f"Mapped AttributeError to page object: {page_file}")
                
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
            
            if actual_filepath in generated_files:
                errors_to_fix.append({
                    "filepath": actual_filepath,
                    "error_type": f"Checkpoint {checkpoint_name}",
                    "error_message": error_msg,
                    "code": generated_files[actual_filepath],
                    "checkpoint": checkpoint_name
                })
    
    return errors_to_fix


def _fix_file_with_llm(
    filepath: str,
    error_type: str,
    error_message: str,
    code: str,
    llm: BedrockClient,
    checkpoint: str = "Unknown"
) -> Tuple[str, bool]:
    """
    Use LLM to fix a file with an error.
    
    Args:
        filepath: Path to the file
        error_type: Type of error (checkpoint name)
        error_message: Error message
        code: Current code content
        llm: Bedrock client
        checkpoint: Checkpoint name (A, B, C, or D)
        
    Returns:
        Tuple of (fixed_code, success)
    """
    prompt = RECOVERY_PROMPT_TEMPLATE.format(
        filepath=filepath,
        checkpoint=checkpoint,
        error_type=error_type,
        error_message=error_message,
        code=code
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
    
    # Check if recovery is needed
    if state.get("verification_passed", False):
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
    
    if not errors_to_fix:
        logger.info("No specific errors to fix")
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
    
    # Initialize LLM
    llm = BedrockClient(
        model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        region_name=state.get("llm_region", "us-east-2"),
        profile_name=state.get("llm_profile", "bedrock-user"),
        max_tokens=16384
    )
    
    # Track recovery results
    recovered_files = state.get("recovered_files", [])
    unrecoverable_files = state.get("unrecoverable_files", [])
    generated_files = state.get("generated_files", {})
    
    # Attempt to fix each file
    for error in errors_to_fix:
        filepath = error["filepath"]
        
        # Skip if already marked as unrecoverable
        if filepath in unrecoverable_files:
            continue
        
        logger.info(f"Attempting to fix: {filepath}")
        logger.info(f"  Error: {error['error_message'][:100]}")
        
        # Enhance error message for Playwright issues
        error_message = error["error_message"]
        if "playwright" in error_message.lower() or "playwright" in error["code"].lower():
            error_message = f"CRITICAL: This file uses Playwright but the project uses Selenium! {error_message}\n\nYou MUST replace ALL Playwright code with Selenium equivalents."
            logger.warning(f"  Detected Playwright usage - will enforce Selenium replacement")
        
        fixed_code, success = _fix_file_with_llm(
            filepath=filepath,
            error_type=error["error_type"],
            error_message=error_message,
            code=error["code"],
            llm=llm,
            checkpoint=error.get("checkpoint", "Unknown")
        )
        
        if success:
            generated_files[filepath] = fixed_code
            if filepath not in recovered_files:
                recovered_files.append(filepath)
            logger.info(f"  ✓ Fixed successfully")
        else:
            if filepath not in unrecoverable_files:
                unrecoverable_files.append(filepath)
            logger.warning(f"  ✗ Could not fix")
    
    # Update state
    state["generated_files"] = generated_files
    state["recovered_files"] = recovered_files
    state["unrecoverable_files"] = unrecoverable_files
    
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
    logger.info("-" * 40)
    
    # Check if human intervention needed
    if unrecoverable_files and current_attempts + 1 >= max_attempts:
        state["needs_human_intervention"] = True
        logger.warning("Human intervention required for unrecoverable files")
    
    return state


def should_retry_verification(state: AgentState) -> bool:
    """
    Check if verification should be retried via recovery.
    
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
    
    # Don't retry if max attempts reached
    recovery_attempts = state.get("recovery_attempts", 0)
    max_attempts = state.get("max_recovery_attempts", 3)
    if recovery_attempts >= max_attempts:
        logger.debug(f"should_retry: False - max attempts reached ({recovery_attempts}/{max_attempts})")
        return False
    
    # Don't retry if human intervention flagged
    if state.get("needs_human_intervention", False):
        logger.debug("should_retry: False - human intervention needed")
        return False
    
    # Check if there are errors that CAN be fixed
    # Prioritize checkpoint_d (runtime errors) as they're most actionable
    results = state.get("verification_results", {})
    has_errors = False
    
    # Check all checkpoints, prioritizing checkpoint_d
    for checkpoint_key in ["checkpoint_d", "checkpoint_a", "checkpoint_b", "checkpoint_c"]:
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
        logger.debug(f"should_retry: True - errors found, attempt {recovery_attempts + 1}/{max_attempts}")
        return True
    
    logger.debug("should_retry: False - no fixable errors found")
    return False
