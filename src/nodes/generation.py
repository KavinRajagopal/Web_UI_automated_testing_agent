"""Generation Node - Generates automation code from the plan.

This node generates:
1. Base classes (BasePage)
2. Page Object classes
3. Flow/Action helper classes
4. Pytest test files
5. conftest.py with fixtures
6. pytest.ini configuration

Supports multiple platforms through the Template Factory pattern:
- Web (Selenium)
- Android (Appium)
"""

import json
import logging
import os
import re
from typing import Dict, List, Any

from ..models.state import AgentState
from ..llm.bedrock_client import BedrockClient
from ..templates import get_templates, BaseTemplates, is_mobile_platform

logger = logging.getLogger(__name__)


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.

    Args:
        name: CamelCase string (e.g., 'ProductsScreen')

    Returns:
        snake_case string (e.g., 'products_screen')
    """
    # Insert underscore before uppercase letters and lowercase everything
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


# =============================================================================
# CODE TEMPLATES - Now loaded from src/templates/ via Template Factory
# =============================================================================
# Templates are platform-specific and loaded via get_templates(platform_type)
# See: src/templates/web_templates.py, src/templates/android_templates.py

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


# =============================================================================
# CODE GENERATION FUNCTIONS
# =============================================================================

def _get_by_type(selector_type: str, templates: BaseTemplates) -> str:
    """Convert selector type to platform-specific By type.

    Args:
        selector_type: Selector type (e.g., 'id', 'accessibility_id')
        templates: Platform-specific templates instance

    Returns:
        Platform-specific By type string (e.g., 'By.ID', 'AppiumBy.ACCESSIBILITY_ID')
    """
    return templates.get_by_type(selector_type)


def _get_selector_value(selector: Dict[str, Any], templates: BaseTemplates) -> str:
    """Get the selector value, transformed for the platform if needed.

    Args:
        selector: Dict with 'selector_type' and 'value' keys
        templates: Platform-specific templates instance

    Returns:
        Transformed selector value
    """
    return templates.get_selector_value(selector)


def generate_page_class(
    page_plan: Dict[str, Any],
    page_metadata: Dict[str, Any],
    llm: BedrockClient,
    templates: BaseTemplates
) -> str:
    """
    Generate a Page Object class using LLM.

    Args:
        page_plan: Plan for this page
        page_metadata: Element metadata for this page
        llm: Bedrock client
        templates: Platform-specific templates instance

    Returns:
        Generated Python code
    """
    page_name = page_plan.get("page_name", "Page")
    file_name = page_plan.get("file_name", "page.py")
    methods = page_plan.get("methods", [])

    # Format elements using platform-specific locator types
    elements_text = ""
    for elem in page_metadata.get("elements", []):
        elem_name = elem.get("name", "unknown")
        elem_type = elem.get("element_type", "element")
        selectors = elem.get("selectors", [])

        if selectors:
            best = selectors[0]
            by_type = _get_by_type(best.get("selector_type", "css"), templates)
            value = _get_selector_value(best, templates)
            elements_text += f"- {elem_name} ({elem_type}): {by_type}, \"{value}\"\n"

    # Format methods
    methods_text = "\n".join(f"- {m}" for m in methods) if methods else "- Standard getters/setters for all elements"

    # Use platform-specific prompt
    prompt = templates.PAGE_GENERATION_PROMPT.format(
        page_name=page_name,
        file_name=file_name,
        elements=elements_text,
        methods=methods_text
    )

    # Platform-specific system message
    platform = templates.platform_name
    if platform == "android":
        system_msg = "You are an expert Python developer specializing in Appium mobile test automation. Generate clean, well-documented code for Android testing."
    else:
        system_msg = "You are an expert Python developer specializing in Selenium test automation. Generate clean, well-documented code."

    response = llm.chat(
        user_message=prompt,
        system=system_msg
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
    llm: BedrockClient,
    templates: BaseTemplates,
    page_code_context: Dict[str, str] = None
) -> str:
    """
    Generate a test file with multiple test functions.

    Args:
        tests: List of test plans
        test_cases: Original test case data
        pages: Available page classes
        llm: Bedrock client
        templates: Platform-specific templates instance
        page_code_context: Dict mapping page class names to their generated code
                          This allows the LLM to see actual method signatures

    Returns:
        Generated Python code
    """
    if page_code_context is None:
        page_code_context = {}
    # Build test case lookup
    tc_lookup = {tc.get("test_id"): tc for tc in test_cases}

    # Platform-specific system message
    platform = templates.platform_name
    if platform == "android":
        system_msg = "You are an expert Python developer specializing in Appium mobile testing. Generate a single pytest test function for Android."
    else:
        system_msg = "You are an expert Python developer. Generate a single pytest test function."

    # Build page code context string for the prompt
    page_context_str = ""
    if page_code_context:
        page_context_str = "\n\n".join([
            f"# {page_name}:\n```python\n{code}\n```"
            for page_name, code in page_code_context.items()
        ])

    # Generate each test using platform-specific prompt
    test_codes = []
    for test_plan in tests:
        test_id = test_plan.get("test_id", "")
        tc_data = tc_lookup.get(test_id, {})

        # Get pages used by this test for context
        test_pages_used = test_plan.get("pages_used", [])

        # Build test-specific page context (only pages used by this test)
        test_page_context = ""
        if page_code_context:
            relevant_pages = {
                name: code for name, code in page_code_context.items()
                if name in test_pages_used
            }
            if relevant_pages:
                test_page_context = "\n\n".join([
                    f"# {page_name}:\n```python\n{code}\n```"
                    for page_name, code in relevant_pages.items()
                ])

        # Format the prompt with page context
        prompt = templates.TEST_GENERATION_PROMPT.format(
            test_id=test_id,
            test_name=test_plan.get("test_name", "test_unnamed"),
            description=test_plan.get("description", ""),
            steps="\n".join(test_plan.get("steps_summary", [])),
            expected=tc_data.get("expected_result", "Test passes"),
            pages_used=", ".join(test_pages_used),
            markers=", ".join(test_plan.get("markers", [])),
            test_data=tc_data.get("test_data", ""),
            page_code_context=test_page_context if test_page_context else "No page code available"
        )

        response = llm.chat(
            user_message=prompt,
            system=system_msg
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
        # Convert CamelCase page name to snake_case for module import
        # e.g., ProductsScreen -> products_screen
        module_name = _camel_to_snake(page)
        imports.add(f"from pages.{module_name} import {page}")

    header = "\n".join(sorted(imports)) + "\n\n"

    # Strip any import statements from LLM-generated test code to avoid duplicates
    cleaned_test_codes = []
    for code in test_codes:
        # Remove import lines at the start of each test code block
        lines = code.split('\n')
        non_import_lines = []
        past_imports = False
        for line in lines:
            # Skip import lines and empty lines before the first non-import
            if not past_imports:
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    continue
                if stripped == '':
                    continue
                past_imports = True
            non_import_lines.append(line)
        cleaned_test_codes.append('\n'.join(non_import_lines))

    return header + "\n\n".join(cleaned_test_codes)


def generation_node(state: AgentState) -> AgentState:
    """
    Generation node - generates all automation code.

    Supports multiple platforms through the Template Factory pattern:
    - Web (Selenium)
    - Android (Appium)

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

    # Get platform type and load appropriate templates
    platform_type = state.get("platform_type", module_spec.get("platform_type", "web"))
    templates = get_templates(platform_type)
    is_mobile = is_mobile_platform(platform_type)

    logger.info(f"Platform: {templates.platform_name}")

    # Initialize LLM
    llm = BedrockClient(
        model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        region_name=state.get("llm_region", "us-east-2"),
        profile_name=state.get("llm_profile", "bedrock-user"),
        max_tokens=32768
    )

    module_name = module_spec.get("module_name", "test_module")
    base_url = module_spec.get("app_url", "")

    # 1. Generate base_page.py (platform-specific)
    logger.info(f"Generating base_page.py ({templates.platform_name})...")
    generated_files["pages/base_page.py"] = templates.BASE_PAGE_TEMPLATE

    # 2. Generate Page Objects
    for page_plan in plan.get("pages", []):
        page_name = page_plan.get("page_name", "")
        # Use snake_case for file names (e.g., ProductsScreen -> products_screen.py)
        file_name = page_plan.get("file_name", f"pages/{_camel_to_snake(page_name)}.py")

        logger.info(f"Generating {file_name}...")

        try:
            # Get metadata for this page
            page_meta = page_metadata.get(page_name, {})

            code = generate_page_class(page_plan, page_meta, llm, templates)
            generated_files[file_name] = code

        except Exception as e:
            logger.error(f"Failed to generate {file_name}: {e}")
            errors.append(f"Failed to generate {file_name}: {e}")

    # 3. Generate Flow classes (if any)
    for flow_plan in plan.get("flows", []):
        flow_name = flow_plan.get("flow_name", "")
        # Use snake_case for file names (e.g., LoginFlow -> login_flow.py)
        file_name = flow_plan.get("file_name", f"flows/{_camel_to_snake(flow_name)}.py")

        logger.info(f"Generating {file_name}...")

        # Simple flow template (platform-aware initialization)
        pages_used = flow_plan.get("pages_used", [])
        # Use snake_case for module imports
        imports = "\n".join(f"from pages.{_camel_to_snake(p)} import {p}" for p in pages_used)

        # Mobile pages don't take base_url
        if is_mobile:
            init_params = "driver"
            page_init = "\n        ".join(f"self.{p.lower()} = {p}(driver)" for p in pages_used) if pages_used else "pass"
            flow_code = f'''"""Flow class for {flow_name}."""

{imports}


class {flow_name}:
    """Helper class for {flow_plan.get('description', 'common flows')}."""

    def __init__(self, driver):
        self.driver = driver
        # Initialize page objects
        {page_init}
'''
        else:
            init_params = "driver, base_url"
            page_init = "\n        ".join(f"self.{p.lower()} = {p}(driver, base_url)" for p in pages_used) if pages_used else "pass"
            flow_code = f'''"""Flow class for {flow_name}."""

{imports}


class {flow_name}:
    """Helper class for {flow_plan.get('description', 'common flows')}."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        # Initialize page objects
        {page_init}
'''
        generated_files[file_name] = flow_code

    # 4. Generate test files WITH page context
    tests = plan.get("tests", [])
    if tests:
        logger.info("Generating test file...")

        try:
            pages_used = list(set(
                p for t in tests for p in t.get("pages_used", [])
            ))

            # NEW: Collect generated page object code for context
            # This helps the LLM use only existing methods
            page_code_context = {}
            for page_name in pages_used:
                page_file = f"pages/{_camel_to_snake(page_name)}.py"
                if page_file in generated_files:
                    page_code_context[page_name] = generated_files[page_file]
                    logger.debug(f"  Including page context for {page_name}")

            logger.info(f"  Passing {len(page_code_context)} page objects as context to test generation")

            test_code = generate_test_file(
                tests, test_cases, pages_used, llm, templates,
                page_code_context=page_code_context  # NEW PARAMETER
            )
            generated_files[f"tests/test_{module_name}.py"] = test_code

        except Exception as e:
            logger.error(f"Failed to generate tests: {e}")
            errors.append(f"Failed to generate tests: {e}")

    # 5. Generate conftest.py (platform-specific)
    logger.info(f"Generating conftest.py ({templates.platform_name})...")

    fixtures = plan.get("conftest_fixtures", [])
    additional_fixtures = ""

    # Add login fixture if needed (platform-aware)
    if "login_user" in fixtures:
        if is_mobile:
            additional_fixtures += '''
@pytest.fixture(scope="function")
def login_user(driver):
    """Login with test user credentials."""
    from pages.loginscreen import LoginScreen
    login_screen = LoginScreen(driver)
    login_screen.enter_username("standard_user")
    login_screen.enter_password("secret_sauce")
    login_screen.tap_login()
    login_screen.hide_keyboard()
    return driver
'''
        else:
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

    # Generate conftest using platform-specific template
    if is_mobile:
        # Android conftest needs android_config parameters
        android_config = module_spec.get("android_config", {})
        conftest = templates.CONFTEST_TEMPLATE.format(
            module_name=module_name,
            app_package=android_config.get("app_package", "com.example.app"),
            app_activity=android_config.get("app_activity", ".MainActivity"),
            device_name=android_config.get("device_name", "Android Emulator"),
            automation_name=android_config.get("automation_name", "UiAutomator2"),
            platform_version=android_config.get("platform_version", "") or "",
            app_path=android_config.get("app_path", "") or "",
            no_reset=str(android_config.get("no_reset", True)),
            additional_fixtures=additional_fixtures
        )
    else:
        # Web conftest
        conftest = templates.CONFTEST_TEMPLATE.format(
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
