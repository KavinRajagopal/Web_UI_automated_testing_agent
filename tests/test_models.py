#!/usr/bin/env python3
"""
Test suite for Pydantic Models.

Verifies:
1. All models import correctly
2. Validation works as expected
3. Serialization to JSON works
4. Model relationships work
5. AgentState initializes correctly

Usage:
    python -m tests.test_models
    # or
    pytest tests/test_models.py -v
"""
import os
import sys
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.models import (
    # Input models
    ModuleSpec,
    PageConfig,
    TestCaseRow,
    
    # Element models
    SelectorType,
    ElementSelector,
    UIElement,
    PageMetadata,
    
    # Planning models
    PagePlan,
    FlowPlan,
    TestPlan,
    GenerationPlan,
    
    # Verification models
    CheckpointResult,
    VerificationResults,
    
    # Reporting models
    SelectorRisk,
    AIReport,
    
    # State
    AgentState,
)
from src.models.state import create_initial_state


def print_banner(text: str):
    """Print a formatted banner."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(msg: str):
    print(f"✓ {msg}")


def print_error(msg: str):
    print(f"✗ {msg}")


def test_module_spec():
    """Test ModuleSpec model."""
    print_banner("Test: ModuleSpec Model")
    
    try:
        spec = ModuleSpec(
            module_name="authentication",
            app_name="TringPlay",
            app_url="https://staging.tringplay.com",
            environment="staging",
            browser="chrome",
            selector_priority=["id", "data-testid", "name", "css"],
            avoid_selectors=["xpath"],
            pages=[
                PageConfig(
                    name="LoginPage",
                    url_pattern="/login",
                    element_metadata_file="login_elements.json"
                ),
                PageConfig(
                    name="HomePage",
                    url_pattern="/home"
                )
            ],
            description="Authentication module tests"
        )
        
        print_success(f"Created ModuleSpec: {spec.module_name}")
        print_success(f"  App: {spec.app_name}")
        print_success(f"  URL: {spec.app_url}")
        print_success(f"  Pages: {len(spec.pages)}")
        print_success(f"  Selector priority: {spec.selector_priority}")
        
        # Test serialization
        json_str = spec.model_dump_json(indent=2)
        print_success(f"  Serialized to JSON ({len(json_str)} chars)")
        
        return True
    except Exception as e:
        print_error(f"ModuleSpec test failed: {e}")
        return False


def test_test_case_row():
    """Test TestCaseRow model with pipe-delimited parsing."""
    print_banner("Test: TestCaseRow Model")
    
    try:
        # Simulate a row from CSV
        row = TestCaseRow(
            test_id="TC_LOGIN_001",
            test_name="Valid Login Test",
            module="authentication",
            priority="P0",
            preconditions="User is on login page",
            steps="Enter valid email|Enter valid password|Click login button",
            expected_result="User is redirected to home page",
            test_data="username=testuser@example.com|password=Test123!",
            tags="smoke,login,critical",
            page_name="LoginPage"
        )
        
        print_success(f"Created TestCaseRow: {row.test_id}")
        print_success(f"  Name: {row.test_name}")
        print_success(f"  Module: {row.module}")
        print_success(f"  Priority: {row.priority}")
        
        # Test step parsing
        steps = row.get_steps_list()
        print_success(f"  Parsed steps: {len(steps)}")
        for i, step in enumerate(steps, 1):
            print(f"    {i}. {step}")
        
        # Test data parsing
        test_data = row.get_test_data_dict()
        print_success(f"  Parsed test data: {test_data}")
        
        return True
    except Exception as e:
        print_error(f"TestCaseRow test failed: {e}")
        return False


def test_element_models():
    """Test Element, UIElement, PageMetadata models."""
    print_banner("Test: Element Models")
    
    try:
        # Create selectors
        id_selector = ElementSelector(
            selector_type=SelectorType.ID,
            value="email-input",
            confidence=1.0,
            is_stable=True
        )
        
        css_selector = ElementSelector(
            selector_type=SelectorType.CSS,
            value="input[name='email']",
            confidence=0.9,
            is_stable=True
        )
        
        # Unstable CSS module hash
        unstable_selector = ElementSelector(
            selector_type=SelectorType.CSS,
            value=".Input_primary__a1b2c3d4",
            confidence=0.5,
            is_stable=False
        )
        
        print_success(f"Created selectors: {id_selector.selector_type.value}, {css_selector.selector_type.value}")
        print_success(f"  CSS hash detected: {unstable_selector.is_css_module_hash()}")
        
        # Create UIElement
        element = UIElement(
            name="email_input",
            description="Email input field on login form",
            element_type="input",
            selectors=[id_selector, css_selector, unstable_selector],
            is_required=True,
            wait_strategy="visible"
        )
        
        print_success(f"Created UIElement: {element.name}")
        print_success(f"  Type: {element.element_type}")
        print_success(f"  Selectors: {len(element.selectors)}")
        
        best = element.get_best_selector()
        print_success(f"  Best selector: {best.selector_type.value} = {best.value}")
        
        # Create PageMetadata
        page = PageMetadata(
            page_name="LoginPage",
            page_url="/login",
            description="Login page for TringPlay",
            elements=[element],
            last_updated=datetime.now()
        )
        
        print_success(f"Created PageMetadata: {page.page_name}")
        print_success(f"  URL: {page.page_url}")
        print_success(f"  Elements: {len(page.elements)}")
        print_success(f"  Required elements: {len(page.get_required_elements())}")
        
        # Test JSON serialization
        json_str = page.model_dump_json(indent=2)
        print_success(f"  Serialized to JSON ({len(json_str)} chars)")
        
        return True
    except Exception as e:
        print_error(f"Element models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_planning_models():
    """Test GenerationPlan and related models."""
    print_banner("Test: Planning Models")
    
    try:
        plan = GenerationPlan(
            module_name="authentication",
            pages=[
                PagePlan(
                    page_name="LoginPage",
                    file_name="login_page.py",
                    elements=["email_input", "password_input", "login_button"],
                    methods=["enter_email", "enter_password", "click_login", "login"],
                    description="Login page object"
                ),
                PagePlan(
                    page_name="HomePage",
                    file_name="home_page.py",
                    elements=["welcome_message", "logout_button"],
                    methods=["get_welcome_text", "click_logout"]
                )
            ],
            flows=[
                FlowPlan(
                    flow_name="AuthFlow",
                    file_name="auth_flow.py",
                    pages_used=["LoginPage", "HomePage"],
                    methods=["login", "logout", "verify_logged_in"]
                )
            ],
            tests=[
                TestPlan(
                    test_id="TC_LOGIN_001",
                    test_name="test_valid_login",
                    flow_used="AuthFlow",
                    steps_summary=["Navigate to login", "Enter credentials", "Click login", "Verify home page"],
                    markers=["smoke", "critical"]
                ),
                TestPlan(
                    test_id="TC_LOGIN_002",
                    test_name="test_invalid_login",
                    flow_used="AuthFlow",
                    steps_summary=["Navigate to login", "Enter invalid credentials", "Verify error"],
                    markers=["negative"]
                )
            ],
            conftest_fixtures=["driver", "base_url", "test_user"],
            llm_model="claude-opus-4.5"
        )
        
        print_success(f"Created GenerationPlan: {plan.module_name}")
        print_success(f"  Pages: {len(plan.pages)}")
        print_success(f"  Flows: {len(plan.flows)}")
        print_success(f"  Tests: {len(plan.tests)}")
        print_success(f"  Total files: ~{plan.total_files}")
        
        print("\n  Plan Summary:")
        for line in plan.summary().split("\n"):
            print(f"    {line}")
        
        return True
    except Exception as e:
        print_error(f"Planning models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verification_models():
    """Test VerificationResults and CheckpointResult models."""
    print_banner("Test: Verification Models")
    
    try:
        # Checkpoint A: Syntax
        checkpoint_a = CheckpointResult(
            checkpoint_name="A",
            checkpoint_description="Syntax Check (AST parsing)",
            status="passed",
            files_checked=["login_page.py", "home_page.py", "auth_flow.py"],
            files_passed=["login_page.py", "home_page.py", "auth_flow.py"],
            files_failed=[],
            duration_seconds=0.5
        )
        
        # Checkpoint B: Imports
        checkpoint_b = CheckpointResult(
            checkpoint_name="B",
            checkpoint_description="Import Check",
            status="passed",
            files_checked=["login_page.py", "home_page.py"],
            files_passed=["login_page.py", "home_page.py"],
            files_failed=[],
            duration_seconds=1.2
        )
        
        # Checkpoint C: Mock execution
        checkpoint_c = CheckpointResult(
            checkpoint_name="C",
            checkpoint_description="Mock Execution (pytest --collect-only)",
            status="passed",
            files_checked=["test_authentication.py"],
            files_passed=["test_authentication.py"],
            files_failed=[],
            duration_seconds=2.1
        )
        
        results = VerificationResults(
            checkpoint_a=checkpoint_a,
            checkpoint_b=checkpoint_b,
            checkpoint_c=checkpoint_c,
            recovery_attempts=0
        )
        
        # Calculate overall pass status
        results.all_passed = results.calculate_all_passed()
        
        print_success(f"Created VerificationResults")
        print_success(f"  Checkpoint A: {checkpoint_a.status}")
        print_success(f"  Checkpoint B: {checkpoint_b.status}")
        print_success(f"  Checkpoint C: {checkpoint_c.status}")
        print_success(f"  All Passed: {results.all_passed}")
        
        return True
    except Exception as e:
        print_error(f"Verification models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_report():
    """Test AIReport model and markdown generation."""
    print_banner("Test: AIReport Model")
    
    try:
        report = AIReport(
            module_name="authentication",
            files_generated=[
                "pages/base_page.py",
                "pages/login_page.py",
                "pages/home_page.py",
                "flows/auth_flow.py",
                "tests/conftest.py",
                "tests/test_authentication.py"
            ],
            tests_generated=2,
            pages_generated=2,
            flows_generated=1,
            verification_passed=True,
            checkpoints_summary={
                "A": "PASSED (3/3 files)",
                "B": "PASSED (3/3 imports)",
                "C": "PASSED (2 tests collected)"
            },
            selector_risks=[
                SelectorRisk(
                    file_name="login_page.py",
                    element_name="submit_button",
                    selector_type="css",
                    selector_value=".Button_primary__a1b2c3",
                    risk_reason="CSS module hash may change on build",
                    suggestion="Request data-testid from developers"
                )
            ],
            recommendations=[
                "Add data-testid attributes to login form elements",
                "Consider adding explicit waits for dynamic content",
                "Run tests against staging before production"
            ],
            llm_calls=5,
            total_tokens=8500,
            duration_seconds=45.3
        )
        
        print_success(f"Created AIReport: {report.session_id}")
        print_success(f"  Module: {report.module_name}")
        print_success(f"  Files: {len(report.files_generated)}")
        print_success(f"  Tests: {report.tests_generated}")
        print_success(f"  Verification: {'PASSED' if report.verification_passed else 'FAILED'}")
        print_success(f"  Selector risks: {len(report.selector_risks)}")
        print_success(f"  LLM tokens: {report.total_tokens:,}")
        
        # Generate markdown
        markdown = report.to_markdown()
        print_success(f"  Generated markdown ({len(markdown)} chars)")
        
        print("\n  --- Markdown Preview (first 500 chars) ---")
        print(markdown[:500])
        print("  --- (truncated) ---")
        
        return True
    except Exception as e:
        print_error(f"AIReport test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_state():
    """Test AgentState initialization."""
    print_banner("Test: AgentState")
    
    try:
        state = create_initial_state(
            inputs_path="./inputs",
            output_path="./automation_repo",
            llm_model_id="us.anthropic.claude-opus-4-5-20251101-v1:0",
            llm_region="us-east-2",
            llm_profile="tring-kavin"
        )
        
        print_success("Created AgentState")
        print_success(f"  Session ID: {state['session_id']}")
        print_success(f"  Started at: {state['started_at']}")
        print_success(f"  Inputs path: {state['inputs_path']}")
        print_success(f"  Output path: {state['output_path']}")
        print_success(f"  LLM model: {state['llm_model_id'][:30]}...")
        print_success(f"  Max recovery: {state['max_recovery_attempts']}")
        
        # Verify all expected keys exist
        expected_keys = [
            'inputs_path', 'output_path', 'module_spec', 'test_cases',
            'generation_plan', 'generated_files', 'verification_results',
            'ai_report', 'llm_calls', 'errors'
        ]
        
        missing = [k for k in expected_keys if k not in state]
        if missing:
            print_error(f"Missing keys: {missing}")
            return False
        
        print_success(f"  All {len(expected_keys)} expected keys present")
        
        return True
    except Exception as e:
        print_error(f"AgentState test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_selector_stability():
    """Test selector stability ordering."""
    print_banner("Test: Selector Stability Order")
    
    try:
        order = SelectorType.stability_order()
        
        print_success("Selector stability order (best first):")
        for i, selector_type in enumerate(order, 1):
            print(f"    {i}. {selector_type.value}")
        
        # Verify ID is most stable, XPath is least
        assert order[0] == SelectorType.ID, "ID should be first"
        assert order[-1] == SelectorType.XPATH, "XPath should be last"
        
        print_success("Verified: ID is most stable, XPath is least")
        
        return True
    except Exception as e:
        print_error(f"Selector stability test failed: {e}")
        return False


def main():
    """Run all Pydantic model tests."""
    print("\n" + "=" * 60)
    print("  PYDANTIC MODELS TESTS")
    print("  TringPlay Web UI Test Generation Agent")
    print("=" * 60)
    
    results = []
    
    results.append(("ModuleSpec", test_module_spec()))
    results.append(("TestCaseRow", test_test_case_row()))
    results.append(("Element Models", test_element_models()))
    results.append(("Planning Models", test_planning_models()))
    results.append(("Verification Models", test_verification_models()))
    results.append(("AIReport", test_ai_report()))
    results.append(("AgentState", test_agent_state()))
    results.append(("Selector Stability", test_selector_stability()))
    
    # Summary
    print_banner("TEST RESULTS")
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n" + "=" * 60)
        print("  ✓ ALL MODEL TESTS PASSED")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  ✗ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
