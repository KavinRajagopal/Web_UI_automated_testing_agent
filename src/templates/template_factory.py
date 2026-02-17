"""Template Factory for platform-specific code generation.

This module provides the factory function that returns the appropriate
template class based on the target platform.
"""

from typing import Union
from .base_templates import BaseTemplates
from .web_templates import WebTemplates
from .android_templates import AndroidTemplates


# Singleton instances for reuse
_web_templates = None
_android_templates = None


def get_templates(platform_type: str) -> BaseTemplates:
    """Get platform-specific templates.

    Args:
        platform_type: Target platform - 'web' or 'android'

    Returns:
        Templates instance for the specified platform

    Raises:
        ValueError: If platform_type is not supported

    Example:
        >>> templates = get_templates("android")
        >>> print(templates.platform_name)
        'android'
        >>> base_code = templates.BASE_PAGE_TEMPLATE
    """
    global _web_templates, _android_templates

    platform_type = platform_type.lower().strip()

    if platform_type == "web":
        if _web_templates is None:
            _web_templates = WebTemplates()
        return _web_templates

    elif platform_type == "android":
        if _android_templates is None:
            _android_templates = AndroidTemplates()
        return _android_templates

    else:
        supported = ["web", "android"]
        raise ValueError(
            f"Unsupported platform_type: '{platform_type}'. "
            f"Supported platforms: {supported}"
        )


def get_supported_platforms() -> list:
    """Return list of supported platform types."""
    return ["web", "android"]


def is_mobile_platform(platform_type: str) -> bool:
    """Check if the platform is a mobile platform.

    Args:
        platform_type: Platform type to check

    Returns:
        True if mobile (android, ios), False otherwise
    """
    return platform_type.lower() in ("android", "ios")
