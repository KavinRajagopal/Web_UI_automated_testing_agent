"""Base template interface for platform-specific code generation.

This module defines the abstract base class that all platform-specific
template classes must implement. The Template Factory pattern allows
easy extension to new platforms (iOS, etc.) in the future.
"""

from abc import ABC, abstractmethod
from typing import Dict


class BaseTemplates(ABC):
    """Abstract base class for platform-specific templates.

    Each platform (web, android, ios) must implement this interface
    to provide code generation templates.
    """

    @property
    @abstractmethod
    def BASE_PAGE_TEMPLATE(self) -> str:
        """Return the base page class template.

        This template should include:
        - Required imports for the platform
        - Base page class with common methods
        - Wait helpers, click, enter text, etc.
        """
        ...

    @property
    @abstractmethod
    def CONFTEST_TEMPLATE(self) -> str:
        """Return the pytest conftest.py template.

        This template should include:
        - Driver setup/teardown fixture
        - Base URL fixture
        - Placeholders for module_name, base_url, additional_fixtures
        """
        ...

    @property
    @abstractmethod
    def PAGE_GENERATION_PROMPT(self) -> str:
        """Return the LLM prompt for generating page classes.

        Placeholders: {page_name}, {file_name}, {elements}, {methods}
        """
        ...

    @property
    @abstractmethod
    def TEST_GENERATION_PROMPT(self) -> str:
        """Return the LLM prompt for generating test functions.

        Placeholders: {test_id}, {test_name}, {description}, {steps},
                      {expected}, {pages_used}, {markers}, {test_data}
        """
        ...

    @property
    def PYTEST_INI_TEMPLATE(self) -> str:
        """Return the pytest.ini template (same for all platforms)."""
        return '''[pytest]
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

    @abstractmethod
    def get_by_type(self, selector_type: str) -> str:
        """Convert selector type to platform-specific locator type.

        Args:
            selector_type: Type like 'id', 'css', 'accessibility_id'

        Returns:
            Platform-specific By type, e.g., 'By.ID', 'AppiumBy.ACCESSIBILITY_ID'
        """
        ...

    @abstractmethod
    def get_selector_value(self, selector: Dict[str, str]) -> str:
        """Transform selector value for the platform if needed.

        Args:
            selector: Dict with 'selector_type' and 'value' keys

        Returns:
            Transformed selector value
        """
        ...

    @property
    def platform_name(self) -> str:
        """Return the platform name for logging."""
        return "unknown"
