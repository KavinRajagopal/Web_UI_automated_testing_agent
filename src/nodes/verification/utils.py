"""Shared utilities for verification checkpoints."""

import re
from typing import Optional

logger = None  # Will be set by importing module


def extract_error_type(error_line: str) -> Optional[str]:
    """Extract error type from pytest error line."""
    error_patterns = [
        r'AttributeError: (.+)',
        r'AssertionError: (.+)',
        r'NameError: (.+)',
        r'TypeError: (.+)',
        r'ImportError: (.+)',
        r'TimeoutException: (.+)',
        r'NoSuchElementException: (.+)',
        r'WebDriverException: (.+)',
        r'TimeoutError: (.+)'
    ]
    
    for pattern in error_patterns:
        match = re.search(pattern, error_line)
        if match:
            return match.group(0)
    return None
