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

class SelectorType(str, Enum):
    """Selector strategy types, ordered by stability preference."""
    ID = "id"
    DATA_TESTID = "data-testid"
    NAME = "name"
    ARIA_LABEL = "aria-label"
    CSS = "css"
    XPATH = "xpath"
    
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


class ModuleSpec(BaseModel):
    """Module specification from module_spec.json.
    
    Defines the test module configuration including:
    - Target app details
    - Browser/environment settings
    - Selector preferences
    - Pages to generate
    """
    module_name: str = Field(..., description="Name of the test module (e.g., 'authentication')")
    app_name: str = Field(default="TringPlay", description="Target application name")
    app_url: str = Field(..., description="Base URL of the application")
    
    # Environment
    environment: str = Field(default="staging", description="Target environment")
    browser: str = Field(default="chrome", description="Target browser")
    
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
# TEST CASE ANALYSIS MODELS
# =============================================================================

class DuplicateTestCase(BaseModel):
    """Identified duplicate test case."""
    test_id: str
    test_name: str
    duplicate_of: str = Field(..., description="test_id of the original")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score 0-1")
    reason: str = Field(..., description="Why this is considered a duplicate")
    recommendation: str = Field(default="merge", description="merge, remove, or keep_separate")


class SuggestedTestCase(BaseModel):
    """Suggested additional test case."""
    test_id: str = Field(..., description="Suggested test ID")
    test_name: str = Field(..., description="Suggested test name")
    module: str
    priority: str = Field(default="P1")
    steps: str
    expected_result: str
    reason: str = Field(..., description="Why this test case should be added")
    coverage_gap: str = Field(..., description="What coverage gap this addresses")


class TestCasePriority(BaseModel):
    """Test case with priority analysis."""
    test_id: str
    test_name: str
    current_priority: str
    recommended_priority: str
    priority_reason: str = Field(..., description="Why this priority is recommended")
    is_critical: bool = Field(default=False, description="Is this a critical test case")


class CoverageMetrics(BaseModel):
    """Coverage metrics for a module or page."""
    module_or_page: str
    total_test_cases: int
    coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    covered_scenarios: List[str] = Field(default_factory=list)
    missing_scenarios: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class TestCaseAnalysis(BaseModel):
    """Complete test case analysis results."""
    # Duplicate detection
    duplicates: List[DuplicateTestCase] = Field(default_factory=list)
    duplicate_count: int = Field(default=0)
    efficient_test_count: int = Field(default=0)
    
    # Suggested test cases
    suggested_tests: List[SuggestedTestCase] = Field(default_factory=list)
    
    # Priority analysis
    priority_analysis: List[TestCasePriority] = Field(default_factory=list)
    critical_tests: List[str] = Field(default_factory=list, description="List of critical test IDs")
    
    # Coverage analysis
    coverage_by_module: Dict[str, CoverageMetrics] = Field(default_factory=dict)
    coverage_by_page: Dict[str, CoverageMetrics] = Field(default_factory=dict)
    overall_coverage: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Summary
    total_input_tests: int = Field(default=0)
    recommended_test_count: int = Field(default=0)
    analysis_timestamp: datetime = Field(default_factory=datetime.now)


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
    checkpoint_name: str = Field(..., description="A, B, C, D1, D2, D3, or D4")
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
    checkpoint_c: Optional[CheckpointResult] = Field(None, description="Pytest collection")
    
    # Granular D checkpoints
    checkpoint_d1: Optional[CheckpointResult] = Field(None, description="Page object structure validation")
    checkpoint_d2: Optional[CheckpointResult] = Field(None, description="Method contract validation")
    checkpoint_d3: Optional[CheckpointResult] = Field(None, description="Method signature validation")
    checkpoint_d4: Optional[CheckpointResult] = Field(None, description="Test execution")
    
    # Backward compatibility: checkpoint_d maps to checkpoint_d4
    checkpoint_d: Optional[CheckpointResult] = Field(None, description="Test execution (deprecated, use checkpoint_d4)")
    
    # Overall
    all_passed: bool = Field(default=False)
    
    # Recovery tracking
    recovery_attempts: int = Field(default=0)
    files_recovered: List[str] = Field(default_factory=list)
    
    def calculate_all_passed(self) -> bool:
        """Check if all checkpoints passed."""
        checkpoints = [
            self.checkpoint_a, self.checkpoint_b, self.checkpoint_c,
            self.checkpoint_d1, self.checkpoint_d2, self.checkpoint_d3, self.checkpoint_d4
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
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    
    # Cost (approximate, in USD)
    input_cost: float = Field(default=0.0, description="Cost for input tokens (USD)")
    output_cost: float = Field(default=0.0, description="Cost for output tokens (USD)")
    total_cost: float = Field(default=0.0, description="Total approximate cost (USD)")
    model_id: str = Field(default="us.anthropic.claude-opus-4-5-20251101-v1:0", description="Model used for pricing")
    
    # Test execution results
    test_execution_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Test execution details from checkpoint D4"
    )
    tests_passed_count: int = Field(default=0, description="Number of tests that passed")
    tests_failed_count: int = Field(default=0, description="Number of tests that failed")
    test_status: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Individual test status: [{test_name, status, error}]"
    )
    
    # Verification errors summary
    verification_errors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of all verification errors by checkpoint"
    )
    
    # Timing
    duration_seconds: Optional[float] = None


