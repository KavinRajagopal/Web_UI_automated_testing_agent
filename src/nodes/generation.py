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
from typing import Dict, List, Any

from ..models.state import AgentState
from ..llm.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


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

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return "{base_url}"


@pytest.fixture(scope="function")
def driver():
    """Chrome WebDriver fixture."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    
    yield driver
    
    driver.quit()


{additional_fixtures}
'''

PYTEST_INI_TEMPLATE = '''[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
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

REQUIREMENTS:
1. Import BasePage and By from selenium
2. Define element locators as class attributes using tuples: (By.X, "value")
3. Create getter/setter methods for each element
4. Create action methods as specified
5. Use the best selector (data-test, id, name, aria-label)
6. Add docstrings to all methods
7. Handle waits properly using BasePage methods

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

REQUIREMENTS:
1. Use pytest fixtures (driver, base_url)
2. Import necessary page objects
3. Add pytest markers: {markers}
4. Add clear docstring with test description
5. Include assertions for expected results
6. Handle setup and teardown if needed

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
    
    response = llm.chat(
        user_message=prompt,
        system="You are an expert Python developer specializing in Selenium test automation. Generate clean, well-documented code."
    )
    
    # Clean up response
    code = response.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    
    return code.strip()


def generate_test_file(
    tests: List[Dict[str, Any]],
    test_cases: List[Dict[str, Any]],
    pages: List[str],
    llm: BedrockClient
) -> str:
    """
    Generate a test file with multiple test functions.
    
    Args:
        tests: List of test plans
        test_cases: Original test case data
        pages: Available page classes
        llm: Bedrock client
        
    Returns:
        Generated Python code
    """
    # Build test case lookup
    tc_lookup = {tc.get("test_id"): tc for tc in test_cases}
    
    # Generate each test
    test_codes = []
    for test_plan in tests:
        test_id = test_plan.get("test_id", "")
        tc_data = tc_lookup.get(test_id, {})
        
        prompt = TEST_GENERATION_PROMPT.format(
            test_id=test_id,
            test_name=test_plan.get("test_name", "test_unnamed"),
            description=test_plan.get("description", ""),
            steps="\n".join(test_plan.get("steps_summary", [])),
            expected=tc_data.get("expected_result", "Test passes"),
            pages_used=", ".join(test_plan.get("pages_used", [])),
            markers=", ".join(test_plan.get("markers", [])),
            test_data=tc_data.get("test_data", "")
        )
        
        response = llm.chat(
            user_message=prompt,
            system="You are an expert Python developer. Generate a single pytest test function."
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
    Generation node - generates all automation code.
    
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
    
    plan = state.get("generation_plan", {})
    module_spec = state.get("module_spec", {})
    page_metadata = state.get("page_metadata", {})
    test_cases = state.get("test_cases", [])
    
    generated_files = {}
    errors = []
    
    # Initialize LLM
    llm = BedrockClient(
        model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        region_name=state.get("llm_region", "us-east-2"),
        profile_name=state.get("llm_profile", "bedrock-user"),
        max_tokens=32768
    )
    
    module_name = module_spec.get("module_name", "test_module")
    base_url = module_spec.get("app_url", "")
    
    # 1. Generate base_page.py
    logger.info("Generating base_page.py...")
    generated_files["pages/base_page.py"] = BASE_PAGE_TEMPLATE
    
    # 2. Generate Page Objects
    for page_plan in plan.get("pages", []):
        page_name = page_plan.get("page_name", "")
        file_name = page_plan.get("file_name", f"pages/{page_name.lower()}.py")
        
        logger.info(f"Generating {file_name}...")
        
        try:
            # Get metadata for this page
            page_meta = page_metadata.get(page_name, {})
            
            code = generate_page_class(page_plan, page_meta, llm)
            generated_files[file_name] = code
            
        except Exception as e:
            logger.error(f"Failed to generate {file_name}: {e}")
            errors.append(f"Failed to generate {file_name}: {e}")
    
    # 3. Generate Flow classes (if any)
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
    
    # 4. Generate test files
    tests = plan.get("tests", [])
    if tests:
        logger.info("Generating test file...")
        
        try:
            pages_used = list(set(
                p for t in tests for p in t.get("pages_used", [])
            ))
            
            test_code = generate_test_file(tests, test_cases, pages_used, llm)
            generated_files[f"tests/test_{module_name}.py"] = test_code
            
        except Exception as e:
            logger.error(f"Failed to generate tests: {e}")
            errors.append(f"Failed to generate tests: {e}")
    
    # 5. Generate conftest.py
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
    
    conftest = CONFTEST_TEMPLATE.format(
        module_name=module_name,
        base_url=base_url,
        additional_fixtures=additional_fixtures
    )
    generated_files["tests/conftest.py"] = conftest
    
    # 6. Generate pytest.ini
    logger.info("Generating pytest.ini...")
    
    markers = set()
    for test in tests:
        markers.update(test.get("markers", []))
    
    additional_markers = "\n    ".join(f"{m}: {m} tests" for m in markers)
    
    pytest_ini = PYTEST_INI_TEMPLATE.format(additional_markers=additional_markers)
    generated_files["pytest.ini"] = pytest_ini
    
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
    logger.info("-" * 40)
    
    for filepath in generated_files.keys():
        logger.info(f"  ✓ {filepath}")
    
    return state
