"""Planning Node - LLM creates code generation plan.

This node:
1. Analyzes test cases and element metadata
2. Groups tests by page/flow
3. Creates a GenerationPlan with file structure
4. Identifies shared utilities and fixtures

Supports multiple platforms:
- Web (Selenium)
- Android (Appium)
"""

import json
import logging
import re
from typing import Dict, List, Any

from ..models.state import AgentState
from ..models.schemas import GenerationPlan, PagePlan, FlowPlan, TestPlan
from ..llm.bedrock_client import BedrockClient
from ..templates import is_mobile_platform

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


# Base planning system prompt (common structure)
PLANNING_SYSTEM_PROMPT_BASE = """You are an expert test automation architect. Your task is to analyze manual test cases and UI element metadata, then create a comprehensive code generation plan.

OUTPUT FORMAT:
Return a JSON object with this structure:
{
    "module_name": "string - module being tested",
    "pages": [
        {
            "page_name": "LoginPage",
            "file_name": "pages/login_page.py",
            "elements": ["username_input", "password_input", "login_button"],
            "methods": [
                {"name": "enter_username", "params": ["text: str"], "returns": "self", "description": "Enter username in input field"},
                {"name": "enter_password", "params": ["text: str"], "returns": "self", "description": "Enter password in input field"},
                {"name": "click_login", "params": [], "returns": "self", "description": "Click the login button"},
                {"name": "get_error_message", "params": [], "returns": "str", "description": "Get error message text if displayed"},
                {"name": "is_error_displayed", "params": [], "returns": "bool", "description": "Check if error message is visible"}
            ],
            "inherits_from": "BasePage",
            "description": "Page object for login page"
        }
    ],
    "flows": [
        {
            "flow_name": "AuthFlow",
            "file_name": "flows/auth_flow.py",
            "pages_used": ["LoginPage"],
            "methods": ["login", "login_invalid", "logout"],
            "description": "Authentication flow helpers"
        }
    ],
    "tests": [
        {
            "test_id": "TC_LOGIN_001",
            "test_name": "test_valid_login",
            "flow_used": "AuthFlow",
            "pages_used": ["LoginPage", "ProductsPage"],
            "steps_summary": ["Navigate to login", "Enter credentials", "Verify redirect"],
            "method_calls": [
                {"page": "LoginPage", "method": "enter_username", "args": ["standard_user"]},
                {"page": "LoginPage", "method": "enter_password", "args": ["secret_sauce"]},
                {"page": "LoginPage", "method": "click_login", "args": []}
            ],
            "markers": ["smoke", "login"],
            "description": "Test valid login with correct credentials"
        }
    ],
    "conftest_fixtures": ["driver", "base_url", "login_user"]
}

CRITICAL - METHOD CONTRACTS:
The "methods" field in pages MUST use the detailed format with name/params/returns/description.
This ensures both page generation AND test generation use the EXACT SAME method names.

The "method_calls" field in tests specifies which page methods each test will call.
This creates a contract between pages and tests to prevent method name mismatches.

GUIDELINES:
1. Create one Page Object class per unique page
2. Group related actions into Flow classes
3. Each test case maps to one test function
4. Use pytest markers from test case tags
5. Include all elements referenced in test steps
6. Generate helper methods for common interactions
7. Follow Python naming conventions (snake_case)
8. Method names MUST be consistent across pages and tests"""


# Web/Selenium specific guidelines
PLANNING_SYSTEM_PROMPT_WEB = PLANNING_SYSTEM_PROMPT_BASE + """

PLATFORM: Web (Selenium)
- Use Selenium WebDriver for browser automation
- Page objects should inherit from BasePage
- Constructor signature: __init__(self, driver, base_url)
- Use methods like enter_text(), click(), find_element_visible()
- Default fixtures: driver, base_url

AVAILABLE BASEPAGE METHODS (use these in your method_calls):
- navigate(path="") -> None
- find_element(by, value) -> WebElement
- find_element_clickable(by, value) -> WebElement
- find_element_visible(by, value) -> WebElement
- is_element_present(by, value, timeout=5) -> bool
- get_element_text(by, value) -> str
- enter_text(by, value, text) -> None
- click(by, value) -> None

IMPORTANT: DO NOT use wait_for_* methods - they don't exist! Use find_* methods instead."""


