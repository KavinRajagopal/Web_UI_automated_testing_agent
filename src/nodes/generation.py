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


PAGE_GENERATION_PROMPT = """Generate a Python Page Object class with these specifications:

Page Name: {page_name}
File: {file_name}
Base Class: BasePage

Elements (with selectors):
{elements}

Methods to generate:
{methods}

CRITICAL REQUIREMENTS:
1. **USE SELENIUM ONLY - DO NOT USE PLAYWRIGHT**
2. Import BasePage from pages.base_page (NOT playwright)
3. Use Selenium WebDriver, NOT Playwright Page
4. Use BasePage methods: find_element_visible(), find_element_clickable(), find_element()
5. DO NOT use wait_for_element_visible() or any wait_for_* methods
6. Define element locators as class attributes using tuples: (By.X, "value")
7. Create getter/setter methods for each element
8. Create action methods as specified
9. Use the best selector (data-test, id, name, aria-label)
10. Add docstrings to all methods
11. Handle waits properly using BasePage methods (find_* not wait_for_*)

BasePage available methods:
- find_element(by: By, value: str) -> WebElement
- find_element_clickable(by: By, value: str) -> WebElement
- find_element_visible(by: By, value: str) -> WebElement
- get_element_text(by: By, value: str) -> str
- is_element_present(by: By, value: str, timeout: int = 5) -> bool
- enter_text(by: By, value: str, text: str)
- click(by: By, value: str)

STANDARD METHOD NAMING (use these exact names):
- For page loaded checks: is_page_loaded() -> bool
- For title display: is_title_displayed() -> bool
- For title text: get_title_text() -> str or get_page_title() -> str
- For page verification: is_on_page() -> bool
- For error checks: is_error_displayed() -> bool, get_error_message() -> str
- For element checks: is_element_present(), is_element_visible(), is_element_clickable()

Return ONLY the Python code, no explanation."""


TEST_GENERATION_PROMPT = """Generate a Pytest test function with these specifications:

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
3. Import page objects from pages.* (they use Selenium, NOT Playwright)
4. DO NOT import from playwright.sync_api
5. DO NOT use Page, expect, or any Playwright APIs
6. Use ONLY the methods listed in "AVAILABLE PAGE OBJECT METHODS" above
7. Add pytest markers: {markers}
8. Add clear docstring with test description
9. Include assertions for expected results using Selenium/assert statements
10. Handle setup and teardown if needed

Return ONLY the Python code, no explanation."""


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
    """Get the selector value for Selenium."""
    selector_type = selector.get("selector_type", "css")
    value = selector.get("value", "")
    
    if selector_type == "data-testid":
        return f'[data-testid="{value}"]'
    elif selector_type == "data-test":
        return f'[data-test="{value}"]'
    elif selector_type == "aria-label":
        return f'[aria-label="{value}"]'
    else:
        return value


