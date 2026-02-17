"""Recovery Node - Fixes errors in generated code using LLM.

This node:
1. Analyzes verification errors
2. Uses LLM to generate fixes
3. Applies fixes and re-verifies
4. Tracks retry attempts (max 3)
5. Escalates to human if retries exhausted

Supports multiple platforms:
- Web (Selenium)
- Android (Appium)
"""

import ast
import logging
import re
from difflib import get_close_matches
from typing import Dict, List, Any, Tuple, Optional

from ..models.state import AgentState
from ..models.schemas import CheckpointStatus
from ..llm.bedrock_client import BedrockClient
from ..templates import get_templates, is_mobile_platform

logger = logging.getLogger(__name__)


# =============================================================================
# AST-BASED METHOD MISMATCH DETECTION
# =============================================================================

def _extract_public_methods_from_code(code: str) -> List[str]:
    """Extract public method names from Python code.

    Args:
        code: Python source code

    Returns:
        List of public method names
    """
    try:
        tree = ast.parse(code)
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if not item.name.startswith('_'):
                            methods.append(item.name)
        return methods
    except SyntaxError:
        return []


def _extract_method_calls_from_test(code: str) -> List[str]:
    """Extract method calls made in test code on page objects.

    Args:
        code: Python test code

    Returns:
        List of method names called (may include duplicates)
    """
    try:
        tree = ast.parse(code)
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                # Skip common built-in methods
                if method_name not in ['get', 'set', 'update', 'append', 'format']:
                    calls.append(method_name)
        return calls
    except SyntaxError:
        return []


def _analyze_method_mismatch(
    test_code: str,
    page_code: str,
    base_page_methods: Optional[List[str]] = None
) -> Dict[str, str]:
    """Find method calls in test that don't exist in page and suggest fixes.

    Uses AST analysis and fuzzy matching to detect mismatches and provide
    specific replacement suggestions.

    Args:
        test_code: Test file source code
        page_code: Page object source code
        base_page_methods: List of methods available from BasePage

    Returns:
        Dict mapping incorrect method names to suggested replacements
    """
    if base_page_methods is None:
        base_page_methods = [
            # Common methods
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

    # Extract actual methods from page object
    page_methods = _extract_public_methods_from_code(page_code)
    available_methods = list(set(page_methods + base_page_methods))

    # Extract method calls from test
    called_methods = _extract_method_calls_from_test(test_code)

    # Find mismatches and suggest closest match
    fixes = {}
    for called in set(called_methods):  # Deduplicate
        if called not in available_methods:
            # Try to find a close match
            close = get_close_matches(called, available_methods, n=1, cutoff=0.5)
            if close:
                fixes[called] = close[0]
                logger.debug(f"Method mismatch: '{called}' -> suggest '{close[0]}'")
            else:
                # Special case: common patterns
                if called.startswith('wait_for_'):
                    # wait_for_element_visible -> find_element_visible
                    potential_fix = called.replace('wait_for_', 'find_')
                    if potential_fix in available_methods:
                        fixes[called] = potential_fix
                    elif 'find_element_visible' in available_methods:
                        fixes[called] = 'find_element_visible'
                elif called.startswith('get_') and called.endswith('_text'):
                    # get_username_text -> get_element_text (or specific getter)
                    if 'get_element_text' in available_methods:
                        fixes[called] = 'get_element_text'
                elif called.startswith('click_'):
                    # click_login_button -> click or tap
                    if 'tap' in available_methods:
                        fixes[called] = 'tap'
                    elif 'click' in available_methods:
                        fixes[called] = 'click'

    return fixes


def _identify_page_from_error(error_message: str, generated_files: Dict[str, str]) -> Optional[str]:
    """Identify the page file associated with an error.

    Args:
        error_message: Error message from test execution
        generated_files: Dict of filepath -> code

    Returns:
        Page file path or None
    """
    # Pattern: "'LoginScreen' object has no attribute 'wait_for_element_visible'"
    page_class_match = re.search(r"'(\w+(?:Page|Screen))' object has no attribute", error_message)
    if page_class_match:
        page_class = page_class_match.group(1)
        # Map to page file using snake_case
        # LoginScreen -> login_screen.py
        snake_name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', page_class)
        snake_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_name).lower()
        page_file = f"pages/{snake_name}.py"
        if page_file in generated_files:
            return page_file

    return None


RECOVERY_SYSTEM_PROMPT = """You are an expert Python developer debugging test automation code.
Your task is to fix errors in generated code.

RULES:
1. Fix ONLY the specific error mentioned
2. Preserve the overall structure and logic
3. Return the COMPLETE fixed file content
4. Do not add unnecessary changes
5. Ensure the fix is syntactically correct
6. Return ONLY the Python code, no explanations"""


