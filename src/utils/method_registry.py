"""Method Registry - Centralized tracking of page object methods.

This module provides a single source of truth for:
- Page name to file path mapping
- Page name to available methods mapping
- Method signature validation

Used by generation and recovery nodes to ensure consistency between
generated page objects and tests.
"""

import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field

from ..tools.method_extractor import extract_method_names, extract_method_signatures

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    """Information about a generated page object."""
    page_name: str
    file_path: str
    class_name: str
    methods: List[str] = field(default_factory=list)
    method_signatures: Dict[str, Dict] = field(default_factory=dict)
    locators: List[str] = field(default_factory=list)
    element_metadata: Optional[Dict[str, Any]] = None  # Cached for recovery re-injection


class MethodRegistry:
    """
    Centralized registry for tracking page object methods.

    This registry ensures consistency between generated page objects
    and the tests that use them. It provides:
    - Fuzzy matching for page name lookups
    - Method availability checking
    - Alias resolution (e.g., click_login -> click_login_button)
    """

    # Common method aliases
    METHOD_ALIASES = {
        "click_login": ["click_login_button", "submit_login"],
        "click_submit": ["click_submit_button", "submit_form"],
        "is_on_page": ["is_page_loaded", "is_loaded"],
        "get_error": ["get_error_message", "get_error_text"],
        "is_error": ["is_error_displayed", "has_error"],
    }

    def __init__(self):
        self.pages: Dict[str, PageInfo] = {}
        self._name_lookup: Dict[str, str] = {}  # normalized_name -> actual_name

    def register_page(
        self,
        page_name: str,
        file_path: str,
        code: str,
        class_name: Optional[str] = None
    ) -> PageInfo:
        """
        Register a generated page object and extract its methods.

        Args:
            page_name: Name of the page (e.g., "LoginPage")
            file_path: Relative file path (e.g., "pages/login_page.py")
            code: Generated Python code
            class_name: Optional class name override

        Returns:
            PageInfo with extracted methods
        """
        # Extract methods using AST
        methods_by_class = extract_method_names(code)
        signatures_by_class = extract_method_signatures(code)

        # Flatten methods from all classes (usually just one per file)
        all_methods = []
        all_signatures = {}
        for cls_name, methods in methods_by_class.items():
            all_methods.extend(methods)
            if cls_name in signatures_by_class:
                all_signatures.update(signatures_by_class[cls_name])

        # Extract locator constants (class attributes with tuple values)
        locators = self._extract_locators(code)

        # Determine class name
        actual_class_name = class_name
        if not actual_class_name and methods_by_class:
            actual_class_name = list(methods_by_class.keys())[0]
        if not actual_class_name:
            actual_class_name = page_name

        # Create page info
        page_info = PageInfo(
            page_name=page_name,
            file_path=file_path,
            class_name=actual_class_name,
            methods=all_methods,
            method_signatures=all_signatures,
            locators=locators
        )

        # Store with multiple lookup keys
        self.pages[page_name] = page_info

        # Build lookup index
        self._name_lookup[page_name.lower()] = page_name
        self._name_lookup[page_name] = page_name

        # Also index without "Page" suffix
        base_name = page_name.replace("Page", "").replace("page", "")
        self._name_lookup[base_name.lower()] = page_name
        self._name_lookup[base_name] = page_name

        logger.info(
            f"Registered {page_name}: {len(all_methods)} methods, "
            f"{len(locators)} locators"
        )

        return page_info

    def register_page_with_metadata(
        self,
        page_name: str,
        file_path: str,
        code: str,
        metadata: Dict[str, Any],
        class_name: Optional[str] = None
    ) -> PageInfo:
        """
        Register a page and cache its element metadata for recovery re-injection.

        This ensures that even if recovery regenerates code with incorrect locators,
        we can re-inject the correct deterministic locators from cached metadata.

        Args:
            page_name: Name of the page (e.g., "LoginPage")
            file_path: Relative file path (e.g., "pages/login_page.py")
            code: Generated Python code
            metadata: Original element metadata for this page
            class_name: Optional class name override

        Returns:
            PageInfo with extracted methods and cached metadata
        """
        page_info = self.register_page(page_name, file_path, code, class_name)
        page_info.element_metadata = metadata
        logger.debug(f"Cached element metadata for {page_name}")
        return page_info

    def _extract_locators(self, code: str) -> List[str]:
        """Extract locator constant names from code."""
        import re
        # Match patterns like: USERNAME_INPUT = (By.ID, "user-name")
        pattern = r'^[ \t]+([A-Z][A-Z0-9_]*)\s*=\s*\(By\.'
        locators = []
        for line in code.split('\n'):
            match = re.match(pattern, line)
            if match:
                locators.append(match.group(1))
        return locators

    def get_page(self, page_name: str) -> Optional[PageInfo]:
        """
        Get page info with fuzzy matching on name.

        Args:
            page_name: Page name to look up (case-insensitive)

        Returns:
            PageInfo if found, None otherwise
        """
        # Try exact match first
        if page_name in self.pages:
            return self.pages[page_name]

        # Try lookup index
        actual_name = self._name_lookup.get(page_name)
        if actual_name:
            return self.pages.get(actual_name)

        # Try case-insensitive
        actual_name = self._name_lookup.get(page_name.lower())
        if actual_name:
            return self.pages.get(actual_name)

        return None

    def get_methods(self, page_name: str) -> List[str]:
        """
        Get available methods for a page with fuzzy matching.

        Args:
            page_name: Page name to look up

        Returns:
            List of method names, or empty list if not found
        """
        page_info = self.get_page(page_name)
        if page_info:
            return page_info.methods
        return []

    def get_methods_with_aliases(self, page_name: str) -> Set[str]:
        """
        Get available methods plus common aliases.

        Args:
            page_name: Page name to look up

        Returns:
            Set of method names including aliases
        """
        methods = set(self.get_methods(page_name))

        # Add reverse aliases
        for alias, targets in self.METHOD_ALIASES.items():
            if alias in methods:
                methods.update(targets)
            for target in targets:
                if target in methods:
                    methods.add(alias)

        return methods

    def validate_method_call(
        self,
        page_name: str,
        method_name: str
    ) -> Dict[str, Any]:
        """
        Check if a method exists on a page.

        Args:
            page_name: Page name
            method_name: Method being called

        Returns:
            Dict with:
                - valid: bool
                - suggestion: str (if invalid, suggests similar method)
                - available_methods: List[str]
        """
        page_info = self.get_page(page_name)

        if not page_info:
            return {
                "valid": False,
                "error": f"Page '{page_name}' not found in registry",
                "suggestion": None,
                "available_methods": []
            }

        methods_with_aliases = self.get_methods_with_aliases(page_name)

        if method_name in methods_with_aliases:
            return {
                "valid": True,
                "suggestion": None,
                "available_methods": list(methods_with_aliases)
            }

        # Find similar method
        suggestion = self._find_similar_method(method_name, page_info.methods)

        return {
            "valid": False,
            "error": f"Method '{method_name}' not found on {page_name}",
            "suggestion": suggestion,
            "available_methods": page_info.methods
        }

    def _find_similar_method(
        self,
        method_name: str,
        available_methods: List[str]
    ) -> Optional[str]:
        """Find a similar method name using fuzzy matching."""
        from difflib import SequenceMatcher

        best_match = None
        best_ratio = 0.0

        for available in available_methods:
            ratio = SequenceMatcher(None, method_name.lower(), available.lower()).ratio()
            if ratio > best_ratio and ratio > 0.5:  # Minimum 50% similarity
                best_ratio = ratio
                best_match = available

        return best_match

    def get_all_pages(self) -> List[str]:
        """Get all registered page names."""
        return list(self.pages.keys())

    def get_methods_text(self, page_name: str, max_methods: int = 30) -> str:
        """
        Get formatted text of available methods for LLM prompts.

        Args:
            page_name: Page name to look up
            max_methods: Maximum number of methods to include

        Returns:
            Formatted string of methods
        """
        methods = self.get_methods_with_aliases(page_name)
        if not methods:
            return f"{page_name}: No methods registered"

        sorted_methods = sorted(methods)[:max_methods]
        return f"{page_name} methods: {', '.join(sorted_methods)}"

    def clear(self):
        """Clear all registered pages."""
        self.pages.clear()
        self._name_lookup.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Export registry to dict for serialization."""
        return {
            page_name: {
                "file_path": info.file_path,
                "class_name": info.class_name,
                "methods": info.methods,
                "locators": info.locators
            }
            for page_name, info in self.pages.items()
        }


# Global registry instance for use across nodes
_global_registry: Optional[MethodRegistry] = None


def get_registry() -> MethodRegistry:
    """Get or create the global method registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = MethodRegistry()
    return _global_registry


def reset_registry():
    """Reset the global registry (for testing)."""
    global _global_registry
    _global_registry = None
