"""Pydantic models for the Web UI Test Generation Agent.

This module defines all data structures used throughout the agent:
- Input models: Configuration and test case inputs
- Element models: UI element selectors and metadata
- Planning models: LLM-generated generation plans
- Verification models: Code verification results
- Reporting models: Final AI report structure
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class PlatformType(str, Enum):
    """Target platform types for test generation."""
    WEB = "web"
    ANDROID = "android"
    # Future: IOS = "ios"


class AutomationName(str, Enum):
    """Appium automation engine names."""
    UIAUTOMATOR2 = "UiAutomator2"
    ESPRESSO = "Espresso"
    # Future: XCUITEST = "XCUITest"


class SelectorType(str, Enum):
    """Selector strategy types, ordered by stability preference."""
    # Web selectors
    ID = "id"
    DATA_TESTID = "data-testid"
    NAME = "name"
    ARIA_LABEL = "aria-label"
    CSS = "css"
    XPATH = "xpath"
    # Android/Mobile selectors
    ACCESSIBILITY_ID = "accessibility_id"
    ANDROID_UIAUTOMATOR = "android_uiautomator"
    RESOURCE_ID = "resource_id"

    @classmethod
    def stability_order(cls) -> List["SelectorType"]:
        """Return selector types ordered by stability (best first)."""
        return [
            cls.ID,
            cls.DATA_TESTID,
            cls.NAME,
            cls.ARIA_LABEL,
            cls.CSS,
            cls.XPATH
        ]

    @classmethod
    def android_stability_order(cls) -> List["SelectorType"]:
        """Return Android selector types ordered by stability (best first)."""
        return [
            cls.ACCESSIBILITY_ID,
            cls.RESOURCE_ID,
            cls.ID,
            cls.XPATH,
            cls.ANDROID_UIAUTOMATOR
        ]


class CheckpointStatus(str, Enum):
    """Status for verification checkpoints."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# INPUT MODELS
# =============================================================================

class PageConfig(BaseModel):
    """Configuration for a single page in module_spec.json."""
    name: str = Field(..., description="Page class name (e.g., 'LoginPage')")
    url_pattern: Optional[str] = Field(None, description="URL pattern to match this page")
    element_metadata_file: Optional[str] = Field(None, description="Path to element JSON file")

    class Config:
        extra = "allow"  # Allow additional fields


class AndroidConfig(BaseModel):
    """Android-specific configuration for Appium tests.

    Required when platform_type='android' in ModuleSpec.
    """
    app_package: str = Field(..., description="Android app package name (e.g., 'com.example.app')")
    app_activity: str = Field(..., description="Main activity to launch (e.g., '.MainActivity')")

    device_name: str = Field(
        default="Android Emulator",
        description="Device name or emulator ID"
    )
    platform_version: Optional[str] = Field(
        None,
        description="Android version (e.g., '11.0')"
    )
    automation_name: AutomationName = Field(
        default=AutomationName.UIAUTOMATOR2,
        description="Appium automation engine"
    )
    app_path: Optional[str] = Field(
        None,
        description="Path to APK file (optional if app already installed)"
    )
    no_reset: bool = Field(
        default=True,
        description="Don't reset app state between tests"
    )

    class Config:
        extra = "allow"  # Allow additional Appium capabilities


class ModuleSpec(BaseModel):
    """Module specification from module_spec.json.

    Defines the test module configuration including:
    - Target app details
    - Platform type (web or android)
    - Browser/environment settings
    - Selector preferences
    - Pages to generate
    """
    module_name: str = Field(..., description="Name of the test module (e.g., 'authentication')")
    app_name: str = Field(default="TringPlay", description="Target application name")
    app_url: Optional[str] = Field(None, description="Base URL of the application (required for web)")

    # Platform configuration
    platform_type: PlatformType = Field(
        default=PlatformType.WEB,
        description="Target platform: 'web' (default) or 'android'"
    )
    android_config: Optional[AndroidConfig] = Field(
        None,
        description="Android/Appium configuration (required when platform_type='android')"
    )

    # Environment
    environment: str = Field(default="staging", description="Target environment")
    browser: str = Field(default="chrome", description="Target browser (web only)")
    
    # Selector policy
    selector_priority: List[str] = Field(
        default=["id", "data-testid", "name", "aria-label", "css"],
        description="Selector types in priority order"
    )
    avoid_selectors: List[str] = Field(
        default=["xpath"],
        description="Selector types to avoid if possible"
    )
    
    # Pages
    pages: List[PageConfig] = Field(default_factory=list, description="Pages in this module")
    
    # Optional metadata
    description: Optional[str] = None
    owner: Optional[str] = None
    
    class Config:
        extra = "allow"


