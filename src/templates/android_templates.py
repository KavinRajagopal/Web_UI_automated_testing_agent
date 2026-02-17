"""Android/Appium templates for mobile test generation.

This module contains all templates and prompts for generating
Appium-based Android automation code.
"""

from typing import Dict
from .base_templates import BaseTemplates


class AndroidTemplates(BaseTemplates):
    """Appium templates for Android mobile automation."""

    @property
    def platform_name(self) -> str:
        return "android"

    @property
    def BASE_PAGE_TEMPLATE(self) -> str:
        return '''"""Base Page Object class for Android mobile automation."""

import os
from typing import Tuple, Optional

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class BasePage:
    """Base class for all Android Page Objects.

    Provides common mobile automation methods including:
    - Element finding with explicit waits
    - Tap, long press, swipe gestures
    - Keyboard handling
    - Activity/package checks
    """

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    # =========================================================================
    # ELEMENT FINDING
    # =========================================================================

    def find_element(self, by: AppiumBy, value: str) -> WebElement:
        """Find an element with explicit wait."""
        return self.wait.until(
            EC.presence_of_element_located((by, value))
        )

    def find_element_clickable(self, by: AppiumBy, value: str) -> WebElement:
        """Find a clickable element with explicit wait."""
        return self.wait.until(
            EC.element_to_be_clickable((by, value))
        )

    def find_element_visible(self, by: AppiumBy, value: str) -> WebElement:
        """Find a visible element with explicit wait."""
        return self.wait.until(
            EC.visibility_of_element_located((by, value))
        )

    def is_element_present(self, by: AppiumBy, value: str, timeout: int = 5) -> bool:
        """Check if an element is present."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def get_element_text(self, by: AppiumBy, value: str) -> str:
        """Get text from an element."""
        element = self.find_element_visible(by, value)
        return element.text

    # =========================================================================
    # TAP & CLICK ACTIONS
    # =========================================================================

    def tap(self, by: AppiumBy, value: str):
        """Tap on an element (equivalent to click for mobile)."""
        element = self.find_element_clickable(by, value)
        element.click()

    def click(self, by: AppiumBy, value: str):
        """Click on an element (alias for tap)."""
        self.tap(by, value)

    def long_press(self, by: AppiumBy, value: str, duration: int = 1000):
        """Long press on an element.

        Args:
            by: Locator strategy
            value: Locator value
            duration: Press duration in milliseconds
        """
        element = self.find_element_clickable(by, value)
        self.driver.execute_script(
            'mobile: longClickGesture',
            {'elementId': element.id, 'duration': duration}
        )

    # =========================================================================
    # TEXT INPUT
    # =========================================================================

    def enter_text(self, by: AppiumBy, value: str, text: str):
        """Clear and enter text into an input field."""
        element = self.find_element_visible(by, value)
        element.clear()
        element.send_keys(text)

    def clear_text(self, by: AppiumBy, value: str):
        """Clear text from an input field."""
        element = self.find_element_visible(by, value)
        element.clear()

    # =========================================================================
    # KEYBOARD HANDLING
    # =========================================================================

    def hide_keyboard(self):
        """Hide the on-screen keyboard if visible."""
        try:
            if self.driver.is_keyboard_shown():
                self.driver.hide_keyboard()
        except Exception:
            pass  # Keyboard might not be visible

    def is_keyboard_shown(self) -> bool:
        """Check if the keyboard is currently shown."""
        try:
            return self.driver.is_keyboard_shown()
        except Exception:
            return False

    # =========================================================================
    # SWIPE GESTURES
    # =========================================================================

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 800):
        """Perform a swipe gesture.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Swipe duration in milliseconds
        """
        self.driver.execute_script(
            'mobile: swipeGesture',
            {
                'left': min(start_x, end_x),
                'top': min(start_y, end_y),
                'width': abs(end_x - start_x),
                'height': abs(end_y - start_y),
                'direction': 'up' if end_y < start_y else 'down',
                'percent': 0.75
            }
        )

    def swipe_up(self, percent: float = 0.5):
        """Swipe up on the screen.

        Args:
            percent: Percentage of screen to swipe (0.0 to 1.0)
        """
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = int(size['height'] * 0.8)
        end_y = int(size['height'] * (0.8 - percent * 0.6))

        self.driver.execute_script(
            'mobile: swipeGesture',
            {
                'left': start_x - 50,
                'top': end_y,
                'width': 100,
                'height': start_y - end_y,
                'direction': 'up',
                'percent': percent
            }
        )

    def swipe_down(self, percent: float = 0.5):
        """Swipe down on the screen.

        Args:
            percent: Percentage of screen to swipe (0.0 to 1.0)
        """
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = int(size['height'] * 0.2)
        end_y = int(size['height'] * (0.2 + percent * 0.6))

        self.driver.execute_script(
            'mobile: swipeGesture',
            {
                'left': start_x - 50,
                'top': start_y,
                'width': 100,
                'height': end_y - start_y,
                'direction': 'down',
                'percent': percent
            }
        )

    def scroll_to_element(self, by: AppiumBy, value: str, max_swipes: int = 5) -> Optional[WebElement]:
        """Scroll down until element is found.

        Args:
            by: Locator strategy
            value: Locator value
            max_swipes: Maximum number of swipes to attempt

        Returns:
            The element if found, None otherwise
        """
        for _ in range(max_swipes):
            if self.is_element_present(by, value, timeout=2):
                return self.find_element(by, value)
            self.swipe_up(0.3)
        return None

    # =========================================================================
    # APP STATE
    # =========================================================================

    def get_current_activity(self) -> str:
        """Get the current Android activity name."""
        return self.driver.current_activity

    def get_current_package(self) -> str:
        """Get the current Android package name."""
        return self.driver.current_package

    def wait_for_activity(self, activity: str, timeout: int = 10) -> bool:
        """Wait for a specific activity to be displayed.

        Args:
            activity: Activity name (e.g., '.MainActivity')
            timeout: Maximum wait time in seconds

        Returns:
            True if activity is displayed, False if timeout
        """
        try:
            return self.driver.wait_activity(activity, timeout)
        except Exception:
            return False

    def background_app(self, seconds: int = 1):
        """Put the app in the background for specified seconds."""
        self.driver.background_app(seconds)

    def launch_app(self):
        """Launch the app (if closed or in background)."""
        self.driver.activate_app(self.driver.capabilities.get('appPackage', ''))

    def close_app(self):
        """Close the app."""
        self.driver.terminate_app(self.driver.capabilities.get('appPackage', ''))
'''

    @property
    def CONFTEST_TEMPLATE(self) -> str:
        return '''"""Pytest fixtures for {module_name} Android tests."""

import os
import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options


# Android configuration from module_spec
APP_PACKAGE = "{app_package}"
APP_ACTIVITY = "{app_activity}"
DEVICE_NAME = "{device_name}"
AUTOMATION_NAME = "{automation_name}"
PLATFORM_VERSION = "{platform_version}"
APP_PATH = "{app_path}"
NO_RESET = {no_reset}


@pytest.fixture(scope="session")
def appium_server():
    """Appium server URL."""
    return os.getenv("APPIUM_SERVER", "http://localhost:4723")


@pytest.fixture(scope="function")
def driver(appium_server):
    """Appium WebDriver fixture for Android."""
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = DEVICE_NAME
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.automation_name = AUTOMATION_NAME
    options.no_reset = NO_RESET

    if PLATFORM_VERSION:
        options.platform_version = PLATFORM_VERSION

    if APP_PATH and os.path.exists(APP_PATH):
        options.app = os.path.abspath(APP_PATH)

    # Additional capabilities for stability
    options.set_capability("newCommandTimeout", 300)
    options.set_capability("autoGrantPermissions", True)

    driver = webdriver.Remote(
        command_executor=appium_server,
        options=options
    )
    driver.implicitly_wait(10)

    yield driver

    driver.quit()


{additional_fixtures}
'''

    @property
    def PAGE_GENERATION_PROMPT(self) -> str:
        return """Generate a Python Page Object class for ANDROID/APPIUM with these specifications:

Page Name: {page_name}
File: {file_name}
Base Class: BasePage

Elements (with selectors):
{elements}

Methods to generate:
{methods}

REQUIREMENTS:
1. Import BasePage and AppiumBy from appium.webdriver.common.appiumby
2. Define element locators as class attributes using tuples: (AppiumBy.X, "value")
3. Create getter/setter methods for each element
4. Create action methods as specified
5. Use the best selector (accessibility_id, id, xpath)
6. Add docstrings to all methods
7. Handle waits properly using BasePage methods
8. Call hide_keyboard() after text input methods

IMPORTANT: This is for APPIUM (Android mobile), NOT Selenium web.
Use AppiumBy instead of By.
Use accessibility_id, id (resource-id), xpath - NOT css selectors.

Return ONLY the Python code, no explanation."""

    @property
    def TEST_GENERATION_PROMPT(self) -> str:
        return """Generate a Pytest test function for ANDROID/APPIUM with these specifications:

Test ID: {test_id}
Test Name: {test_name}
Description: {description}

Steps:
{steps}

Expected Results:
{expected}

Available Pages: {pages_used}
Test Data: {test_data}

GENERATED PAGE OBJECT CODE (use ONLY these methods):
{page_code_context}

CRITICAL REQUIREMENT - METHOD USAGE:
You MUST use ONLY methods that exist in the page objects shown above.
- DO NOT invent methods like wait_for_*, get_*, verify_*, etc.
- Check the actual page class code above before calling any method
- Available BasePage methods: find_element(), find_element_clickable(), find_element_visible(),
  is_element_present(), get_element_text(), tap(), click(), enter_text(), hide_keyboard(),
  swipe_up(), swipe_down(), scroll_to_element()

REQUIREMENTS:
1. Use pytest fixtures (driver) - NOTE: no base_url for mobile
2. Import necessary page objects
3. Add pytest markers: {markers}
4. Add clear docstring with test description
5. Include assertions for expected results
6. Call hide_keyboard() after entering text
7. Use tap() instead of click() for mobile elements

IMPORTANT: This is for APPIUM (Android mobile), NOT Selenium web.
- No browser, no URLs
- Use page objects that take only driver (not base_url)
- Use mobile-specific methods like tap(), swipe(), hide_keyboard()

Return ONLY the Python code, no explanation."""

    def get_by_type(self, selector_type: str) -> str:
        """Convert selector type to Appium By type."""
        mapping = {
            # Android/Mobile selectors
            "accessibility_id": "AppiumBy.ACCESSIBILITY_ID",
            "id": "AppiumBy.ID",
            "resource_id": "AppiumBy.ID",
            "xpath": "AppiumBy.XPATH",
            "android_uiautomator": "AppiumBy.ANDROID_UIAUTOMATOR",
            "class_name": "AppiumBy.CLASS_NAME",
            # Web selectors (fallback - not recommended for Android)
            "name": "AppiumBy.NAME",
            "css": "AppiumBy.CSS_SELECTOR",  # Not supported well in Appium
        }
        return mapping.get(selector_type, "AppiumBy.XPATH")

    def get_selector_value(self, selector: Dict[str, str]) -> str:
        """Get the selector value for Appium.

        Unlike Selenium, Appium selectors typically don't need transformation.
        """
        selector_type = selector.get("selector_type", "xpath")
        value = selector.get("value", "")

        # For resource_id, ensure it has the full format if just ID is provided
        if selector_type in ("id", "resource_id"):
            # If it doesn't contain ':', it might need the package prefix
            # But usually the full resource-id is provided
            return value

        return value
