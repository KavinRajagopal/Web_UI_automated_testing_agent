"""Recovery Node - Simplified error fixing using LLM.

This node:
1. Extracts errors from verification results
2. Uses LLM to generate fixes
3. Tracks retry attempts (max 3)
4. Detects circular loops to prevent infinite retries
"""

import ast
import logging
import hashlib
import re
from typing import Dict, List, Any

from ..models.state import AgentState
from ..llm.bedrock_client import BedrockClient
from ..utils.event_logger import add_event_to_state
from ..utils.method_registry import get_registry

logger = logging.getLogger(__name__)

# Recovery attempt limits
MAX_RECOVERY_ATTEMPTS = 5  # Default starting budget
ABSOLUTE_MAX_ATTEMPTS = 10  # Hard cap - never exceed this


def _hash_error(error_message: str) -> str:
    """Create a hash of an error message for tracking loops."""
    error_key = error_message[:500].strip()
    return hashlib.md5(error_key.encode()).hexdigest()[:16]


def _detect_loop(
    filepath: str,
    error_hash: str,
    error_history: Dict[str, List[str]],
    max_same_error: int = 2
) -> bool:
    """Detect if we're stuck fixing the same error."""
    if filepath not in error_history:
        return False

    file_errors = error_history[filepath]
    if len(file_errors) < max_same_error:
        return False

    # Check if recent errors have the same hash
    recent = file_errors[-max_same_error:]
    if len(set(recent)) == 1 and recent[0] == error_hash:
        logger.warning(f"Loop detected for {filepath}: same error after {max_same_error} attempts")
        return True

    return False


def _validate_fix(code: str, filepath: str) -> bool:
    """Validate that a fix is syntactically correct and doesn't use Playwright."""
    # Check for empty code
    if not code.strip():
        return False

    # Check for Playwright usage (should use Selenium)
    if "from playwright" in code.lower() or "import playwright" in code.lower():
        logger.warning(f"Fix rejected for {filepath}: Uses Playwright instead of Selenium")
        return False

    # Basic syntax check
    try:
        ast.parse(code)
    except SyntaxError as e:
        logger.warning(f"Fix rejected for {filepath}: Syntax error - {e}")
        return False

    return True


RECOVERY_PROMPT = """You are an expert Python developer fixing test automation code.

FILE: {filepath}
ERROR TYPE: {error_type}
ERROR CATEGORY: {error_category}

ERROR DETAILS:
{error_message}

{smart_fix_hint}

ORIGINAL CODE:
```python
{code}
```

{page_methods_context}

{context}

RULES:
1. Fix ONLY the specific error - don't refactor unrelated code
2. Return the COMPLETE fixed file content
3. Use SELENIUM, not Playwright
4. Use ONLY methods listed in "PAGE OBJECT METHODS" if available
5. Return ONLY Python code, no markdown or explanations

BASE PAGE METHODS (inherited by all pages):
- find_element(by, value) -> WebElement
- find_element_clickable(by, value) -> WebElement
- find_element_visible(by, value) -> WebElement
- get_element_text(by, value) -> str
- is_element_present(by, value, timeout=5) -> bool
- enter_text(by, value, text)
- click(by, value)

COMMON FIXES BY ERROR TYPE:
- AttributeError (missing_attribute): Add the missing locator constant or use correct method name
- NameError (undefined_name): Import the missing module or define the variable
- TypeError (argument_count): Adjust method call arguments to match signature
- AssertionError: Fix test logic or expected values

Return the COMPLETE fixed Python code:"""


def _build_page_methods_context(state: AgentState, error_info: Dict[str, Any]) -> str:
    """Build context string with available page methods from registry."""
    registry = get_registry()
    context_parts = []

    # Get all registered pages
    all_pages = registry.get_all_pages()
    if not all_pages:
        return ""

    context_parts.append("PAGE OBJECT METHODS AVAILABLE:")

    # If we know which class has the error, prioritize it
    error_class = error_info.get("class_name", "")

    for page_name in all_pages:
        page_info = registry.get_page(page_name)
        if page_info:
            methods = page_info.methods[:25]  # Limit to 25 methods
            locators = page_info.locators[:15]  # Include locator constants

            # Mark the error class
            prefix = ">>> " if page_name == error_class or page_info.class_name == error_class else ""
            context_parts.append(f"{prefix}{page_name} ({page_info.class_name}):")

            if locators:
                context_parts.append(f"  Locators: {', '.join(locators)}")
            if methods:
                context_parts.append(f"  Methods: {', '.join(methods)}")

    return "\n".join(context_parts)