def generate_page_class(
    page_plan: Dict[str, Any],
    page_metadata: Dict[str, Any],
    llm: BedrockClient
) -> str:
    """
    Generate a Page Object class using LLM.
    
    Args:
        page_plan: Plan for this page
        page_metadata: Element metadata for this page
        llm: Bedrock client
        
    Returns:
        Generated Python code
    """
    page_name = page_plan.get("page_name", "Page")
    file_name = page_plan.get("file_name", "page.py")
    methods = page_plan.get("methods", [])
    
    # Format elements
    elements_text = ""
    for elem in page_metadata.get("elements", []):
        elem_name = elem.get("name", "unknown")
        elem_type = elem.get("element_type", "element")
        selectors = elem.get("selectors", [])
        
        if selectors:
            best = selectors[0]
            by_type = _get_by_type(best.get("selector_type", "css"))
            value = _get_selector_value(best)
            elements_text += f"- {elem_name} ({elem_type}): {by_type}, \"{value}\"\n"
    
    # Format methods
    methods_text = "\n".join(f"- {m}" for m in methods) if methods else "- Standard getters/setters for all elements"
    
    prompt = PAGE_GENERATION_PROMPT.format(
        page_name=page_name,
        file_name=file_name,
        elements=elements_text,
        methods=methods_text
    )
    
    system_prompt = """You are an expert Python developer specializing in Selenium test automation. 
Generate clean, well-documented code. **CRITICAL: Use Selenium WebDriver only. DO NOT use Playwright.**
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
        # Clean up again
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()
        
        if "playwright" in code.lower():
            logger.error(f"Still contains Playwright after retry")
    
    return code


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
    
    # Extract available methods from page objects using AST (more reliable than regex)
    available_methods_by_page = {}
    for page_name in pages:
        # Try to find the page object code
        page_file = f"pages/{page_name.lower()}_page.py"
        page_code = page_objects_code.get(page_file, "")
        if page_code:
            # Extract method names using AST
            methods_dict = extract_method_names(page_code)
            # Flatten methods from all classes in the file
            methods = []
            for class_name, class_methods in methods_dict.items():
                methods.extend(class_methods)
            available_methods_by_page[page_name] = methods
            logger.debug(f"Found {len(methods)} methods in {page_name} using AST: {methods[:5]}...")
    
    # Generate each test
    test_codes = []
    for test_plan in tests:
        test_id = test_plan.get("test_id", "")
        tc_data = tc_lookup.get(test_id, {})
        
        # Build available methods text (Option 2 + 3)
        pages_used = test_plan.get("pages_used", [])
        methods_text = ""
        for page_name in pages_used:
            methods = available_methods_by_page.get(page_name, [])
            if methods:
                methods_text += f"\n{page_name} methods: {', '.join(methods[:20])}"  # Limit to 20 methods
            else:
                # Fallback to standard methods (Option 2)
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
Generate pytest test functions using Selenium WebDriver. **CRITICAL: Use Selenium only. DO NOT use Playwright.**
Use ONLY the methods listed in the "AVAILABLE PAGE OBJECT METHODS" section."""
        
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
        
        test_codes.append(code.strip())
    
    # Combine into a test file
    imports = set()
    imports.add("import pytest")
    
    for page in pages:
        imports.add(f"from pages.{page.lower()} import {page}")
    
    header = "\n".join(sorted(imports)) + "\n\n"
    
    return header + "\n\n".join(test_codes)