# Android/Appium specific guidelines
PLANNING_SYSTEM_PROMPT_ANDROID = PLANNING_SYSTEM_PROMPT_BASE + """

PLATFORM: Android (Appium)
- Use Appium with UiAutomator2 for Android automation
- Page objects should inherit from BasePage
- Constructor signature: __init__(self, driver)  # NO base_url for mobile
- Use AppiumBy locators: ACCESSIBILITY_ID, ID, XPATH (NO CSS selectors)
- Use mobile methods like tap(), swipe_up(), hide_keyboard()
- Call hide_keyboard() after text input
- Default fixtures: driver, appium_server
- Use "Screen" suffix for page names (e.g., LoginScreen instead of LoginPage)

AVAILABLE BASEPAGE METHODS (use these in your method_calls):
- find_element(by, value) -> WebElement
- find_element_clickable(by, value) -> WebElement
- find_element_visible(by, value) -> WebElement
- is_element_present(by, value, timeout=5) -> bool
- get_element_text(by, value) -> str
- tap(by, value) -> None
- click(by, value) -> None (alias for tap)
- enter_text(by, value, text) -> None
- clear_text(by, value) -> None
- hide_keyboard() -> None
- swipe_up(percent=0.5) -> None
- swipe_down(percent=0.5) -> None
- scroll_to_element(by, value, max_swipes=5) -> Optional[WebElement]

MOBILE-SPECIFIC GUIDELINES:
1. NO CSS selectors - use accessibility_id, id, or xpath only
2. Add hide_keyboard() calls after text input methods
3. Use tap() instead of click() for buttons
4. Consider swipe gestures for scrolling content
5. Page objects don't need base_url parameter
6. DO NOT use wait_for_* methods - they don't exist! Use find_* methods instead."""


def _get_planning_system_prompt(platform_type: str) -> str:
    """Get platform-specific planning system prompt.

    Args:
        platform_type: 'web' or 'android'

    Returns:
        Planning system prompt string
    """
    if is_mobile_platform(platform_type):
        return PLANNING_SYSTEM_PROMPT_ANDROID
    return PLANNING_SYSTEM_PROMPT_WEB


# Backward compatibility alias
PLANNING_SYSTEM_PROMPT = PLANNING_SYSTEM_PROMPT_WEB


MAX_TEST_CASES_PER_BATCH = 10  # Limit test cases to keep LLM responses fast and accurate


