"""Tools for automated element discovery and test case generation.

This module contains:
- ElementDiscoveryTool: Selenium-based UI element extraction
- TestCaseGenerator: LLM-powered test case generation from elements
"""

from .element_discovery import ElementDiscoveryTool
from .testcase_generator import TestCaseGenerator

__all__ = ["ElementDiscoveryTool", "TestCaseGenerator"]