class TestCaseRow(BaseModel):
    """A single test case row from testcases.csv.
    
    Matches your spreadsheet format with pipe-delimited fields.
    """
    test_id: str = Field(..., description="Unique test identifier (e.g., 'TC_LOGIN_001')")
    test_name: str = Field(..., description="Human-readable test name")
    module: str = Field(..., description="Module this test belongs to")
    priority: str = Field(default="P1", description="Priority level (P0, P1, P2)")
    
    # Test steps - pipe delimited in CSV
    preconditions: Optional[str] = Field(None, description="Setup requirements")
    steps: str = Field(..., description="Test steps (pipe-delimited)")
    expected_result: str = Field(..., description="Expected outcome")
    
    # Test data
    test_data: Optional[str] = Field(None, description="Test data (pipe-delimited key=value)")
    
    # Metadata
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    page_name: Optional[str] = Field(None, description="Primary page for this test")
    
    @field_validator('steps', 'expected_result')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure required fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
    def get_steps_list(self) -> List[str]:
        """Parse pipe-delimited steps into a list."""
        if not self.steps:
            return []
        return [s.strip() for s in self.steps.split("|") if s.strip()]
    
    def get_test_data_dict(self) -> Dict[str, str]:
        """Parse pipe-delimited test data into a dict.
        
        Format: 'username=testuser|password=Test123!'
        Returns: {'username': 'testuser', 'password': 'Test123!'}
        """
        if not self.test_data:
            return {}
        
        result = {}
        for pair in self.test_data.split("|"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                result[key.strip()] = value.strip()
        return result


# =============================================================================
# ELEMENT MODELS
# =============================================================================

class ElementSelector(BaseModel):
    """A single selector for a UI element."""
    selector_type: SelectorType = Field(..., description="Type of selector")
    value: str = Field(..., description="Selector value")
    confidence: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    is_stable: bool = Field(
        default=True,
        description="Whether this selector is considered stable"
    )
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str) -> str:
        """Ensure selector value is not empty."""
        if not v or not v.strip():
            raise ValueError("Selector value cannot be empty")
        return v.strip()
    
    def is_css_module_hash(self) -> bool:
        """Check if this looks like a CSS module hash (unstable)."""
        if self.selector_type not in [SelectorType.CSS, SelectorType.XPATH]:
            return False
        # CSS module hashes typically look like: .Button_primary__a1b2c3
        import re
        return bool(re.search(r'__[a-zA-Z0-9]{5,}', self.value))


class UIElement(BaseModel):
    """A UI element with multiple selector options.
    
    Each element has a primary selector (best) and fallback options.
    """
    name: str = Field(..., description="Element name (e.g., 'email_input')")
    description: Optional[str] = Field(None, description="What this element is for")
    element_type: str = Field(default="element", description="Type: input, button, link, etc.")
    
    # Selectors - ordered by preference
    selectors: List[ElementSelector] = Field(
        default_factory=list,
        description="Available selectors, ordered by preference"
    )
    
    # Interaction hints
    is_required: bool = Field(default=False, description="Whether this element is required for tests")
    wait_strategy: Optional[str] = Field(None, description="Wait strategy: visible, clickable, present")
    
    def get_best_selector(self) -> Optional[ElementSelector]:
        """Get the most stable/preferred selector."""
        if not self.selectors:
            return None
        
        # Filter to stable selectors
        stable = [s for s in self.selectors if s.is_stable]
        if stable:
            return stable[0]
        
        # Fall back to first available
        return self.selectors[0]
    
    def get_selector_by_type(self, selector_type: SelectorType) -> Optional[ElementSelector]:
        """Get a specific selector type if available."""
        for s in self.selectors:
            if s.selector_type == selector_type:
                return s
        return None