def _build_smart_fix_hint(error_info: Dict[str, Any]) -> str:
    """Build a smart fix hint based on parsed error details."""
    error_category = error_info.get("error_category", "")
    fix_suggestion = error_info.get("fix_suggestion", "")

    if not error_category:
        return ""

    hint_parts = ["SMART FIX HINT:"]
    hint_parts.append(f"  Category: {error_category}")

    if error_category == "missing_attribute":
        class_name = error_info.get("class_name", "")
        missing_attr = error_info.get("missing_attribute", "")
        hint_parts.append(f"  Missing: {class_name}.{missing_attr}")
        hint_parts.append(f"  Action: Define '{missing_attr}' as a class constant (locator tuple) or fix the method call")

    elif error_category == "undefined_name":
        undefined = error_info.get("undefined_name", "")
        hint_parts.append(f"  Undefined: {undefined}")
        hint_parts.append(f"  Action: Add import or define variable '{undefined}'")

    elif error_category == "argument_count":
        method = error_info.get("method_name", "")
        expected = error_info.get("expected_args", "")
        actual = error_info.get("actual_args", "")
        hint_parts.append(f"  Method: {method}() expects {expected} args, got {actual}")
        hint_parts.append(f"  Action: Adjust method call to use correct number of arguments")

    if fix_suggestion:
        hint_parts.append(f"  Suggestion: {fix_suggestion}")

    return "\n".join(hint_parts)


def _extract_errors_from_verification(state: AgentState) -> List[Dict[str, Any]]:
    """Extract errors to fix from verification results, including smart-parsed fields."""
    errors_to_fix = []
    generated_files = state.get("generated_files", {})

    # First, use extracted errors from verification (if available)
    # These include smart-parsed fields from verification_node
    verification_errors = state.get("verification_errors", [])
    if verification_errors:
        for err in verification_errors:
            filepath = err.get("file")
            if filepath and filepath in generated_files:
                # Build error info, preserving smart-parsed fields
                error_info = {
                    "filepath": filepath,
                    "error_type": err.get("error_type", "Error"),
                    "error_message": err.get("message", "") + "\n" + "\n".join(err.get("traceback", [])),
                    "code": generated_files[filepath],
                    # Preserve smart-parsed fields from verification
                    "error_category": err.get("error_category", ""),
                    "class_name": err.get("class_name", ""),
                    "missing_attribute": err.get("missing_attribute", ""),
                    "undefined_name": err.get("undefined_name", ""),
                    "fix_suggestion": err.get("fix_suggestion", ""),
                    "traceback": err.get("traceback", []),
                    "test_name": err.get("test_name", ""),
                    "line": err.get("line"),
                }
                errors_to_fix.append(error_info)

    # Fallback: extract from verification_results checkpoint errors
    if not errors_to_fix:
        results = state.get("verification_results", {})
        for checkpoint_key in ["checkpoint_d", "checkpoint_c", "checkpoint_b", "checkpoint_a"]:
            checkpoint = results.get(checkpoint_key, {})
            if checkpoint.get("status") != "failed":
                continue

            checkpoint_errors = checkpoint.get("errors", {})
            for filepath, error_msg in checkpoint_errors.items():
                if filepath in generated_files:
                    if isinstance(error_msg, list):
                        error_msg = "\n".join(error_msg)
                    errors_to_fix.append({
                        "filepath": filepath,
                        "error_type": f"Checkpoint {checkpoint.get('checkpoint_name', checkpoint_key)}",
                        "error_message": error_msg[:2000],
                        "code": generated_files[filepath]
                    })

    return errors_to_fix


def _get_related_context(filepath: str, generated_files: Dict[str, str]) -> str:
    """Get related code context for better fixes."""
    context_parts = []

    # For test files, include relevant page objects
    if filepath.startswith("tests/"):
        for page_file, code in generated_files.items():
            if page_file.startswith("pages/") and page_file != "pages/__init__.py":
                context_parts.append(f"--- {page_file} ---\n{code[:1500]}")

    # For page files, include base_page
    elif filepath.startswith("pages/") and filepath != "pages/base_page.py":
        base_page = generated_files.get("pages/base_page.py", "")
        if base_page:
            context_parts.append(f"--- pages/base_page.py ---\n{base_page[:1500]}")

    if context_parts:
        return "RELATED CODE:\n" + "\n\n".join(context_parts[:3])
    return ""