# Web/Selenium recovery prompt
RECOVERY_PROMPT_WEB = """Fix the following Python file that has an error:

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
- DO NOT invent methods - use ONLY methods that exist in page objects!

CONTEXT:
- If Checkpoint A (Syntax) failed: The code has basic Python syntax errors.
- If Checkpoint B (Imports) failed: There are unresolvable import statements. **CRITICAL: Replace Playwright with Selenium imports!**
- If Checkpoint B.5 (Method Consistency) failed: Tests call methods that don't exist in page objects. You MUST use only methods defined in the page classes!
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


# Android/Appium recovery prompt
RECOVERY_PROMPT_ANDROID = """Fix the following Python file that has an error:

FILE: {filepath}
CHECKPOINT: {checkpoint}
ERROR TYPE: {error_type}
ERROR MESSAGE: {error_message}

ORIGINAL CODE:
```python
{code}
```

BASE PAGE CLASS (for reference - these are the available methods for ANDROID/APPIUM):
```python
class BasePage:
    # Element finding
    def find_element(self, by: AppiumBy, value: str) -> WebElement
    def find_element_clickable(self, by: AppiumBy, value: str) -> WebElement
    def find_element_visible(self, by: AppiumBy, value: str) -> WebElement
    def is_element_present(self, by: AppiumBy, value: str, timeout: int = 5) -> bool
    def get_element_text(self, by: AppiumBy, value: str) -> str

    # Tap & Click
    def tap(self, by: AppiumBy, value: str)
    def click(self, by: AppiumBy, value: str)  # alias for tap
    def long_press(self, by: AppiumBy, value: str, duration: int = 1000)

    # Text input
    def enter_text(self, by: AppiumBy, value: str, text: str)
    def clear_text(self, by: AppiumBy, value: str)

    # Keyboard
    def hide_keyboard(self)
    def is_keyboard_shown(self) -> bool

    # Swipe gestures
    def swipe(self, start_x, start_y, end_x, end_y, duration=800)
    def swipe_up(self, percent: float = 0.5)
    def swipe_down(self, percent: float = 0.5)
    def scroll_to_element(self, by: AppiumBy, value: str, max_swipes: int = 5)

    # App state
    def get_current_activity(self) -> str
    def get_current_package(self) -> str
    def wait_for_activity(self, activity: str, timeout: int = 10) -> bool
    def background_app(self, seconds: int = 1)
    def launch_app(self)
    def close_app(self)
```

CRITICAL: This project uses APPIUM for ANDROID, NOT Selenium for web!
- Use `AppiumBy` instead of `By` for locators
- Use `AppiumBy.ACCESSIBILITY_ID`, `AppiumBy.ID`, `AppiumBy.XPATH` - NOT CSS selectors
- Import from `appium.webdriver.common.appiumby import AppiumBy`
- Page classes take only `driver` parameter (no `base_url`)
- Use `tap()` instead of `click()` for mobile interactions
- Call `hide_keyboard()` after text input

CRITICAL: Method Name Fixes Required!
- Replace `wait_for_element_visible()` with `find_element_visible()`
- Replace `wait_for_element_clickable()` with `find_element_clickable()`
- Replace `wait_for_element()` with `find_element()`
- The BasePage class does NOT have `wait_for_*` methods - only `find_*` methods!
- DO NOT invent methods - use ONLY methods that exist in page objects!

CONTEXT:
- If Checkpoint A (Syntax) failed: The code has basic Python syntax errors.
- If Checkpoint B (Imports) failed: There are unresolvable import statements. Use Appium imports!
- If Checkpoint B.5 (Method Consistency) failed: Tests call methods that don't exist in page objects. You MUST use only methods defined in the page classes!
- If Checkpoint C (Collection) failed: Pytest could not discover tests.
- If Checkpoint D (Test Execution) failed: Runtime errors on the Android device.

Common Android-specific issues:
- Using `By` instead of `AppiumBy`
- Using CSS selectors (not supported in Appium)
- Page class expecting `base_url` parameter
- Missing `hide_keyboard()` calls after text input
- Wrong locator strategies for mobile
- TimeoutException / NoSuchElementException: Usually means:
  * Selector is wrong - verify resource-id or accessibility_id matches the app
  * Missing navigation step - e.g., need to tap menu button before accessing Login screen
  * Element not visible - may need to scroll or wait for animation
  * Add try/except with better error messages for debugging

