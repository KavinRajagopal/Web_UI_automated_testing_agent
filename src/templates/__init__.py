"""Templates module for platform-specific code generation.

This module provides the Template Factory pattern for generating
automation code for different platforms (web, android, ios).

Usage:
    from src.templates import get_templates, WebTemplates, AndroidTemplates

    # Get templates for a specific platform
    templates = get_templates("android")

    # Use templates
    base_page_code = templates.BASE_PAGE_TEMPLATE
    by_type = templates.get_by_type("accessibility_id")

    # Or use specific template class directly
    android = AndroidTemplates()
    web = WebTemplates()
"""

from .base_templates import BaseTemplates
from .web_templates import WebTemplates
from .android_templates import AndroidTemplates
from .template_factory import (
    get_templates,
    get_supported_platforms,
    is_mobile_platform,
)


__all__ = [
    # Base class
    "BaseTemplates",
    # Platform implementations
    "WebTemplates",
    "AndroidTemplates",
    # Factory functions
    "get_templates",
    "get_supported_platforms",
    "is_mobile_platform",
]
