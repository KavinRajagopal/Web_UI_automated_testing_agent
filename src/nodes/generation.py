"""Generation Node - Generates automation code from the plan.

This node generates:
1. Base classes (BasePage)
2. Page Object classes
3. Flow/Action helper classes
4. Pytest test files
5. conftest.py with fixtures
6. pytest.ini configuration
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Set

from ..models.state import AgentState
from ..llm.bedrock_client import BedrockClient
from ..tools.method_extractor import (
    extract_method_names,
    extract_method_signatures,
    extract_method_calls
)
from ..utils.event_logger import add_event_to_state
from ..utils.method_registry import get_registry, MethodRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# STANDARD METHOD NAMES
# =============================================================================

STANDARD_METHOD_NAMES = {
    "page_loaded": "is_page_loaded",
    "title_displayed": "is_title_displayed", 
    "title_text": "get_title_text",
    "page_title": "get_page_title",
    "on_page": "is_on_page",
    "error_displayed": "is_error_displayed",
    "error_message": "get_error_message",
    "element_present": "is_element_present",
    "element_visible": "is_element_visible",
    "element_clickable": "is_element_clickable"
}


def analyze_test_requirements_for_methods(
    tests: List[Dict[str, Any]],
    test_cases: List[Dict[str, Any]]
) -> Dict[str, Set[str]]:
    """
    Analyze test plans and test cases to determine what methods are needed.
    
    Args:
        tests: List of test plans from generation plan
        test_cases: Original test case data
        
    Returns:
        Dict mapping page_name -> set of required method names
    """
    required_methods = {}
    tc_lookup = {tc.get("test_id"): tc for tc in test_cases}
    
    for test in tests:
        test_id = test.get("test_id", "")
        tc_data = tc_lookup.get(test_id, {})
        pages_used = test.get("pages_used", [])
        steps = test.get("steps_summary", []) or tc_data.get("test_steps", [])
        
        for page in pages_used:
            if page not in required_methods:
                required_methods[page] = set()
            
            # Analyze steps to infer required methods
            for step in steps:
                step_lower = step.lower() if isinstance(step, str) else str(step).lower()
                
                # Common patterns
                if "login" in step_lower or "authenticate" in step_lower:
                    required_methods[page].add("login")
                if "click" in step_lower:
                    # Extract what to click
                    if "button" in step_lower or "submit" in step_lower:
                        required_methods[page].add("click_login")
                        required_methods[page].add("click_submit")
                    elif "add" in step_lower and "cart" in step_lower:
                        required_methods[page].add("add_to_cart")
                if "enter" in step_lower or "input" in step_lower or "type" in step_lower:
                    if "username" in step_lower:
                        required_methods[page].add("enter_username")
                    if "password" in step_lower:
                        required_methods[page].add("enter_password")
                if "verify" in step_lower or "check" in step_lower or "assert" in step_lower:
                    if "page" in step_lower and "load" in step_lower:
                        required_methods[page].add("is_page_loaded")
                    if "title" in step_lower:
                        required_methods[page].add("is_title_displayed")
                        required_methods[page].add("get_title_text")
                    if "error" in step_lower:
                        required_methods[page].add("is_error_displayed")
                        required_methods[page].add("get_error_message")
                if "sort" in step_lower:
                    required_methods[page].add("sort_products")
                if "view" in step_lower and "product" in step_lower:
                    required_methods[page].add("get_all_product_names")
                    required_methods[page].add("get_product_prices")
    
    return required_methods


# =============================================================================
# CODE TEMPLATES
# =============================================================================

BASE_PAGE_TEMPLATE = '''"""Base Page Object class for all page objects."""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class BasePage:
    """Base class for all Page Objects."""
    
    def __init__(self, driver: WebDriver, base_url: str = ""):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)
    
    def navigate(self, path: str = ""):
        """Navigate to a URL path."""
        url = f"{self.base_url}{path}"
        self.driver.get(url)
    
    def find_element(self, by: By, value: str) -> WebElement:
        """Find an element with explicit wait."""
        return self.wait.until(
            EC.presence_of_element_located((by, value))
        )
    
    def find_element_clickable(self, by: By, value: str) -> WebElement:
        """Find a clickable element with explicit wait."""
        return self.wait.until(
            EC.element_to_be_clickable((by, value))
        )
    
    def find_element_visible(self, by: By, value: str) -> WebElement:
        """Find a visible element with explicit wait."""
        return self.wait.until(
            EC.visibility_of_element_located((by, value))
        )
    
    def get_element_text(self, by: By, value: str) -> str:
        """Get text from an element."""
        element = self.find_element_visible(by, value)
        return element.text
    
    def is_element_present(self, by: By, value: str, timeout: int = 5) -> bool:
        """Check if an element is present."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except:
            return False
    
    def enter_text(self, by: By, value: str, text: str):
        """Clear and enter text into an input field."""
        element = self.find_element_visible(by, value)
        element.clear()
        element.send_keys(text)
    
    def click(self, by: By, value: str):
        """Click on an element."""
        element = self.find_element_clickable(by, value)
        element.click()