class TestCasePriority(BaseModel):
    """Test case with priority analysis."""
    test_id: str
    test_name: str
    current_priority: str
    recommended_priority: str
    priority_reason: str = Field(..., description="Why this priority is recommended")
    is_critical: bool = Field(default=False, description="Is this a critical test case")


class CoverageMetrics(BaseModel):
    """Coverage metrics for a module or page."""
    module_or_page: str
    total_test_cases: int
    coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    covered_scenarios: List[str] = Field(default_factory=list)
    missing_scenarios: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class TestCaseAnalysis(BaseModel):
    """Complete test case analysis results."""
    # Duplicate detection
    duplicates: List[DuplicateTestCase] = Field(default_factory=list)
    duplicate_count: int = Field(default=0)
    efficient_test_count: int = Field(default=0)
    
    # Suggested test cases
    suggested_tests: List[SuggestedTestCase] = Field(default_factory=list)
    
    # Priority analysis
    priority_analysis: List[TestCasePriority] = Field(default_factory=list)
    critical_tests: List[str] = Field(default_factory=list, description="List of critical test IDs")
    
    # Coverage analysis
    coverage_by_module: Dict[str, CoverageMetrics] = Field(default_factory=dict)
    coverage_by_page: Dict[str, CoverageMetrics] = Field(default_factory=dict)
    overall_coverage: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Summary
    total_input_tests: int = Field(default=0)
    recommended_test_count: int = Field(default=0)
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    
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
            f"| Tests Passed | {self.tests_passed_count} |",
            f"| Tests Failed | {self.tests_failed_count} |",
            f"| LLM Calls | {self.llm_calls} |",
            f"| Total Tokens | {self.total_tokens:,} |",
            f"| Input Tokens | {self.input_tokens:,} |",
            f"| Output Tokens | {self.output_tokens:,} |",
            f"| **Total Cost (Approx.)** | **${self.total_cost:.4f}** |",
            f"|   - Input Cost | ${self.input_cost:.4f} |",
            f"|   - Output Cost | ${self.output_cost:.4f} |",
            f"",
        ]
        
        # Add Verification Checkpoints section
        if self.checkpoints_summary:
            lines.extend([
                f"## Verification Checkpoints",
                f"",
                f"| Checkpoint | Status |",
                f"|------------|--------|",
            ])
            for cp_name, cp_status in sorted(self.checkpoints_summary.items()):
                status_icon = "✅" if cp_status == "passed" else "❌" if cp_status == "failed" else "⏭️"
                lines.append(f"| {cp_name} | {status_icon} {cp_status} |")
            lines.append("")
        
        # Add Test Status section
        if self.test_status:
            lines.extend([
                f"## Test Execution Status",
                f"",
                f"**Total:** {self.tests_passed_count} passed, {self.tests_failed_count} failed",
                f"",
                f"| Test Name | Status | Error Type |",
                f"|-----------|--------|------------|",
            ])
            for test in self.test_status:
                status = test.get("status", "unknown")
                if status == "passed":
                    status_icon = "✅"
                elif status == "failed":
                    status_icon = "❌"
                else:
                    status_icon = "⏭️"  # not_run or other
                error_type = test.get("error_type", "N/A")
                lines.append(f"| `{test.get('test_name', 'unknown')}` | {status_icon} {status} | {error_type} |")
            lines.append("")
            
            # Add detailed errors for failed tests
            failed_tests = [t for t in self.test_status if t.get("status") == "failed"]
            if failed_tests:
                lines.extend([
                    f"### Failed Test Details",
                    f"",
                ])
                for test in failed_tests:
                    lines.extend([
                        f"#### {test.get('test_name', 'unknown')}",
                        f"",
                        f"**File:** `{test.get('file', 'unknown')}`",
                        f"**Error Type:** {test.get('error_type', 'Unknown')}",
                        f"",
                        f"```",
                        test.get("error_summary", "No error details available"),
                        f"```",
                        f"",
                    ])
        
        # Add Verification Errors section
        if self.verification_errors:
            lines.extend([
                f"## Verification Errors",
                f"",
            ])
            for checkpoint_name, error_info in self.verification_errors.items():
                lines.extend([
                    f"### Checkpoint {checkpoint_name}",
                    f"",
                    f"- **Status:** {error_info.get('status', 'unknown')}",
                    f"- **Files Failed:** {len(error_info.get('files_failed', []))}",
                    f"- **Error Count:** {error_info.get('error_count', 0)}",
                    f"",
                ])
                if error_info.get("errors"):
                    lines.append("**Errors:**")
                    for filepath, error_msg in list(error_info.get("errors", {}).items())[:5]:
                        error_preview = str(error_msg)[:300] + ("..." if len(str(error_msg)) > 300 else "")
                        lines.extend([
                            f"- **{filepath}:**",
                            f"  ```",
                            error_preview,
                            f"  ```",
                            f"",
                        ])
        
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