class PageMetadata(BaseModel):
    """Metadata for a page, including all its elements.
    
    Loaded from element_metadata/*.json files.
    """
    page_name: str = Field(..., description="Page class name")
    page_url: Optional[str] = Field(None, description="Page URL or pattern")
    description: Optional[str] = Field(None, description="What this page represents")
    
    elements: List[UIElement] = Field(
        default_factory=list,
        description="UI elements on this page"
    )
    
    # Metadata
    last_updated: Optional[datetime] = None
    extracted_from: Optional[str] = Field(None, description="Source of extraction")
    
    def get_element(self, name: str) -> Optional[UIElement]:
        """Find an element by name."""
        for elem in self.elements:
            if elem.name == name:
                return elem
        return None
    
    def get_required_elements(self) -> List[UIElement]:
        """Get all elements marked as required."""
        return [e for e in self.elements if e.is_required]


# =============================================================================
# PLANNING MODELS
# =============================================================================

class PagePlan(BaseModel):
    """Plan for generating a Page Object class."""
    page_name: str = Field(..., description="Class name (e.g., 'LoginPage')")
    file_name: str = Field(..., description="Output file name (e.g., 'login_page.py')")
    
    elements: List[str] = Field(default_factory=list, description="Element names to include")
    methods: List[str] = Field(default_factory=list, description="Methods to generate")
    
    inherits_from: str = Field(default="BasePage", description="Parent class")
    description: Optional[str] = None


class FlowPlan(BaseModel):
    """Plan for generating a Flow class."""
    flow_name: str = Field(..., description="Class name (e.g., 'AuthFlow')")
    file_name: str = Field(..., description="Output file name")
    
    pages_used: List[str] = Field(default_factory=list, description="Page classes used")
    methods: List[str] = Field(default_factory=list, description="Flow methods to generate")
    
    description: Optional[str] = None


class TestPlan(BaseModel):
    """Plan for generating a test function."""
    test_id: str = Field(..., description="Original test ID from CSV")
    test_name: str = Field(..., description="Test function name")
    
    flow_used: Optional[str] = Field(None, description="Flow class to use")
    pages_used: List[str] = Field(default_factory=list, description="Page classes used directly")
    
    steps_summary: List[str] = Field(default_factory=list, description="High-level step descriptions")
    markers: List[str] = Field(default_factory=list, description="Pytest markers")
    
    description: Optional[str] = None


class GenerationPlan(BaseModel):
    """Complete plan for code generation, created by Planning node.
    
    This is the main output from the LLM planning step.
    """
    module_name: str = Field(..., description="Module being generated")
    
    # What to generate
    pages: List[PagePlan] = Field(default_factory=list)
    flows: List[FlowPlan] = Field(default_factory=list)
    tests: List[TestPlan] = Field(default_factory=list)
    
    # Shared utilities
    conftest_fixtures: List[str] = Field(
        default_factory=list,
        description="Fixtures to generate in conftest.py"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    llm_model: Optional[str] = None
    
    # Summary stats
    @property
    def total_files(self) -> int:
        """Total number of files to generate."""
        # pages + flows + tests + conftest + base_page + requirements + pytest.ini
        return len(self.pages) + len(self.flows) + 1 + 3
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        return (
            f"Module: {self.module_name}\n"
            f"Pages: {len(self.pages)} ({', '.join(p.page_name for p in self.pages)})\n"
            f"Flows: {len(self.flows)} ({', '.join(f.flow_name for f in self.flows)})\n"
            f"Tests: {len(self.tests)}\n"
            f"Total files: ~{self.total_files}"
        )


# =============================================================================
# VERIFICATION MODELS
# =============================================================================

class CheckpointResult(BaseModel):
    """Result of a single verification checkpoint."""
    checkpoint_name: str = Field(..., description="A, B, C, or D")
    checkpoint_description: str = Field(..., description="What was checked")
    
    status: CheckpointStatus = Field(..., description="passed, failed, skipped")
    
    # Details
    files_checked: List[str] = Field(default_factory=list)
    files_passed: List[str] = Field(default_factory=list)
    files_failed: List[str] = Field(default_factory=list)
    
    # Error details for failed files
    errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of file -> error message (or list of errors as string)"
    )
    
    # Timing
    duration_seconds: Optional[float] = None
    
    # Metadata (for checkpoint D: test counts)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional checkpoint-specific data"
    )