'''

CONFTEST_TEMPLATE = '''"""Pytest fixtures for {module_name} tests."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return "{base_url}"


@pytest.fixture(scope="function")
def driver(request):
    """Chrome WebDriver fixture.
    
    Default: Headless mode (HEADLESS=true)
    
    To run with visible browser (for debugging):
        HEADLESS=false pytest tests/ -v
        OR
        pytest --headless=false tests/ -v
    """
    options = Options()
    
    # Check for headless setting
    # Priority: pytest --headless flag > environment variable > state default
    headless = request.config.getoption("--headless", default=None)
    if headless is None:
        # Check environment variable
        headless_env = os.getenv("HEADLESS")
        if headless_env is not None:
            headless = headless_env.lower() == "true"
        else:
            # Use state default (from agent configuration)
            headless = {headless_default}  # This will be replaced by .format()
    else:
        headless = headless.lower() == "true"
    
    if headless:
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Start maximized for better visibility when not headless
    if not headless:
        options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    
    yield driver
    
    driver.quit()


def pytest_addoption(parser):
    """Add custom pytest command line options."""
    parser.addoption(
        "--headless",
        action="store",
        default=None,
        help="Run browser in headless mode: --headless=true or --headless=false (default: true - headless mode)"
    )


{allure_hooks}

{additional_fixtures}
'''

PYTEST_INI_TEMPLATE = '''[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short{allure_opts}
markers =
    smoke: Smoke tests
    regression: Regression tests
    login: Login related tests
    {additional_markers}
'''


PAGE_GENERATION_PROMPT = """Generate a Python Page Object class for {page_name}.

**THE FOLLOWING LOCATORS WILL BE AUTO-INJECTED - USE THESE EXACT CONSTANT NAMES:**
{locator_constants}

**REQUIRED ELEMENTS (for is_page_loaded check):**
{required_elements}

Methods to generate:
{methods}

CRITICAL REQUIREMENTS:
1. **USE SELENIUM ONLY - DO NOT USE PLAYWRIGHT**
2. Import BasePage from pages.base_page
3. DO NOT define locator constants - they will be auto-injected after class definition
4. Use the constant names above with self.CONSTANT_NAME syntax (e.g., self.USERNAME, self.LOGIN_BUTTON)
5. Use BasePage methods for all element interactions
6. Add docstrings to all methods

BasePage available methods:
- find_element_visible(by: By, value: str) -> WebElement
- find_element_clickable(by: By, value: str) -> WebElement
- find_element(by: By, value: str) -> WebElement
- get_element_text(by: By, value: str) -> str
- is_element_present(by: By, value: str, timeout: int = 5) -> bool
- enter_text(by: By, value: str, text: str)
- click(by: By, value: str)

**is_page_loaded() IMPLEMENTATION - CRITICAL:**
- Check ONLY the required elements listed above
- Use: return self.is_element_present(*self.CONSTANT_NAME, timeout=10)
- For multiple required elements, check ALL of them: return self.is_element_present(*self.X, timeout=10) and self.is_element_present(*self.Y, timeout=10)
- Use timeout=10 to allow page load time

STANDARD METHOD NAMING:
- is_page_loaded() -> bool: Check ONLY required elements are present (with timeout=10)
- is_on_page() -> bool: Alias that calls is_page_loaded()
- is_error_displayed() -> bool, get_error_message() -> str

FOR LOGIN PAGE - include both:
- click_login_button() - the main method
- click_login() - alias that calls click_login_button()

Return ONLY the Python code, no explanation."""


TEST_GENERATION_PROMPT = """Generate ONLY a Pytest test function (no imports, no module-level code) with these specifications:

Test ID: {test_id}
Test Name: {test_name}
Description: {description}

Steps:
{steps}

Expected Results:
{expected}

Available Pages: {pages_used}
Test Data: {test_data}

AVAILABLE PAGE OBJECT METHODS (use these exact method names):
{available_methods}

CRITICAL REQUIREMENTS:
1. **USE SELENIUM ONLY - DO NOT USE PLAYWRIGHT**
2. Use pytest fixtures (driver, base_url) - driver is Selenium WebDriver
3. **DO NOT include any import statements** - imports will be added separately
4. **DO NOT include module-level docstrings** - just the test function
5. DO NOT import from playwright.sync_api
6. DO NOT use Page, expect, or any Playwright APIs
7. Use ONLY the methods listed in "AVAILABLE PAGE OBJECT METHODS" above
8. Add pytest markers: {markers}
9. Add clear docstring INSIDE the function
10. Include assertions for expected results using Selenium/assert statements
11. For clicking login button use: click_login_button() or click_login() - either works
12. Use standard method names: is_page_loaded(), is_error_displayed(), get_error_message(), is_on_page()