def _fix_with_llm(
    filepath: str,
    error_info: Dict[str, Any],
    code: str,
    context: str,
    state: AgentState,
    llm: BedrockClient
) -> str:
    """Use LLM to fix code with smart error context."""
    # Extract error details
    error_type = error_info.get("error_type", "Unknown")
    error_category = error_info.get("error_category", "unknown")
    error_message = error_info.get("message", "") + "\n" + "\n".join(error_info.get("traceback", []))

    # Build smart context
    smart_fix_hint = _build_smart_fix_hint(error_info)
    page_methods_context = _build_page_methods_context(state, error_info)

    prompt = RECOVERY_PROMPT.format(
        filepath=filepath,
        error_type=error_type,
        error_category=error_category,
        error_message=error_message[:2000],
        smart_fix_hint=smart_fix_hint,
        page_methods_context=page_methods_context,
        code=code,
        context=context
    )

    logger.debug(f"Recovery prompt length: {len(prompt)} chars")
    response = llm.chat(user_message=prompt)

    # Extract code from response (remove markdown if present)
    fixed_code = response.strip()

    # Remove markdown code blocks if present
    if fixed_code.startswith("```python"):
        fixed_code = fixed_code[9:]
    elif fixed_code.startswith("```"):
        fixed_code = fixed_code[3:]

    if fixed_code.endswith("```"):
        fixed_code = fixed_code[:-3]

    return fixed_code.strip()


def _reinject_locators(filepath: str, code: str, registry: 'MethodRegistry') -> str:
    """
    Re-inject deterministic locators into LLM-fixed code.

    When LLM fixes page object code, it may generate incorrect locators.
    This function replaces them with the correct deterministic locators
    from the cached element metadata in the registry.

    Args:
        filepath: Path to the page file (e.g., "pages/login_page.py")
        code: LLM-fixed code
        registry: Method registry with cached metadata

    Returns:
        Code with correct locators re-injected
    """
    from ..nodes.generation import _generate_locators_code, _inject_locators_into_code

    # Extract page name from filepath (e.g., "pages/login_page.py" -> "LoginPage")
    filename = filepath.split("/")[-1].replace("_page.py", "").replace(".py", "")
    page_name = filename.title().replace("_", "") + "Page"

    # Try to find the page in registry
    page_info = registry.get_page(page_name)

    if not page_info or not page_info.element_metadata:
        logger.debug(f"No cached metadata for {page_name}, skipping locator re-injection")
        return code

    # Generate deterministic locators from cached metadata
    locators_info = _generate_locators_code(page_info.element_metadata)

    # Inject into code
    fixed_code = _inject_locators_into_code(
        code,
        locators_info["constants"],
        page_info.class_name
    )

    logger.info(f"Re-injected locators for {page_name}")
    return fixed_code


def should_retry_verification(state: AgentState) -> bool:
    """Check if recovery should be attempted."""
    if state.get("verification_passed", False):
        return False

    current_attempts = state.get("recovery_attempts", 0)
    max_attempts = state.get("max_recovery_attempts", MAX_RECOVERY_ATTEMPTS)

    if current_attempts >= max_attempts:
        logger.info(f"Max recovery attempts ({max_attempts}) reached")
        return False

    return True


