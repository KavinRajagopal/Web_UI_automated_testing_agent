#!/usr/bin/env python3
"""
Test suite for Input Parsers.

Verifies:
1. ModuleParser loads module_spec.json correctly
2. CSVParser loads testcases.csv correctly
3. ElementParser loads element_metadata/*.json correctly
4. All parsers handle errors gracefully
5. Summary and validation methods work

Usage:
    python -m tests.test_parsers
    # or
    pytest tests/test_parsers.py -v
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.parsers import ModuleParser, CSVParser, ElementParser


# Paths to sample inputs
INPUTS_DIR = Path(PROJECT_ROOT) / "inputs"
MODULE_SPEC_PATH = INPUTS_DIR / "module_spec.json"
TESTCASES_PATH = INPUTS_DIR / "testcases.csv"
ELEMENT_METADATA_DIR = INPUTS_DIR / "element_metadata"


def print_banner(text: str):
    """Print a formatted banner."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(msg: str):
    print(f"✓ {msg}")


def print_error(msg: str):
    print(f"✗ {msg}")


def test_module_parser():
    """Test ModuleParser with module_spec.json."""
    print_banner("Test: ModuleParser")
    
    try:
        # Parse module spec
        spec = ModuleParser.parse(MODULE_SPEC_PATH)
        
        print_success(f"Parsed module: {spec.module_name}")
        print_success(f"  App: {spec.app_name}")
        print_success(f"  URL: {spec.app_url}")
        print_success(f"  Environment: {spec.environment}")
        print_success(f"  Browser: {spec.browser}")
        print_success(f"  Pages: {len(spec.pages)}")
        
        for page in spec.pages:
            print(f"    - {page.name} ({page.url_pattern})")
        
        print_success(f"  Selector priority: {spec.selector_priority}")
        print_success(f"  Avoid selectors: {spec.avoid_selectors}")
        
        # Test validation
        warnings = ModuleParser.validate(MODULE_SPEC_PATH)
        if warnings:
            print(f"  Warnings: {len(warnings)}")
            for w in warnings:
                print(f"    ⚠ {w}")
        else:
            print_success("  No validation warnings")
        
        return True
    except Exception as e:
        print_error(f"ModuleParser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_csv_parser():
    """Test CSVParser with testcases.csv."""
    print_banner("Test: CSVParser")
    
    try:
        # Parse all test cases
        test_cases = CSVParser.parse(TESTCASES_PATH)
        
        print_success(f"Parsed {len(test_cases)} test cases")
        
        for tc in test_cases:
            print(f"\n  {tc.test_id}: {tc.test_name}")
            print(f"    Module: {tc.module}, Priority: {tc.priority}")
            
            steps = tc.get_steps_list()
            print(f"    Steps: {len(steps)}")
            for i, step in enumerate(steps, 1):
                print(f"      {i}. {step[:50]}{'...' if len(step) > 50 else ''}")
            
            test_data = tc.get_test_data_dict()
            if test_data:
                print(f"    Test data: {list(test_data.keys())}")
        
        # Test module filter
        auth_cases = CSVParser.parse(TESTCASES_PATH, module_filter="authentication")
        print_success(f"\nFiltered by 'authentication': {len(auth_cases)} cases")
        
        # Test get_modules
        modules = CSVParser.get_modules(TESTCASES_PATH)
        print_success(f"Unique modules: {modules}")
        
        # Test summary
        summary = CSVParser.get_summary(TESTCASES_PATH)
        print_success(f"Summary:")
        print(f"    Total: {summary['total_test_cases']} test cases")
        print(f"    Modules: {summary['modules']}")
        print(f"    Priorities: {summary['priorities']}")
        
        return True
    except Exception as e:
        print_error(f"CSVParser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_element_parser():
    """Test ElementParser with element_metadata/*.json."""
    print_banner("Test: ElementParser")
    
    try:
        # Parse single file
        login_page = ElementParser.parse(ELEMENT_METADATA_DIR / "login_elements.json")
        
        print_success(f"Parsed page: {login_page.page_name}")
        print_success(f"  URL: {login_page.page_url}")
        print_success(f"  Elements: {len(login_page.elements)}")
        
        for elem in login_page.elements:
            best_selector = elem.get_best_selector()
            print(f"\n    {elem.name} ({elem.element_type})")
            print(f"      Required: {elem.is_required}")
            print(f"      Selectors: {len(elem.selectors)}")
            if best_selector:
                print(f"      Best: {best_selector.selector_type.value} = {best_selector.value[:40]}...")
        
        # Parse all files in directory
        print("\n" + "-" * 40)
        all_pages = ElementParser.parse_directory(ELEMENT_METADATA_DIR)
        
        print_success(f"Parsed {len(all_pages)} pages from directory")
        for page_name, page in all_pages.items():
            required = page.get_required_elements()
            print(f"    {page_name}: {len(page.elements)} elements ({len(required)} required)")
        
        # Test unstable selector detection
        print("\n" + "-" * 40)
        print_success("Checking for unstable selectors...")
        
        for page_name, page in all_pages.items():
            risks = ElementParser.find_unstable_selectors(page)
            if risks:
                print(f"\n  {page_name}: {len(risks)} risks found")
                for risk in risks[:3]:  # Show first 3
                    print(f"    ⚠ {risk['element_name']}: {risk['risk_reason']}")
            else:
                print(f"  {page_name}: No unstable selectors found")
        
        # Test summary
        print("\n" + "-" * 40)
        summary = ElementParser.get_summary(ELEMENT_METADATA_DIR)
        print_success(f"Summary:")
        print(f"    Pages: {summary['total_pages']}")
        print(f"    Elements: {summary['total_elements']}")
        print(f"    Selectors: {summary['total_selectors']}")
        print(f"    Selector types: {summary['selector_types']}")
        
        return True
    except Exception as e:
        print_error(f"ElementParser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling for missing files."""
    print_banner("Test: Error Handling")
    
    passed = True
    
    # Test missing module spec
    try:
        ModuleParser.parse("/nonexistent/path/module_spec.json")
        print_error("Expected FileNotFoundError for missing module spec")
        passed = False
    except FileNotFoundError:
        print_success("ModuleParser raises FileNotFoundError for missing file")
    
    # Test missing CSV
    try:
        CSVParser.parse("/nonexistent/path/testcases.csv")
        print_error("Expected FileNotFoundError for missing CSV")
        passed = False
    except FileNotFoundError:
        print_success("CSVParser raises FileNotFoundError for missing file")
    
    # Test missing element metadata
    try:
        ElementParser.parse("/nonexistent/path/elements.json")
        print_error("Expected FileNotFoundError for missing element metadata")
        passed = False
    except FileNotFoundError:
        print_success("ElementParser raises FileNotFoundError for missing file")
    
    return passed


def test_integration():
    """Test integration: load all inputs as the Onboarding node would."""
    print_banner("Test: Integration (Onboarding Simulation)")
    
    try:
        # 1. Load module spec
        spec = ModuleParser.parse(MODULE_SPEC_PATH)
        print_success(f"Loaded module: {spec.module_name}")
        
        # 2. Load test cases for this module
        test_cases = CSVParser.parse(TESTCASES_PATH, module_filter=spec.module_name)
        print_success(f"Loaded {len(test_cases)} test cases for module")
        
        # 3. Load element metadata for pages in spec
        page_metadata = {}
        for page_config in spec.pages:
            if page_config.element_metadata_file:
                file_path = ELEMENT_METADATA_DIR / page_config.element_metadata_file
                if file_path.exists():
                    page = ElementParser.parse(file_path)
                    page_metadata[page.page_name] = page
                    print_success(f"Loaded metadata for {page.page_name}")
                else:
                    print(f"  ⚠ Missing: {page_config.element_metadata_file}")
        
        # 4. Summary
        print("\n" + "-" * 40)
        print_success("Integration Summary:")
        print(f"    Module: {spec.module_name}")
        print(f"    Test cases: {len(test_cases)}")
        print(f"    Pages with metadata: {len(page_metadata)}")
        
        total_elements = sum(len(p.elements) for p in page_metadata.values())
        print(f"    Total elements: {total_elements}")
        
        # Check coverage: do test cases reference pages we have metadata for?
        test_pages = set(tc.page_name for tc in test_cases if tc.page_name)
        metadata_pages = set(page_metadata.keys())
        
        covered = test_pages & metadata_pages
        uncovered = test_pages - metadata_pages
        
        print(f"    Page coverage: {len(covered)}/{len(test_pages)}")
        if uncovered:
            print(f"    ⚠ Missing metadata for: {uncovered}")
        
        return True
    except Exception as e:
        print_error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all parser tests."""
    print("\n" + "=" * 60)
    print("  INPUT PARSERS TESTS")
    print("  TringPlay Web UI Test Generation Agent")
    print("=" * 60)
    
    # Check inputs directory exists
    if not INPUTS_DIR.exists():
        print_error(f"Inputs directory not found: {INPUTS_DIR}")
        print("Please create sample input files first.")
        sys.exit(1)
    
    results = []
    
    results.append(("ModuleParser", test_module_parser()))
    results.append(("CSVParser", test_csv_parser()))
    results.append(("ElementParser", test_element_parser()))
    results.append(("Error Handling", test_error_handling()))
    results.append(("Integration", test_integration()))
    
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
        print("  ✓ ALL PARSER TESTS PASSED")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  ✗ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