Return ONLY the @pytest.mark decorated function definition starting with @pytest.mark, nothing else."""


# =============================================================================
# CODE GENERATION FUNCTIONS
# =============================================================================

def _get_by_type(selector_type: str) -> str:
    """Convert selector type to Selenium By type."""
    mapping = {
        "id": "By.ID",
        "data-testid": "By.CSS_SELECTOR",
        "data-test": "By.CSS_SELECTOR",
        "name": "By.NAME",
        "aria-label": "By.CSS_SELECTOR",
        "css": "By.CSS_SELECTOR",
        "xpath": "By.XPATH"
    }
    return mapping.get(selector_type, "By.CSS_SELECTOR")


def _get_selector_value(selector: Dict[str, Any]) -> str:
    """Get the selector value for Selenium.

    Uses single quotes inside CSS attribute selectors to avoid quote escaping issues
    when the value is embedded in Python code with double quotes.
    """
    selector_type = selector.get("selector_type", "css")
    value = selector.get("value", "")

    if selector_type == "data-testid":
        return f"[data-testid='{value}']"
    elif selector_type == "data-test":
        return f"[data-test='{value}']"
    elif selector_type == "aria-label":
        return f"[aria-label='{value}']"
    else:
        return value


def _generate_locators_code(page_metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate locator constants deterministically from element metadata.

    Selector priority (most to least stable):
    1. id - unique identifiers
    2. data-test / data-testid - test-specific attributes
    3. name - form element names
    4. css / other - fallback

    Args:
        page_metadata: Element metadata for the page

    Returns:
        Dict with 'constants' (Python code) and 'element_map' (name -> const_name)
    """
    locator_lines = []
    element_map = {}  # Maps element name to constant name

    # Priority order for selector types
    SELECTOR_PRIORITY = ["id", "data-test", "data-testid", "name", "css", "xpath", "aria-label"]

    for elem in page_metadata.get("elements", []):
        elem_name = elem.get("name", "unknown")
        selectors = elem.get("selectors", [])

        if selectors:
            # Find the best selector based on priority
            best = None
            for priority_type in SELECTOR_PRIORITY:
                for sel in selectors:
                    if sel.get("selector_type") == priority_type:
                        best = sel
                        break
                if best:
                    break

            # Fallback to first selector if no priority match
            if not best:
                best = selectors[0]

            by_type = _get_by_type(best.get("selector_type", "css"))
            value = _get_selector_value(best)

            # Convert element name to Python constant (e.g., "login-button" -> "LOGIN_BUTTON")
            const_name = elem_name.upper().replace("-", "_").replace(" ", "_")
            element_map[elem_name] = const_name

            locator_lines.append(f'    {const_name} = ({by_type}, "{value}")')

    return {
        "constants": "\n".join(locator_lines),
        "element_map": element_map
    }


def _inject_locators_into_code(code: str, locators_code: str, page_name: str) -> str:
    """
    Inject deterministic locators into LLM-generated code, replacing any LLM-generated ones.

    Args:
        code: LLM-generated page class code
        locators_code: Deterministic locator constants
        page_name: Name of the page class

    Returns:
        Code with correct locators injected
    """
    import re

    # Find the class definition
    class_pattern = rf'(class\s+{page_name}\s*\([^)]*\)\s*:\s*\n(?:\s*"""[^"]*"""\s*\n)?)'

    match = re.search(class_pattern, code)
    if not match:
        # Try simpler pattern
        class_pattern = rf'(class\s+{page_name}[^:]*:\s*\n)'
        match = re.search(class_pattern, code)

    if match:
        # Remove existing locator constants (lines with UPPER_CASE = (By.X, "..."))
        lines = code.split('\n')
        cleaned_lines = []
        skip_until_method = False

        for line in lines:
            stripped = line.strip()
            # Skip lines that look like locator constants
            if re.match(r'^[A-Z][A-Z0-9_]*\s*=\s*\(By\.', stripped):
                continue
            cleaned_lines.append(line)

        code = '\n'.join(cleaned_lines)

        # Now inject our locators after the class definition
        match = re.search(class_pattern, code)
        if match:
            insert_pos = match.end()

            # Check if there's a docstring after class def
            remaining = code[insert_pos:]
            docstring_match = re.match(r'(\s*"""[^"]*"""\s*\n|\s*\'\'\'[^\']*\'\'\'\s*\n)', remaining)
            if docstring_match:
                insert_pos += docstring_match.end()

            # Insert locators
            locators_section = f"\n    # Element Locators (auto-generated from metadata)\n{locators_code}\n"
            code = code[:insert_pos] + locators_section + code[insert_pos:]

    return code