def _build_planning_prompt(state: AgentState) -> str:
    """
    Build the prompt for planning.

    Args:
        state: Current agent state

    Returns:
        Planning prompt string
    """
    module_spec = state.get("module_spec", {})
    all_test_cases = state.get("test_cases", [])
    page_metadata = state.get("page_metadata", {})

    # Get platform type
    platform_type = state.get("platform_type", module_spec.get("platform_type", "web"))
    is_mobile = is_mobile_platform(platform_type)

    # Limit test cases to keep responses manageable
    test_cases = all_test_cases[:MAX_TEST_CASES_PER_BATCH]
    if len(all_test_cases) > MAX_TEST_CASES_PER_BATCH:
        logger.info(f"Limiting to {MAX_TEST_CASES_PER_BATCH} test cases (of {len(all_test_cases)} total)")

    # Format module info - platform-aware
    if is_mobile:
        android_config = module_spec.get("android_config", {})
        module_info = f"""
## Module Information
- Name: {module_spec.get('module_name', 'unknown')}
- App: {module_spec.get('app_name', 'unknown')}
- Platform: Android (Appium)
- App Package: {android_config.get('app_package', 'unknown')}
- App Activity: {android_config.get('app_activity', 'unknown')}
- Device: {android_config.get('device_name', 'Android Emulator')}
- Automation: {android_config.get('automation_name', 'UiAutomator2')}
"""
    else:
        module_info = f"""
## Module Information
- Name: {module_spec.get('module_name', 'unknown')}
- App: {module_spec.get('app_name', 'unknown')}
- Platform: Web (Selenium)
- URL: {module_spec.get('app_url', 'unknown')}
- Browser: {module_spec.get('browser', 'chrome')}
"""
    
    # Format pages and elements (limit to key elements)
    MAX_ELEMENTS_PER_PAGE = 15
    pages_info = "\n## Pages and Elements\n"
    for page_name, page in page_metadata.items():
        pages_info += f"\n### {page_name}\n"
        pages_info += f"URL: {page.get('page_url', 'N/A')}\n"
        pages_info += "Elements:\n"
        
        elements = page.get("elements", [])
        # Prioritize required elements and inputs/buttons
        priority_elements = [e for e in elements if e.get("is_required") or e.get("element_type") in ("input", "button")]
        other_elements = [e for e in elements if e not in priority_elements]
        limited_elements = (priority_elements + other_elements)[:MAX_ELEMENTS_PER_PAGE]
        
        for elem in limited_elements:
            elem_name = elem.get("name", "unknown")
            elem_type = elem.get("element_type", "element")
            selectors = elem.get("selectors", [])
            best_selector = selectors[0] if selectors else {}
            
            pages_info += f"  - {elem_name} ({elem_type})"
            if best_selector:
                pages_info += f" [{best_selector.get('selector_type', 'N/A')}='{best_selector.get('value', 'N/A')}']"
            pages_info += "\n"
        
        if len(elements) > MAX_ELEMENTS_PER_PAGE:
            pages_info += f"  ... and {len(elements) - MAX_ELEMENTS_PER_PAGE} more elements\n"
    
    # Format test cases
    tests_info = "\n## Test Cases\n"
    for tc in test_cases:
        tests_info += f"\n### {tc.get('test_id', 'N/A')}: {tc.get('test_name', 'N/A')}\n"
        tests_info += f"Priority: {tc.get('priority', 'N/A')}\n"
        tests_info += f"Page: {tc.get('page_name', 'N/A')}\n"
        tests_info += f"Tags: {tc.get('tags', 'N/A')}\n"
        tests_info += f"Preconditions: {tc.get('preconditions', 'None')}\n"
        tests_info += f"Steps: {tc.get('steps', 'N/A')}\n"
        tests_info += f"Expected: {tc.get('expected_result', 'N/A')}\n"
    
    prompt = f"""Create a code generation plan for the following test automation module.

{module_info}

{pages_info}

{tests_info}

Generate a comprehensive plan that includes:
1. Page Object classes for each unique page
2. Flow classes for grouped actions
3. Test functions for each test case
4. Conftest fixtures needed

Return ONLY valid JSON matching the specified format."""
    
    return prompt