def recovery_node(state: AgentState) -> AgentState:
    """
    Simplified recovery node - fixes errors using LLM.

    Process:
    1. Extract errors from verification results
    2. For each error, use LLM to generate fix
    3. Validate fix (syntax, no Playwright)
    4. Update generated_files with fixed code
    5. Increment recovery_attempts counter

    Routes back to verification for re-testing.

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

    # Log node start
    add_event_to_state(state, "node_start", "recovery")

    current_attempt = state.get("recovery_attempts", 0) + 1
    max_attempts = state.get("max_recovery_attempts", MAX_RECOVERY_ATTEMPTS)

    logger.info(f"Recovery attempt {current_attempt}/{max_attempts}")

    # Check if we should proceed
    if current_attempt > max_attempts:
        logger.warning("Max recovery attempts exceeded - giving up")
        state["needs_human_intervention"] = True
        add_event_to_state(state, "recovery_exhausted", "recovery", {
            "attempts": current_attempt - 1
        })
        return state

    # Initialize LLM
    try:
        llm = BedrockClient(
            model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
            region_name=state.get("llm_region", "us-east-2"),
            profile_name=state.get("llm_profile", "default"),
            max_tokens=16384
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        state["needs_human_intervention"] = True
        add_event_to_state(state, "error", "recovery", {
            "error_type": "llm_init_failed",
            "message": str(e)
        })
        return state

    # Extract errors to fix
    errors_to_fix = _extract_errors_from_verification(state)

    if not errors_to_fix:
        logger.warning("No errors found to fix")
        state["recovery_attempts"] = current_attempt
        return state

    logger.info(f"Found {len(errors_to_fix)} files with errors to fix")

    # Initialize registry for locator re-injection
    registry = get_registry()

    # Dynamic retry budget: extend if making progress
    previous_error_count = state.get("previous_error_count", float('inf'))
    current_error_count = len(errors_to_fix)

    is_making_progress = current_error_count < previous_error_count

    if is_making_progress and current_attempt >= max_attempts - 1:
        new_max = min(max_attempts + 2, ABSOLUTE_MAX_ATTEMPTS)
        if new_max > max_attempts:
            logger.info(f"Progress detected ({previous_error_count} -> {current_error_count} errors). "
                        f"Extending retry budget: {max_attempts} -> {new_max}")
            state["max_recovery_attempts"] = new_max
            max_attempts = new_max

    # Store for next iteration
    state["previous_error_count"] = current_error_count

    # Initialize error history for loop detection
    error_history = state.get("error_history", {})
    generated_files = state.get("generated_files", {})
    recovered_files = []
    unrecoverable_files = []

    # Process each error
    for error_info in errors_to_fix:
        filepath = error_info["filepath"]
        error_type = error_info.get("error_type", "Unknown")
        error_message = error_info.get("error_message", "")
        code = error_info["code"]

        # Log smart-parsed error info if available
        error_category = error_info.get("error_category", "")
        if error_category:
            logger.info(f"Fixing {filepath}: {error_type} ({error_category})")
            if error_info.get("fix_suggestion"):
                logger.info(f"  Hint: {error_info['fix_suggestion']}")
        else:
            logger.info(f"Fixing {filepath}: {error_type}")

        # Check for loop
        error_hash = _hash_error(error_message)
        if _detect_loop(filepath, error_hash, error_history):
            logger.warning(f"Skipping {filepath} - stuck in loop")
            unrecoverable_files.append(filepath)
            continue

        # Track error
        if filepath not in error_history:
            error_history[filepath] = []
        error_history[filepath].append(error_hash)

        # Get related context
        context = _get_related_context(filepath, generated_files)

        # Fix with LLM (passing full error_info for smart context)
        try:
            fixed_code = _fix_with_llm(
                filepath=filepath,
                error_info=error_info,
                code=code,
                context=context,
                state=state,
                llm=llm
            )

            # Re-inject deterministic locators for page files
            # This ensures LLM-regenerated code doesn't lose correct selectors
            if filepath.startswith("pages/") and filepath != "pages/base_page.py":
                fixed_code = _reinject_locators(filepath, fixed_code, registry)

            # Validate fix
            if _validate_fix(fixed_code, filepath):
                generated_files[filepath] = fixed_code
                recovered_files.append(filepath)
                logger.info(f"  Fixed {filepath}")
            else:
                logger.warning(f"  Fix validation failed for {filepath}")
                unrecoverable_files.append(filepath)

        except Exception as e:
            logger.error(f"  Error fixing {filepath}: {e}")
            unrecoverable_files.append(filepath)

    # Update state
    state["generated_files"] = generated_files
    state["error_history"] = error_history
    state["recovery_attempts"] = current_attempt
    state["recovered_files"] = state.get("recovered_files", []) + recovered_files
    state["unrecoverable_files"] = list(set(state.get("unrecoverable_files", []) + unrecoverable_files))

    # Update LLM usage stats
    usage = llm.get_usage_stats()
    state["llm_calls"] = state.get("llm_calls", 0) + usage["call_count"]
    state["llm_input_tokens"] = state.get("llm_input_tokens", 0) + usage["total_input_tokens"]
    state["llm_output_tokens"] = state.get("llm_output_tokens", 0) + usage["total_output_tokens"]

    # Log recovery event
    add_event_to_state(state, "recovery_attempt", "recovery", {
        "attempt": current_attempt,
        "files_fixed": recovered_files,
        "files_unrecoverable": unrecoverable_files,
        "errors_addressed": len(errors_to_fix)
    })

    # Log summary
    logger.info("-" * 40)
    logger.info("RECOVERY SUMMARY")
    logger.info(f"  Attempt: {current_attempt}/{max_attempts}")
    logger.info(f"  Files fixed: {len(recovered_files)}")
    logger.info(f"  Unrecoverable: {len(unrecoverable_files)}")
    logger.info("-" * 40)

    # Check if all files are unrecoverable
    if len(unrecoverable_files) == len(errors_to_fix):
        logger.warning("All files are unrecoverable - needs human intervention")
        state["needs_human_intervention"] = True

    # Log node complete
    add_event_to_state(state, "node_complete", "recovery")

    return state