def generate_page_class(
    page_plan: Dict[str, Any],
    page_metadata: Dict[str, Any],
    llm: BedrockClient
) -> str:
    """
    Generate a Page Object class using LLM with deterministic locator injection.

    The locators are generated deterministically from element metadata,
    not by the LLM, ensuring correct selectors every time.

    Args:
        page_plan: Plan for this page
        page_metadata: Element metadata for this page
        llm: Bedrock client

    Returns:
        Generated Python code with correct locators
    """
    page_name = page_plan.get("page_name", "Page")
    file_name = page_plan.get("file_name", "page.py")
    methods = page_plan.get("methods", [])

    # Generate locators DETERMINISTICALLY from metadata
    locators_info = _generate_locators_code(page_metadata)
    locators_code = locators_info["constants"]
    element_map = locators_info["element_map"]

    # Build locator constants list for the prompt (show what constants will be available)
    locator_constants_text = "\n".join(f"- self.{const}" for const in element_map.values())

    # Identify required elements (for is_page_loaded check)
    required_elements = []
    for elem in page_metadata.get("elements", []):
        elem_name = elem.get("name", "")
        if elem.get("is_required", False) and elem_name in element_map:
            const_name = element_map[elem_name]
            required_elements.append(f"- self.{const_name} ({elem_name})")

    # If no required elements specified, use key elements based on page type
    if not required_elements:
        # Default to first 2-3 key elements
        key_elements = list(element_map.items())[:3]
        required_elements = [f"- self.{const} ({name})" for name, const in key_elements]

    required_elements_text = "\n".join(required_elements) if required_elements else "- No specific required elements"

    # Format methods
    methods_text = "\n".join(f"- {m}" for m in methods) if methods else "- Standard getters/setters for all elements"

    prompt = PAGE_GENERATION_PROMPT.format(
        page_name=page_name,
        locator_constants=locator_constants_text,
        required_elements=required_elements_text,
        methods=methods_text
    )

    system_prompt = """You are an expert Python developer specializing in Selenium test automation.
Generate clean, well-documented code. **CRITICAL: Use Selenium WebDriver only. DO NOT use Playwright.**
The locators will be injected automatically - focus on generating the methods.
Follow the standard method naming conventions exactly as specified."""

    response = llm.chat(
        user_message=prompt,
        system=system_prompt
    )

    # Clean up response
    code = response.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]

    code = code.strip()

    # Validate - reject Playwright code
    if "playwright" in code.lower() or "from playwright" in code.lower():
        logger.warning(f"Generated code contains Playwright - regenerating...")
        prompt += "\n\nCRITICAL: The previous attempt used Playwright. You MUST use Selenium only. DO NOT use Playwright imports or APIs."
        response = llm.chat(user_message=prompt, system=system_prompt)
        code = response.strip()
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()

        if "playwright" in code.lower():
            logger.error(f"Still contains Playwright after retry")

    # DETERMINISTIC INJECTION: Replace any LLM-generated locators with correct ones
    code = _inject_locators_into_code(code, locators_code, page_name)

    logger.info(f"Generated {page_name} with {len(element_map)} deterministic locators")

    return code


