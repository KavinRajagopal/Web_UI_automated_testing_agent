"""Web/Selenium templates for browser-based test generation.

This module contains all templates and prompts for generating
Selenium-based web automation code.
"""

from typing import Dict
from .base_templates import BaseTemplates


class WebTemplates(BaseTemplates):
    """Selenium/WebDriver templates for web browser automation."""

    @property
    def platform_name(self) -> str:
        return "web"

    @property
    def BASE_PAGE_TEMPLATE(self) -> str:
        return '''"""Base Page Object class for all page objects."""

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

    @property
    def CONFTEST_TEMPLATE(self) -> str:
        return '''"""Pytest fixtures for {module_name} tests."""

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

    @property
    def PAGE_GENERATION_PROMPT(self) -> str:
        return """Generate a Python Page Object class with these specifications:

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

    @property
    def TEST_GENERATION_PROMPT(self) -> str:
        return """Generate a Pytest test function with these specifications:

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
- Available BasePage methods: navigate(), find_element(), find_element_clickable(),
  find_element_visible(), is_element_present(), get_element_text(), enter_text(), click()

REQUIREMENTS:
1. Use pytest fixtures (driver, base_url)
2. Import necessary page objects
3. Add pytest markers: {markers}
4. Add clear docstring with test description
5. Include assertions for expected results
6. Handle setup and teardown if needed

Return ONLY the Python code, no explanation."""

    def get_by_type(self, selector_type: str) -> str:
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

    def get_selector_value(self, selector: Dict[str, str]) -> str:
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