IMPORTANT:
- Use ONLY the methods listed in BasePage above
- Use `AppiumBy` for all locators
- NO CSS selectors - use accessibility_id, id, xpath
- Call `hide_keyboard()` after entering text
- Page objects take only `driver`, not `base_url`

Provide the COMPLETE fixed code. Return ONLY the Python code, no markdown or explanation."""


def _get_recovery_prompt(platform_type: str) -> str:
    """Get platform-specific recovery prompt template.

    Args:
        platform_type: 'web' or 'android'

    Returns:
        Recovery prompt template string
    """
    if is_mobile_platform(platform_type):
        return RECOVERY_PROMPT_ANDROID
    return RECOVERY_PROMPT_WEB


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
    # Include checkpoint_b5 (method consistency) as it catches method mismatches early
    checkpoint_priority = ["checkpoint_d", "checkpoint_b5", "checkpoint_a", "checkpoint_b", "checkpoint_c"]

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

            # =====================================================
            # SPECIAL HANDLING FOR CHECKPOINT B.5 (Method Consistency)
            # =====================================================
            # Checkpoint B.5 errors are on test files, and the fix is usually
            # to use the correct method name from the page object
            if checkpoint_name == "B.5" and filepath.startswith("tests/"):
                # Enhance error message with fix guidance
                error_msg = (
                    f"METHOD MISMATCH ERROR:\n{error_msg}\n\n"
                    f"FIX INSTRUCTIONS:\n"
                    f"1. Replace all calls to non-existent methods with methods that exist in the page object\n"
                    f"2. Check the 'Available methods' list in the error message above\n"
                    f"3. Common fixes:\n"
                    f"   - tap_checkout_button() -> tap_menu_button() or tap_cart_icon()\n"
                    f"   - is_cart_screen_displayed() -> is_products_screen_displayed()\n"
                    f"   - wait_for_* methods -> find_element_* methods\n"
                    f"4. Make sure all method calls match exactly what's defined in the page objects"
                )

            # Map test file errors to source files if needed
            actual_filepath = filepath
            if filepath not in generated_files:
                # =====================================================
                # SPECIAL HANDLING FOR CHECKPOINT C (Collection Errors)
                # =====================================================
                # Checkpoint C stores errors under "collection" key, not file paths.
                # We need to parse the error message to find the actual file.
                if filepath == "collection" and checkpoint_name == "C":
                    # Parse pytest collection error to find the failing file
                    # Pattern: "ERROR collecting tests/test_xxx.py" or
                    #          "ImportError while importing test module '...tests/test_xxx.py'"

                    # Try to find the test file from the error
                    test_file_match = re.search(
                        r"(?:ERROR collecting |importing test module ['\"]?[^'\"]*?)(tests/[^'\":\s]+\.py)",
                        error_msg
                    )
                    if test_file_match:
                        actual_filepath = test_file_match.group(1)
                        logger.info(f"Extracted test file from collection error: {actual_filepath}")

                    # If test file found, also check for import error details
                    # Pattern: "from pages.cartscreen import CartScreen" -> should be "pages.cart_screen"
                    import_error_match = re.search(
                        r"(?:from|import)\s+(pages\.[^\s]+)\s+import",
                        error_msg
                    )
                    if import_error_match:
                        bad_import = import_error_match.group(1)
                        logger.info(f"Found bad import: {bad_import}")
                        # Enhance error message with fix hint
                        error_msg = (
                            f"IMPORT ERROR: The file has incorrect import statements.\n"
                            f"Bad import found: '{bad_import}'\n"
                            f"The page files use snake_case naming (e.g., 'pages.cart_screen' not 'pages.cartscreen').\n"
                            f"Fix ALL imports to use snake_case module names matching the actual file names.\n\n"
                            f"Original error:\n{error_msg}"
                        )

                    # Also check for ModuleNotFoundError pattern
                    module_error_match = re.search(
                        r"ModuleNotFoundError: No module named '([^']+)'",
                        error_msg
                    )
                    if module_error_match:
                        bad_module = module_error_match.group(1)
                        logger.info(f"Found ModuleNotFoundError for: {bad_module}")
                        # This confirms it's an import issue
                        if "pages." in bad_module and "IMPORT ERROR" not in error_msg:
                            error_msg = (
                                f"IMPORT ERROR: ModuleNotFoundError for '{bad_module}'.\n"
                                f"The page files use snake_case naming (e.g., 'pages.cart_screen' not 'pages.cartscreen').\n"
                                f"Fix ALL imports to use snake_case module names matching the actual file names.\n\n"
                                f"Original error:\n{error_msg}"
                            )

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
                        # Last resort for collection errors: the test file itself needs fixing
                        if filepath == "collection":
                            # Find the test file in generated files
                            for gen_file in generated_files.keys():
                                if gen_file.startswith("tests/") and gen_file.endswith(".py") and "test_" in gen_file:
                                    actual_filepath = gen_file
                                    logger.info(f"Falling back to test file for collection error: {actual_filepath}")
                                    break

                        if actual_filepath not in generated_files:
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
    checkpoint: str = "Unknown",
    platform_type: str = "web",
    generated_files: Dict[str, str] = None
) -> Tuple[str, bool]:
    """
    Use LLM to fix a file with an error.

    Args:
        filepath: Path to the file
        error_type: Type of error (checkpoint name)
        error_message: Error message
        code: Current code content
        llm: Bedrock client
        checkpoint: Checkpoint name (A, B, C, D, or B.5)
        platform_type: Target platform ('web' or 'android')
        generated_files: Dict of all generated files (for AST analysis)

    Returns:
        Tuple of (fixed_code, success)
    """
    if generated_files is None:
        generated_files = {}

    # =========================================================================
    # SMART RECOVERY: Detect method mismatches using AST analysis
    # =========================================================================
    enhanced_error_message = error_message

    # Check if this is a method mismatch error (AttributeError or B.5 consistency)
    is_method_error = (
        "AttributeError" in error_message or
        "has no attribute" in error_message or
        "undefined method" in error_message.lower() or
        checkpoint == "B.5"
    )

    if is_method_error:
        # Try to identify the relevant page object
        page_file = _identify_page_from_error(error_message, generated_files)

        if page_file and page_file in generated_files:
            page_code = generated_files[page_file]
            fixes = _analyze_method_mismatch(code, page_code)

            if fixes:
                enhanced_error_message += "\n\n" + "=" * 50
                enhanced_error_message += "\nDETECTED METHOD MISMATCHES (apply these EXACT fixes):\n"
                for wrong, correct in fixes.items():
                    enhanced_error_message += f"  - Replace ALL calls to '{wrong}()' with '{correct}()'\n"
                enhanced_error_message += "=" * 50
                logger.info(f"  AST analysis found {len(fixes)} method mismatches to fix")
        elif filepath.startswith("tests/") and filepath in generated_files:
            # For test files, check against all page objects
            all_fixes = {}
            for page_path, page_code in generated_files.items():
                if page_path.startswith("pages/") and page_path != "pages/base_page.py":
                    fixes = _analyze_method_mismatch(code, page_code)
                    all_fixes.update(fixes)

            if all_fixes:
                enhanced_error_message += "\n\n" + "=" * 50
                enhanced_error_message += "\nDETECTED METHOD MISMATCHES (apply these EXACT fixes):\n"
                for wrong, correct in all_fixes.items():
                    enhanced_error_message += f"  - Replace ALL calls to '{wrong}()' with '{correct}()'\n"
                enhanced_error_message += "=" * 50
                logger.info(f"  AST analysis found {len(all_fixes)} method mismatches to fix")

    # Get platform-specific recovery prompt
    prompt_template = _get_recovery_prompt(platform_type)

    prompt = prompt_template.format(
        filepath=filepath,
        checkpoint=checkpoint,
        error_type=error_type,
        error_message=enhanced_error_message,
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


def _extract_error_type(error_msg: str) -> str:
    """Extract the main error type from an error message.

    Args:
        error_msg: Error message string

    Returns:
        Normalized error type string
    """
    error_patterns = [
        (r"TimeoutException", "TimeoutException"),
        (r"NoSuchElementException", "NoSuchElementException"),
        (r"StaleElementReferenceException", "StaleElementReferenceException"),
        (r"ElementNotInteractableException", "ElementNotInteractableException"),
        (r"AttributeError.*has no attribute '([^']+)'", "AttributeError"),
        (r"ModuleNotFoundError", "ModuleNotFoundError"),
        (r"ImportError", "ImportError"),
        (r"SyntaxError", "SyntaxError"),
        (r"NameError", "NameError"),
        (r"TypeError", "TypeError"),
    ]

    for pattern, error_type in error_patterns:
        if re.search(pattern, error_msg, re.IGNORECASE):
            return error_type

    return "UnknownError"


# Error types that are typically not fixable via code changes alone
# These usually indicate deep app state problems that require manual investigation
# NOTE: TimeoutException and NoSuchElementException CAN be fixed by:
#   - Correcting selectors/locators
#   - Adding navigation steps (e.g., opening menu before clicking login)
#   - Adjusting wait strategies
UNFIXABLE_ERROR_TYPES = {
    "StaleElementReferenceException",  # Element reference is stale - timing/DOM issue
    # "TimeoutException" - REMOVED: Can be fixed by correcting selectors or adding navigation
    # "NoSuchElementException" - REMOVED: Can be fixed by correcting selectors
    # "ElementNotInteractableException" - REMOVED: Can be fixed by adding waits or scrolling
}


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

    # Track error history to detect loops
    error_history = state.get("error_history", [])

    # Extract current errors to check for loops
    errors_to_fix = _extract_errors_to_fix(state)
    current_error_types = set()
    for error in errors_to_fix:
        error_type = _extract_error_type(error.get("error_message", ""))
        current_error_types.add(error_type)

    # Check if we're stuck on unfixable errors
    if current_error_types and current_error_types.issubset(UNFIXABLE_ERROR_TYPES):
        logger.warning(f"Current errors are unfixable via code changes: {current_error_types}")
        logger.warning("These errors typically indicate:")
        logger.warning("  - Incorrect element selectors/locators")
        logger.warning("  - App state issues (element not visible/loaded)")
        logger.warning("  - Timing issues (element not ready)")
        logger.warning("Escalating to human intervention...")
        state["needs_human_intervention"] = True
        state["unfixable_errors"] = list(current_error_types)
        return state

    # Check if the same error types keep occurring (loop detection)
    if error_history:
        last_error_types = set(error_history[-1]) if error_history[-1] else set()
        if current_error_types == last_error_types and current_attempts >= 1:
            logger.warning(f"Same error types occurring repeatedly: {current_error_types}")
            logger.warning("Recovery is not making progress - escalating to human intervention")
            state["needs_human_intervention"] = True
            state["stuck_on_errors"] = list(current_error_types)
            return state

    # Record current error types in history
    error_history.append(list(current_error_types))
    state["error_history"] = error_history

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

    # Get platform type for recovery prompts
    module_spec = state.get("module_spec", {})
    platform_type = state.get("platform_type", module_spec.get("platform_type", "web"))
    is_mobile = is_mobile_platform(platform_type)

    logger.info(f"Platform: {platform_type}")

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

        # Enhance error message based on platform
        error_message = error["error_message"]

        # =====================================================
        # For test files with method consistency errors, include
        # the actual page object code so LLM knows what methods exist
        # =====================================================
        if filepath.startswith("tests/") and error.get("checkpoint") == "B.5":
            page_code_context = "\n\nAVAILABLE PAGE OBJECT METHODS:\n"
            page_code_context += "=" * 50 + "\n"
            for page_path, page_code in generated_files.items():
                if page_path.startswith("pages/") and page_path != "pages/base_page.py" and page_path != "pages/__init__.py":
                    # Extract just the method signatures from the page
                    page_methods = _extract_public_methods_from_code(page_code)
                    if page_methods:
                        class_name = page_path.replace("pages/", "").replace(".py", "")
                        # Convert snake_case to CamelCase for display
                        class_display = ''.join(word.title() for word in class_name.split('_'))
                        page_code_context += f"\n{class_display} methods:\n"
                        for method in page_methods:
                            page_code_context += f"  - {method}()\n"
            page_code_context += "=" * 50 + "\n"
            page_code_context += "\nYou MUST replace ALL undefined method calls with methods from the list above.\n"
            error_message = error_message + page_code_context

        if is_mobile:
            # Android/Appium specific enhancements
            if "By." in error["code"] and "AppiumBy" not in error["code"]:
                error_message = f"CRITICAL: This file uses Selenium By locators but the project uses Appium! {error_message}\n\nYou MUST use AppiumBy instead of By."
                logger.warning(f"  Detected Selenium By usage - will enforce Appium replacement")
        else:
            # Web/Selenium specific enhancements
            if "playwright" in error_message.lower() or "playwright" in error["code"].lower():
                error_message = f"CRITICAL: This file uses Playwright but the project uses Selenium! {error_message}\n\nYou MUST replace ALL Playwright code with Selenium equivalents."
                logger.warning(f"  Detected Playwright usage - will enforce Selenium replacement")

        fixed_code, success = _fix_file_with_llm(
            filepath=filepath,
            error_type=error["error_type"],
            error_message=error_message,
            code=error["code"],
            llm=llm,
            checkpoint=error.get("checkpoint", "Unknown"),
            platform_type=platform_type,
            generated_files=generated_files  # Pass for AST analysis
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
    # Include checkpoint_b5 for method consistency errors
    results = state.get("verification_results", {})
    has_errors = False

    # Check all checkpoints, prioritizing checkpoint_d and checkpoint_b5
    for checkpoint_key in ["checkpoint_d", "checkpoint_b5", "checkpoint_a", "checkpoint_b", "checkpoint_c"]:
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