def _clean_test_code(code: str) -> str:
    """
    Clean test code by removing imports and module-level content.

    Args:
        code: Raw generated test code

    Returns:
        Cleaned code with only test functions
    """
    lines = code.strip().split('\n')
    cleaned_lines = []
    in_function = False
    function_indent = 0

    for line in lines:
        stripped = line.strip()

        # Skip import statements
        if stripped.startswith('import ') or stripped.startswith('from '):
            continue

        # Skip module-level docstrings (triple quotes at start of file)
        if not in_function and (stripped.startswith('"""') or stripped.startswith("'''")):
            # If single-line docstring, skip it
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                continue
            # Multi-line docstring - skip until closing
            continue

        # Detect function start
        if stripped.startswith('@pytest.mark') or stripped.startswith('def test_'):
            in_function = True
            cleaned_lines.append(line)
            if stripped.startswith('def '):
                function_indent = len(line) - len(line.lstrip())
            continue

        # If we're in a function, keep the line
        if in_function:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def validate_generated_code(generated_files: Dict[str, str], registry: MethodRegistry) -> Dict[str, Any]:
    """
    Post-generation validation to catch method mismatches before verification.

    Checks:
    1. All method calls in tests exist in corresponding page objects
    2. All locator references in page objects are defined

    Returns:
        Dict with validation results and any issues found
    """
    issues = []
    warnings = []

    # Get test files
    test_files = {k: v for k, v in generated_files.items() if k.startswith("tests/") and k.endswith(".py")}
    page_files = {k: v for k, v in generated_files.items() if k.startswith("pages/") and k.endswith(".py")}

    # Check 1: Validate method calls in test files
    for test_file, test_code in test_files.items():
        if test_file == "tests/__init__.py" or test_file == "tests/conftest.py":
            continue

        # Extract method calls from test code
        try:
            method_calls = extract_method_calls(test_code)

            for call in method_calls:
                class_name = call.get("class_name", "")
                method_name = call.get("method_name", "")
                line = call.get("line", 0)

                # Skip built-in methods
                if method_name.startswith("_") or method_name in ["get", "find_element", "find_elements"]:
                    continue

                # Check if method exists in registry
                if class_name and "Page" in class_name:
                    validation = registry.validate_method_call(class_name, method_name)
                    if not validation.get("valid", True):
                        suggestion = validation.get("suggestion", "")
                        issue = {
                            "file": test_file,
                            "line": line,
                            "class": class_name,
                            "method": method_name,
                            "type": "missing_method",
                            "suggestion": suggestion
                        }
                        issues.append(issue)
        except Exception as e:
            warnings.append(f"Could not analyze {test_file}: {e}")

    # Check 2: Validate locator references in page objects
    for page_file, page_code in page_files.items():
        if page_file == "pages/__init__.py" or page_file == "pages/base_page.py":
            continue

        # Find locator references (self.SOMETHING_LOCATOR patterns)
        import re
        locator_refs = re.findall(r'self\.([A-Z][A-Z0-9_]+)', page_code)

        # Find locator definitions
        locator_defs = re.findall(r'^[ \t]+([A-Z][A-Z0-9_]+)\s*=\s*\(By\.', page_code, re.MULTILINE)

        # Check for undefined locators
        for ref in set(locator_refs):
            if ref not in locator_defs:
                issues.append({
                    "file": page_file,
                    "type": "undefined_locator",
                    "locator": ref,
                    "suggestion": f"Define {ref} = (By.XXX, 'selector') in the class"
                })

    # Log validation results
    if issues:
        logger.warning(f"Post-generation validation found {len(issues)} issues:")
        for issue in issues[:5]:  # Log first 5
            logger.warning(f"  {issue['file']}: {issue['type']} - {issue.get('method', issue.get('locator', ''))}")
        if len(issues) > 5:
            logger.warning(f"  ... and {len(issues) - 5} more issues")
    else:
        logger.info("Post-generation validation: All checks passed")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "issues_count": len(issues)
    }