class VerificationResults(BaseModel):
    """Combined results from all verification checkpoints."""

    checkpoint_a: Optional[CheckpointResult] = Field(None, description="Syntax check")
    checkpoint_b: Optional[CheckpointResult] = Field(None, description="Import check")
    checkpoint_b5: Optional[CheckpointResult] = Field(None, description="Method consistency check")
    checkpoint_c: Optional[CheckpointResult] = Field(None, description="Pytest collection")
    checkpoint_d: Optional[CheckpointResult] = Field(None, description="Test execution")

    # Overall
    all_passed: bool = Field(default=False)

    # Recovery tracking
    recovery_attempts: int = Field(default=0)
    files_recovered: List[str] = Field(default_factory=list)

    def calculate_all_passed(self) -> bool:
        """Check if all checkpoints passed."""
        checkpoints = [
            self.checkpoint_a, self.checkpoint_b, self.checkpoint_b5,
            self.checkpoint_c, self.checkpoint_d
        ]
        for cp in checkpoints:
            if cp and cp.status == CheckpointStatus.FAILED:
                return False
        return True


# =============================================================================
# REPORTING MODELS
# =============================================================================

class SelectorRisk(BaseModel):
    """A flagged selector that may be unstable."""
    file_name: str
    element_name: str
    selector_type: str
    selector_value: str
    
    risk_reason: str = Field(..., description="Why this is risky")
    suggestion: Optional[str] = Field(None, description="How to improve")


class AIReport(BaseModel):
    """Final AI-generated report for the test generation session.
    
    Saved to ai_report.json and ai_report.md
    """
    # Session info
    session_id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    module_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # What was generated
    files_generated: List[str] = Field(default_factory=list)
    tests_generated: int = Field(default=0)
    pages_generated: int = Field(default=0)
    flows_generated: int = Field(default=0)
    
    # Verification
    verification_passed: bool = Field(default=False)
    checkpoints_summary: Dict[str, str] = Field(default_factory=dict)
    
    # Risks and recommendations
    selector_risks: List[SelectorRisk] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # LLM usage
    llm_calls: int = Field(default=0)
    total_tokens: int = Field(default=0)
    
    # Timing
    duration_seconds: Optional[float] = None
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# AI Test Generation Report",
            f"",
            f"**Module:** {self.module_name}",
            f"**Generated:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Session ID:** {self.session_id}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files Generated | {len(self.files_generated)} |",
            f"| Tests Generated | {self.tests_generated} |",
            f"| Pages Generated | {self.pages_generated} |",
            f"| Flows Generated | {self.flows_generated} |",
            f"| Verification | {'✅ PASSED' if self.verification_passed else '❌ FAILED'} |",
            f"| LLM Calls | {self.llm_calls} |",
            f"| Total Tokens | {self.total_tokens:,} |",
            f"",
        ]
        
        if self.selector_risks:
            lines.extend([
                f"## Selector Risks ({len(self.selector_risks)})",
                f"",
            ])
            for risk in self.selector_risks:
                lines.extend([
                    f"### {risk.file_name} - {risk.element_name}",
                    f"- **Selector:** `{risk.selector_value}`",
                    f"- **Risk:** {risk.risk_reason}",
                    f"- **Suggestion:** {risk.suggestion or 'N/A'}",
                    f"",
                ])
        
        if self.recommendations:
            lines.extend([
                f"## Recommendations",
                f"",
            ])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        lines.extend([
            f"## Files Generated",
            f"",
        ])
        for f in self.files_generated:
            lines.append(f"- `{f}`")
        
        return "\n".join(lines)