def planning_node(state: AgentState) -> AgentState:
    """
    Planning node - creates code generation plan using LLM.

    Supports multiple platforms:
    - Web (Selenium)
    - Android (Appium)

    Args:
        state: Current agent state

    Returns:
        Updated state with generation plan
    """
    logger.info("=" * 60)
    logger.info("PLANNING NODE")
    logger.info("=" * 60)

    state["current_node"] = "planning"
    state["node_history"] = state.get("node_history", []) + ["planning"]

    # Get platform type
    module_spec = state.get("module_spec", {})
    platform_type = state.get("platform_type", module_spec.get("platform_type", "web"))

    logger.info(f"Platform: {platform_type}")

    # Build the planning prompt
    prompt = _build_planning_prompt(state)
    state["planning_prompt"] = prompt

    logger.info("Building generation plan with LLM...")

    # Initialize LLM client with high token limit for quality
    llm = BedrockClient(
        model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        region_name=state.get("llm_region", "us-east-2"),
        profile_name=state.get("llm_profile", "bedrock-user"),
        max_tokens=16384
    )

    # Get platform-specific system prompt
    system_prompt = _get_planning_system_prompt(platform_type)

    try:
        # Call LLM with platform-specific prompt
        response = llm.chat(
            user_message=prompt,
            system=system_prompt
        )
        
        state["planning_response"] = response
        
        # Parse JSON response
        # Clean up response - extract JSON
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        text = text.strip()
        
        plan_dict = json.loads(text)
        
        # Validate and store plan
        state["generation_plan"] = plan_dict
        
        # Update LLM usage
        usage = llm.get_usage_stats()
        state["llm_calls"] = state.get("llm_calls", 0) + usage["call_count"]
        state["llm_input_tokens"] = state.get("llm_input_tokens", 0) + usage["total_input_tokens"]
        state["llm_output_tokens"] = state.get("llm_output_tokens", 0) + usage["total_output_tokens"]
        
        # Log summary
        logger.info("-" * 40)
        logger.info("PLANNING SUMMARY")
        logger.info(f"  Pages: {len(plan_dict.get('pages', []))}")
        logger.info(f"  Flows: {len(plan_dict.get('flows', []))}")
        logger.info(f"  Tests: {len(plan_dict.get('tests', []))}")
        logger.info(f"  Fixtures: {len(plan_dict.get('conftest_fixtures', []))}")
        logger.info(f"  LLM tokens: {usage['total_tokens']}")
        logger.info("-" * 40)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        state["errors"] = state.get("errors", []) + [f"Planning failed: Invalid JSON response"]
        state["generation_plan"] = {}
    except Exception as e:
        logger.error(f"Planning failed: {e}")
        state["errors"] = state.get("errors", []) + [f"Planning failed: {e}"]
        state["generation_plan"] = {}
    
    return state


def create_default_plan(state: AgentState) -> Dict[str, Any]:
    """
    Create a default plan when LLM planning fails.
    
    Uses simple heuristics based on input data.
    
    Args:
        state: Current agent state
        
    Returns:
        Default generation plan dict
    """
    module_spec = state.get("module_spec", {})
    test_cases = state.get("test_cases", [])
    page_metadata = state.get("page_metadata", {})
    
    module_name = module_spec.get("module_name", "test_module")
    
    # Create page plans
    pages = []
    for page_name, page in page_metadata.items():
        elements = [e.get("name") for e in page.get("elements", [])]
        methods = []
        
        for elem in page.get("elements", []):
            elem_name = elem.get("name", "")
            elem_type = elem.get("element_type", "")
            
            if elem_type == "input":
                methods.append(f"enter_{elem_name}")
            elif elem_type == "button":
                methods.append(f"click_{elem_name}")
            elif elem_type == "link":
                methods.append(f"click_{elem_name}")
        
        pages.append({
            "page_name": page_name,
            "file_name": f"pages/{_camel_to_snake(page_name)}.py",
            "elements": elements,
            "methods": methods,
            "inherits_from": "BasePage",
            "description": f"Page object for {page_name}"
        })
    
    # Create test plans
    tests = []
    for tc in test_cases:
        test_id = tc.get("test_id", "")
        test_name = f"test_{test_id.lower().replace('-', '_')}"
        tags = tc.get("tags", "")
        markers = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        
        tests.append({
            "test_id": test_id,
            "test_name": test_name,
            "flow_used": None,
            "pages_used": [tc.get("page_name")] if tc.get("page_name") else [],
            "steps_summary": tc.get("steps", "").split("|") if tc.get("steps") else [],
            "markers": markers,
            "description": tc.get("test_name", "")
        })
    
    return {
        "module_name": module_name,
        "pages": pages,
        "flows": [],
        "tests": tests,
        "conftest_fixtures": ["driver", "base_url"]
    }