def generate_test_file(
    tests: List[Dict[str, Any]],
    test_cases: List[Dict[str, Any]],
    pages: List[str],
    page_objects_code: Dict[str, str],
    llm: BedrockClient
) -> str:
    """
    Generate a test file with multiple test functions.

    Args:
        tests: List of test plans
        test_cases: Original test case data
        pages: Available page classes
        page_objects_code: Dict mapping page file paths to their generated code
        llm: Bedrock client

    Returns:
        Generated Python code
    """
    # Build test case lookup
    tc_lookup = {tc.get("test_id"): tc for tc in test_cases}

    # Get method registry for consistent method lookup
    registry = get_registry()

    # Build available methods from registry (preferred) or fallback to direct extraction
    available_methods_by_page = {}
    for page_name in pages:
        # Try registry first (most reliable)
        methods = registry.get_methods(page_name)
        if methods:
            available_methods_by_page[page_name] = methods
            logger.debug(f"Found {len(methods)} methods for {page_name} from registry")
        else:
            # Fallback: Try to find the page object code directly
            # Try multiple file name variants for robustness
            page_code = None
            page_name_clean = page_name.replace("Page", "").replace("page", "")
            variants = [
                f"pages/{page_name.lower()}_page.py",
                f"pages/{page_name_clean.lower()}_page.py",
                f"pages/{page_name.lower()}.py",
            ]
            for variant in variants:
                if variant in page_objects_code:
                    page_code = page_objects_code[variant]
                    break

            if page_code:
                # Extract method names using AST
                methods_dict = extract_method_names(page_code)
                methods = []
                for class_name, class_methods in methods_dict.items():
                    methods.extend(class_methods)
                available_methods_by_page[page_name] = methods
                logger.debug(f"Found {len(methods)} methods in {page_name} via fallback AST extraction")
            else:
                logger.warning(f"No methods found for {page_name} - neither in registry nor in generated code")

    # Generate each test
    test_codes = []
    for test_plan in tests:
        test_id = test_plan.get("test_id", "")
        tc_data = tc_lookup.get(test_id, {})

        # Build available methods text - use registry for consistent lookups
        pages_used = test_plan.get("pages_used", [])
        methods_text = ""
        for page_name in pages_used:
            # Try registry first (includes aliases automatically)
            methods_with_aliases = registry.get_methods_with_aliases(page_name)
            if methods_with_aliases:
                methods_text += f"\n{page_name} methods: {', '.join(sorted(methods_with_aliases)[:30])}"
            else:
                # Fallback to local lookup
                methods = available_methods_by_page.get(page_name, [])
                if methods:
                    method_set = set(methods)
                    # Add common aliases
                    if 'click_login_button' in method_set:
                        method_set.add('click_login')
                    methods_text += f"\n{page_name} methods: {', '.join(sorted(method_set)[:25])}"
                else:
                    # Last resort: use standard methods
                    logger.warning(f"No methods found for {page_name}, using standard method names")
                    methods_text += f"\n{page_name} methods: {', '.join(STANDARD_METHOD_NAMES.values())}"

        prompt = TEST_GENERATION_PROMPT.format(
            test_id=test_id,
            test_name=test_plan.get("test_name", "test_unnamed"),
            description=test_plan.get("description", ""),
            steps="\n".join(test_plan.get("steps_summary", [])),
            expected=tc_data.get("expected_result", "Test passes"),
            pages_used=", ".join(pages_used),
            markers=", ".join(test_plan.get("markers", [])),
            test_data=tc_data.get("test_data", ""),
            available_methods=methods_text
        )

        system_prompt = """You are an expert Python developer specializing in Selenium test automation.
Generate ONLY a pytest test function (no imports). **CRITICAL: Use Selenium only. DO NOT use Playwright.**
Use ONLY the methods listed in the "AVAILABLE PAGE OBJECT METHODS" section.
Return ONLY the decorated test function, starting with @pytest.mark - no imports, no module docstrings."""

        response = llm.chat(
            user_message=prompt,
            system=system_prompt
        )

        # Clean up
        code = response.strip()
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]

        # Clean the test code to remove any imports
        cleaned_code = _clean_test_code(code.strip())
        if cleaned_code.strip():
            test_codes.append(cleaned_code)

    # Build the test file with proper imports at the top
    imports = [
        '"""Automated test file."""',
        '',
        'import pytest',
        'from selenium.webdriver.common.by import By',
        'from selenium.webdriver.support.ui import WebDriverWait, Select',
        'from selenium.webdriver.support import expected_conditions as EC',
        ''
    ]

    # Add page imports - normalize page names to file names
    for page in sorted(set(pages)):
        # Normalize: "Login", "LoginPage", "login" -> "login_page" file, "LoginPage" class
        page_clean = page.replace('Page', '').replace('page', '')
        page_lower = page_clean.lower()
        class_name = f"{page_clean}Page" if not page.endswith('Page') else page
        # File is always {name}_page.py, class is always {Name}Page
        imports.append(f"from pages.{page_lower}_page import {class_name}")

    imports.append('')
    imports.append('')

    header = '\n'.join(imports)

    return header + '\n\n'.join(test_codes)