def generation_node(state: AgentState) -> AgentState:
    """
    Generation node - generates all automation code with incremental verification.
    
    Stages:
    1. Base + Page Objects → Verify Stage 1
    2. Flows → Verify Stage 2
    3. Tests + Config → Verify Stage 3
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with generated files
    """
    logger.info("=" * 60)
    logger.info("GENERATION NODE (Multi-Stage)")
    logger.info("=" * 60)
    
    state["current_node"] = "generation"
    state["node_history"] = state.get("node_history", []) + ["generation"]
    
    plan = state.get("generation_plan", {})
    module_spec = state.get("module_spec", {})
    page_metadata = state.get("page_metadata", {})
    test_cases = state.get("test_cases", [])
    output_path = state.get("output_path", "")
    
    generated_files = state.get("generated_files", {}).copy()  # Preserve existing files
    errors = []
    
    # Check if we're re-verifying after recovery
    recovery_stage = state.get("recovery_stage", None)
    if recovery_stage and not state.get("needs_recovery", False):
        # Re-verify the specific stage after recovery
        logger.info(f"Re-verifying Stage {recovery_stage} after recovery...")
        from .verification.incremental import verify_page_objects, verify_flows, verify_tests
        
        if recovery_stage == 1:
            stage1_results = verify_page_objects(generated_files, output_path)
            state["incremental_verification_stage1"] = stage1_results.model_dump()
            if stage1_results.all_passed:
                state["recovery_stage"] = None
                state["needs_recovery"] = False
                logger.info("✓ Stage 1 re-verification passed - continuing to Stage 2")
                # Continue to Stage 2
            else:
                state["needs_recovery"] = True
                return state
        
        elif recovery_stage == 2:
            stage1_results_dict = state.get("incremental_verification_stage1", {})
            stage1_passed = stage1_results_dict.get("all_passed", False)
            stage2_results = verify_flows(generated_files, output_path, stage1_passed)
            state["incremental_verification_stage2"] = stage2_results.model_dump()
            if stage2_results.all_passed:
                state["recovery_stage"] = None
                state["needs_recovery"] = False
                logger.info("✓ Stage 2 re-verification passed - continuing to Stage 3")
                # Continue to Stage 3
            else:
                state["needs_recovery"] = True
                return state
        
        elif recovery_stage == 3:
            stage2_results_dict = state.get("incremental_verification_stage2", {})
            stage2_passed = stage2_results_dict.get("all_passed", False)
            stage3_results = verify_tests(generated_files, output_path, stage2_passed)
            state["incremental_verification_stage3"] = stage3_results.model_dump()
            if stage3_results.all_passed:
                state["recovery_stage"] = None
                state["needs_recovery"] = False
                state["generation_complete"] = True
                logger.info("✓ Stage 3 re-verification passed - generation complete")
                return state
            else:
                state["needs_recovery"] = True
                return state
    
    # Initialize LLM with reasoning enabled
    llm = BedrockClient(
        model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        region_name=state.get("llm_region", "us-east-2"),
        profile_name=state.get("llm_profile", "bedrock-user"),
        max_tokens=32768,
        enable_reasoning=True
    )
    
    module_name = module_spec.get("module_name", "test_module")
    base_url = module_spec.get("app_url", "")
    
    # Check which stages are already complete
    stage1_complete = state.get("incremental_verification_stage1", {}).get("all_passed", False)
    stage2_complete = state.get("incremental_verification_stage2", {}).get("all_passed", False)
    stage3_complete = state.get("incremental_verification_stage3", {}).get("all_passed", False)
    
    # ========================================================================
    # STAGE 1: Generate Base + Page Objects
    # ========================================================================
    if not stage1_complete:
        logger.info("=" * 60)
        logger.info("GENERATION STAGE 1: Base & Page Objects")
        logger.info("=" * 60)
        
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
                # Get metadata for this page
                page_meta_key = page_plan.get("page_metadata_key", page_name.lower())
                page_meta = page_metadata.get(page_meta_key, {})
                
                code = generate_page_class(page_plan, page_meta, llm)
                generated_files[file_name] = code
                page_objects_code[file_name] = code  # Store for test generation
                
                logger.info(f"  ✓ {file_name}")
            except Exception as e:
                logger.error(f"  ✗ Failed to generate {file_name}: {e}")
                errors.append(f"Failed to generate {file_name}: {e}")
        
        # Generate __init__.py for pages
        generated_files["pages/__init__.py"] = ""
        
        # INCREMENTAL VERIFICATION STAGE 1
        state["generated_files"] = generated_files.copy()
        state["current_generation_stage"] = 1
        state["node_history"] = state.get("node_history", []) + ["generation_stage1"]
        
        from .verification.incremental import verify_page_objects
        stage1_results = verify_page_objects(generated_files, output_path)
        
        state["incremental_verification_stage1"] = stage1_results.model_dump()
        
        # Update scratchpad
        scratchpad = state.get("scratchpad")
        if scratchpad:
            scratchpad.add_incremental_verification(1, stage1_results.model_dump())
            scratchpad.update_progress(state)
        
        if not stage1_results.all_passed:
            logger.warning("Stage 1 verification failed - triggering recovery")
            state["verification_passed"] = False
            state["needs_recovery"] = True
            state["recovery_stage"] = 1
            return state  # Return to trigger recovery
        
        logger.info("✓ Stage 1 verification passed - proceeding to flows")
    else:
        logger.info("Stage 1 already complete - skipping")
        # Get existing stage1 results
        stage1_results_dict = state.get("incremental_verification_stage1", {})
        from ..models.schemas import VerificationResults
        stage1_results = VerificationResults(**stage1_results_dict)
        # Get page objects code from existing files
        page_objects_code = {
            k: v for k, v in generated_files.items()
            if k.startswith("pages/") and k.endswith(".py")
        }
    
    # ========================================================================
    # STAGE 2: Generate Flows
    # ========================================================================
    if not stage2_complete:
        logger.info("=" * 60)
        logger.info("GENERATION STAGE 2: Flows")
        logger.info("=" * 60)
        
        # Generate Flow classes
        for flow_plan in plan.get("flows", []):
            flow_name = flow_plan.get("flow_name", "")
            file_name = flow_plan.get("file_name", f"flows/{flow_name.lower()}.py")
            
            logger.info(f"Generating {file_name}...")
            
            # Simple flow template
            pages_used = flow_plan.get("pages_used", [])
            imports = "\n".join(f"from pages.{p.lower()} import {p}" for p in pages_used)
            
            flow_code = f'''"""Flow class for {flow_name}."""
            
{imports}


class {flow_name}:
    """Helper class for {flow_plan.get('description', 'common flows')}."""
    
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        # Initialize page objects
        {chr(10).join(f'        self.{p.lower()} = {p}(driver, base_url)' for p in pages_used) if pages_used else 'pass'}
'''
            generated_files[file_name] = flow_code
            logger.info(f"  ✓ {file_name}")
        
        # Generate __init__.py for flows
        generated_files["flows/__init__.py"] = ""
        
        # INCREMENTAL VERIFICATION STAGE 2
        state["generated_files"] = generated_files.copy()
        state["current_generation_stage"] = 2
        state["node_history"] = state.get("node_history", []) + ["generation_stage2"]
        
        from .verification.incremental import verify_flows
        stage2_results = verify_flows(
            generated_files, 
            output_path,
            page_objects_verified=stage1_results.all_passed
        )
        
        state["incremental_verification_stage2"] = stage2_results.model_dump()
        
        # Update scratchpad
        scratchpad = state.get("scratchpad")
        if scratchpad:
            try:
                scratchpad.add_incremental_verification(2, stage2_results.model_dump())
                scratchpad.update_progress(state)
            except Exception as e:
                logger.warning(f"Failed to update scratchpad: {e}")
        
        if not stage2_results.all_passed:
            logger.warning("Stage 2 verification failed - triggering recovery")
            state["verification_passed"] = False
            state["needs_recovery"] = True
            state["recovery_stage"] = 2
            return state
        
        logger.info("✓ Stage 2 verification passed - proceeding to tests")
    else:
        logger.info("Stage 2 already complete - skipping")
        # Get existing stage2 results
        stage2_results_dict = state.get("incremental_verification_stage2", {})
        from ..models.schemas import VerificationResults
        stage2_results = VerificationResults(**stage2_results_dict)
    
    # ========================================================================
    # STAGE 3: Generate Tests + Config (in batches)
    # ========================================================================
    if not stage3_complete:
        logger.info("=" * 60)
        logger.info("GENERATION STAGE 3: Tests & Configuration")
        logger.info("=" * 60)
        
        # Get test batches from plan (planner should have organized tests into batches)
        test_batches = plan.get("test_batches", [])
        all_tests = plan.get("tests", [])
        
        # If no batches defined, create one batch with all tests (backward compatibility)
        if not test_batches and all_tests:
            test_batches = [all_tests]
            logger.info("No test batches in plan - using all tests as single batch")
        
        # Generate tests in batches
        test_files_generated = []
        for batch_idx, test_batch in enumerate(test_batches):
            if not test_batch:
                continue
                
            logger.info(f"Generating test batch {batch_idx + 1}/{len(test_batches)} ({len(test_batch)} tests)...")
            
            try:
                pages_used = list(set(
                    p for t in test_batch for p in t.get("pages_used", [])
                ))
                
                # Generate batch file name
                if len(test_batches) > 1:
                    batch_file = f"tests/test_{module_name}_batch{batch_idx + 1}.py"
                else:
                    batch_file = f"tests/test_{module_name}.py"
                
                test_code = generate_test_file(
                    tests=test_batch,
                    test_cases=test_cases,
                    pages=pages_used,
                    page_objects_code=page_objects_code,  # Pass page object code
                    llm=llm
                )
                generated_files[batch_file] = test_code
                test_files_generated.append(batch_file)
                logger.info(f"  ✓ {batch_file}")
                
                # Verify this batch before generating next
                state["generated_files"] = generated_files.copy()
                
                # Quick syntax check for this batch
                from .verification.checkpoint_a import checkpoint_a_syntax
                batch_files = {batch_file: test_code}
                syntax_check = checkpoint_a_syntax(batch_files)
                
                if syntax_check.status.value == "failed":
                    logger.warning(f"  ✗ Batch {batch_idx + 1} has syntax errors - will fix in recovery")
                    # Continue to next batch, recovery will handle
                
            except Exception as e:
                logger.error(f"Failed to generate test batch {batch_idx + 1}: {e}")
                errors.append(f"Failed to generate test batch {batch_idx + 1}: {e}")
        
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
            headless_default=str(headless_default).lower()
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
        generated_files["tests/__init__.py"] = ""
        
        # INCREMENTAL VERIFICATION STAGE 3
        state["generated_files"] = generated_files.copy()
        state["current_generation_stage"] = 3
        state["node_history"] = state.get("node_history", []) + ["generation_stage3"]
        
        from .verification.incremental import verify_tests
        stage3_results = verify_tests(
            generated_files,
            output_path,
            previous_stages_passed=stage2_results.all_passed
        )
        
        state["incremental_verification_stage3"] = stage3_results.model_dump()
        
        # Update scratchpad
        scratchpad = state.get("scratchpad")
        if scratchpad:
            try:
                scratchpad.add_incremental_verification(3, stage3_results.model_dump())
                scratchpad.update_progress(state)
            except Exception as e:
                logger.warning(f"Failed to update scratchpad: {e}")
        
        if not stage3_results.all_passed:
            logger.warning("Stage 3 verification failed - triggering recovery")
            state["verification_passed"] = False
            state["needs_recovery"] = True
            state["recovery_stage"] = 3
            return state
        
        logger.info("✓ Stage 3 verification passed - all code generated successfully")
    else:
        logger.info("Stage 3 already complete - skipping")
        # Get existing stage3 results
        stage3_results_dict = state.get("incremental_verification_stage3", {})
        from ..models.schemas import VerificationResults
        stage3_results = VerificationResults(**stage3_results_dict)
    
    # 7. Generate pages/__init__.py
    generated_files["pages/__init__.py"] = '"""Page Objects package."""\n'
    
    # 8. Generate tests/__init__.py  
    generated_files["tests/__init__.py"] = '"""Tests package."""\n'
    
    # 9. Generate flows/__init__.py (if flows exist)
    if plan.get("flows"):
        generated_files["flows/__init__.py"] = '"""Flow helpers package."""\n'
    
    # Update state
    state["generated_files"] = generated_files
    state["generation_errors"] = errors
    
    # Generate __init__.py for tests
    generated_files["tests/__init__.py"] = ""
    
    # INCREMENTAL VERIFICATION STAGE 3
    state["generated_files"] = generated_files.copy()
    state["current_generation_stage"] = 3
    state["node_history"] = state.get("node_history", []) + ["generation_stage3"]
    
    from .verification.incremental import verify_tests
    stage3_results = verify_tests(
        generated_files,
        output_path,
        previous_stages_passed=stage2_results.all_passed
    )
    
    state["incremental_verification_stage3"] = stage3_results.model_dump()
    
    # Update scratchpad
    if scratchpad:
        scratchpad.add_incremental_verification(3, stage3_results.model_dump())
        scratchpad.update_progress(state)
    
    if not stage3_results.all_passed:
        logger.warning("Stage 3 verification failed - triggering recovery")
        state["verification_passed"] = False
        state["needs_recovery"] = True
        state["recovery_stage"] = 3
        return state
    
        logger.info("✓ Stage 3 verification passed - all code generated successfully")
    else:
        logger.info("Stage 3 already complete - skipping")
        # Get existing stage3 results
        stage3_results_dict = state.get("incremental_verification_stage3", {})
        from ..models.schemas import VerificationResults
        stage3_results = VerificationResults(**stage3_results_dict)
    
    # Update LLM usage
    usage = llm.get_usage_stats()
    state["llm_calls"] = state.get("llm_calls", 0) + usage["call_count"]
    state["llm_input_tokens"] = state.get("llm_input_tokens", 0) + usage["total_input_tokens"]
    state["llm_output_tokens"] = state.get("llm_output_tokens", 0) + usage["total_output_tokens"]
    
    # Log summary
    logger.info("-" * 40)
    logger.info("GENERATION SUMMARY")
    logger.info(f"  Files generated: {len(generated_files)}")
    logger.info(f"  Errors: {len(errors)}")
    logger.info(f"  LLM calls: {usage['call_count']}")
    logger.info(f"  LLM tokens: {usage['total_tokens']}")
    logger.info(f"  Stage 1: {'✅' if stage1_results.all_passed else '❌'}")
    logger.info(f"  Stage 2: {'✅' if stage2_results.all_passed else '❌'}")
    logger.info(f"  Stage 3: {'✅' if stage3_results.all_passed else '❌'}")
    logger.info("-" * 40)
    
    for filepath in generated_files.keys():
        logger.info(f"  ✓ {filepath}")
    
    # Mark generation as complete
    state["generation_complete"] = True
    state["verification_passed"] = stage3_results.all_passed
    
    return state