def generation_node(state: AgentState) -> AgentState:
    """
    Simplified generation node - generates all automation code.

    Generates:
    1. Base page class
    2. Page Object classes
    3. Flow classes (if needed)
    4. Test files
    5. conftest.py and pytest.ini

    Args:
        state: Current agent state

    Returns:
        Updated state with generated files
    """
    logger.info("=" * 60)
    logger.info("GENERATION NODE")
    logger.info("=" * 60)

    state["current_node"] = "generation"
    state["node_history"] = state.get("node_history", []) + ["generation"]

    # Log node start
    add_event_to_state(state, "node_start", "generation")

    plan = state.get("generation_plan", {})
    module_spec = state.get("module_spec", {})
    page_metadata = state.get("page_metadata", {})
    test_cases = state.get("test_cases", [])
    # Use approved_tests if available (from human gate), otherwise use all test_cases
    approved_tests = state.get("approved_tests", [])
    if approved_tests:
        test_cases = approved_tests
    output_path = state.get("output_path", "")

    generated_files = state.get("generated_files", {}).copy()  # Preserve existing files
    errors = []

    # Initialize method registry for tracking generated methods
    registry = get_registry()
    registry.clear()  # Start fresh for this generation

    # Initialize LLM with reasoning enabled
    llm = BedrockClient(
        model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        region_name=state.get("llm_region", "us-east-2"),
        profile_name=state.get("llm_profile", "default"),
        max_tokens=32768,
        enable_reasoning=True
    )

    module_name = module_spec.get("module_name", "test_module")
    base_url = module_spec.get("app_url", "")
    
    # ========================================================================
    # STAGE 1: Generate Base + Page Objects
    # ========================================================================
    logger.info("-" * 40)
    logger.info("Generating Base & Page Objects...")
    logger.info("-" * 40)

    # 1. Generate base_page.py
    logger.info("Generating base_page.py...")
    generated_files["pages/base_page.py"] = BASE_PAGE_TEMPLATE

    # 2. Generate Page Objects
    page_objects_code = {}  # Store generated page object code for test generation
    for page_plan in plan.get("pages", []):
        page_name = page_plan.get("page_name", "")
        file_name = page_plan.get("file_name", f"pages/{page_name.lower()}_page.py")

        logger.info(f"Generating {file_name}...")

        try:
            # Get metadata for this page - try multiple key variants for robustness
            page_meta = None
            page_meta_key = page_plan.get("page_metadata_key")

            if page_meta_key:
                page_meta = page_metadata.get(page_meta_key)

            if not page_meta:
                # Try exact page_name match (e.g., "LoginPage")
                page_meta = page_metadata.get(page_name)

            if not page_meta:
                # Try case-insensitive match
                for key in page_metadata.keys():
                    if key.lower() == page_name.lower():
                        page_meta = page_metadata.get(key)
                        logger.info(f"  Found metadata with key '{key}' for page '{page_name}'")
                        break

            if not page_meta:
                # Try without "Page" suffix variations
                base_name = page_name.replace("Page", "").replace("page", "")
                for key in page_metadata.keys():
                    key_base = key.replace("Page", "").replace("page", "")
                    if key_base.lower() == base_name.lower():
                        page_meta = page_metadata.get(key)
                        logger.info(f"  Found metadata with key '{key}' for base name '{base_name}'")
                        break

            if not page_meta:
                logger.warning(f"  No element metadata found for {page_name}")
                logger.warning(f"  Available metadata keys: {list(page_metadata.keys())}")
                page_meta = {}  # Empty dict as fallback

            code = generate_page_class(page_plan, page_meta, llm)
            generated_files[file_name] = code
            page_objects_code[file_name] = code  # Store for test generation

            # Register page in method registry with metadata for recovery re-injection
            page_info = registry.register_page_with_metadata(
                page_name=page_name,
                file_path=file_name,
                code=code,
                metadata=page_meta
            )
            logger.info(f"  Registered {page_name}: {len(page_info.methods)} methods, {len(page_info.locators)} locators")

            add_event_to_state(state, "file_generated", "generation", {
                "filepath": file_name,
                "type": "page_object",
                "methods_count": len(page_info.methods),
                "locators_count": len(page_info.locators)
            })
            logger.info(f"  -> {file_name}")
        except Exception as e:
            logger.error(f"  Failed to generate {file_name}: {e}")
            errors.append(f"Failed to generate {file_name}: {e}")

    # Generate __init__.py for pages
    generated_files["pages/__init__.py"] = '"""Page Objects package."""\n'
    
    # ========================================================================
    # STAGE 2: Generate Flows
    # ========================================================================
    logger.info("-" * 40)
    logger.info("Generating Flow Classes...")
    logger.info("-" * 40)

    # Generate Flow classes
    flows_generated = plan.get("flows", [])
    for flow_plan in flows_generated:
        flow_name = flow_plan.get("flow_name", "")
        file_name = flow_plan.get("file_name", f"flows/{flow_name.lower()}.py")

        logger.info(f"Generating {file_name}...")

        # Simple flow template
        pages_used = flow_plan.get("pages_used", [])
        imports = "\n".join(f"from pages.{p.lower()}_page import {p}Page" for p in pages_used)

        flow_code = f'''"""Flow class for {flow_name}."""

{imports}


class {flow_name}:
    """Helper class for {flow_plan.get('description', 'common flows')}."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
'''
        generated_files[file_name] = flow_code

        add_event_to_state(state, "file_generated", "generation", {
            "filepath": file_name,
            "type": "flow"
        })
        logger.info(f"  -> {file_name}")

    # Generate __init__.py for flows if any flows exist
    if flows_generated:
        generated_files["flows/__init__.py"] = '"""Flow helpers package."""\n'
    
    # ========================================================================
    # STAGE 3: Generate Tests + Config
    # ========================================================================
    logger.info("-" * 40)
    logger.info("Generating Tests & Configuration...")
    logger.info("-" * 40)

    # Get tests from plan
    all_tests = plan.get("tests", [])

    # Generate single test file (simplified - no batching)
    if all_tests:
        pages_used = list(set(
            p for t in all_tests for p in t.get("pages_used", [])
        ))

        test_file = f"tests/test_{module_name}.py"
        logger.info(f"Generating {test_file} with {len(all_tests)} tests...")

        try:
            test_code = generate_test_file(
                tests=all_tests,
                test_cases=test_cases,
                pages=pages_used,
                page_objects_code=page_objects_code,
                llm=llm
            )
            generated_files[test_file] = test_code

            add_event_to_state(state, "file_generated", "generation", {
                "filepath": test_file,
                "type": "test_file",
                "test_count": len(all_tests)
            })
            logger.info(f"  -> {test_file}")

        except Exception as e:
            logger.error(f"Failed to generate {test_file}: {e}")
            errors.append(f"Failed to generate {test_file}: {e}")
        
        # Generate conftest.py
        logger.info("Generating conftest.py...")
        
        fixtures = plan.get("conftest_fixtures", [])
        additional_fixtures = ""
        
        # Add login fixture if needed
        if "login_user" in fixtures:
            additional_fixtures += '''
@pytest.fixture(scope="function")
def login_user(driver, base_url):
    """Login with test user credentials."""
    from pages.loginpage import LoginPage
    login_page = LoginPage(driver, base_url)
    login_page.navigate()
    login_page.enter_username("standard_user")
    login_page.enter_password("secret_sauce")
    login_page.click_login()
    return driver
'''
        
        # Check if Allure is enabled (from state or environment variable)
        enable_allure = state.get("enable_allure", False)
        if not enable_allure:
            # Also check environment variable
            import os
            enable_allure = os.getenv("ENABLE_ALLURE", "false").lower() == "true"
        
        # Prepare Allure hooks for conftest (if enabled)
        allure_hooks = ""
        if enable_allure:
            allure_hooks = '''
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture screenshot on test failure for Allure."""
    try:
        import allure
    except ImportError:
        # Allure not installed, skip
        outcome = yield
        return
    
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        # Get the driver from the test
        if hasattr(item, 'funcargs') and 'driver' in item.funcargs:
            driver = item.funcargs['driver']
            try:
                screenshot = driver.get_screenshot_as_png()
                allure.attach(
                    screenshot,
                    name="screenshot",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception as e:
                print(f"Failed to capture screenshot: {e}")
'''
        
        # Get headless mode from state (default: True)
        headless_default = state.get("headless_mode", True)
        
        conftest = CONFTEST_TEMPLATE.format(
            module_name=module_name,
            base_url=base_url,
            allure_hooks=allure_hooks,
            additional_fixtures=additional_fixtures,
            headless_default=str(headless_default)
        )
        generated_files["tests/conftest.py"] = conftest
        
        # Generate pytest.ini
        logger.info("Generating pytest.ini...")
        
        markers = set()
        for test in all_tests:
            markers.update(test.get("markers", []))
        
        additional_markers = "\n    ".join(f"{m}: {m} tests" for m in markers)
        
        # Add Allure options if enabled
        allure_opts = ""
        if enable_allure:
            allure_opts = " --alluredir=allure-results"
            logger.info("  Allure reporting enabled")
        
        pytest_ini = PYTEST_INI_TEMPLATE.format(
            additional_markers=additional_markers,
            allure_opts=allure_opts
        )
        generated_files["pytest.ini"] = pytest_ini
        
        # Generate __init__.py for tests
        generated_files["tests/__init__.py"] = '"""Tests package."""\n'

    # ========================================================================
    # FINALIZE
    # ========================================================================

    # Update state with all generated files
    state["generated_files"] = generated_files
    state["generation_errors"] = errors

    # Update LLM usage stats
    usage = llm.get_usage_stats()
    state["llm_calls"] = state.get("llm_calls", 0) + usage["call_count"]
    state["llm_input_tokens"] = state.get("llm_input_tokens", 0) + usage["total_input_tokens"]
    state["llm_output_tokens"] = state.get("llm_output_tokens", 0) + usage["total_output_tokens"]

    # ========================================================================
    # POST-GENERATION VALIDATION
    # ========================================================================
    logger.info("-" * 40)
    logger.info("Running Post-Generation Validation...")
    logger.info("-" * 40)

    validation_results = validate_generated_code(generated_files, registry)
    state["validation_results"] = validation_results

    if validation_results["issues"]:
        logger.warning(f"Found {validation_results['issues_count']} potential issues")
        # Store issues for potential auto-fix in verification/recovery
        state["generation_issues"] = validation_results["issues"]
    else:
        logger.info("Validation passed - no issues found")

    # Log generation event
    add_event_to_state(state, "generation_complete", "generation", {
        "files_count": len(generated_files),
        "errors_count": len(errors),
        "llm_calls": usage["call_count"],
        "llm_tokens": usage["total_tokens"],
        "validation_issues": validation_results["issues_count"]
    })

    # Log summary
    logger.info("-" * 40)
    logger.info("GENERATION SUMMARY")
    logger.info(f"  Files generated: {len(generated_files)}")
    logger.info(f"  Errors: {len(errors)}")
    logger.info(f"  LLM calls: {usage['call_count']}")
    logger.info(f"  LLM tokens: {usage['total_tokens']}")
    logger.info("-" * 40)

    for filepath in generated_files.keys():
        logger.info(f"  -> {filepath}")

    # Mark generation as complete
    state["generation_complete"] = True

    # Log node complete
    add_event_to_state(state, "node_complete", "generation")

    return state
