"""Onboarding Node - Validates and loads input files.

This node:
1. Checks if required input files exist
2. Loads and validates module_spec.json
3. Loads and validates testcases.csv (or generates if missing)
4. Loads and validates element_metadata/*.json (or generates if missing)
5. Sets flags for human review if inputs were auto-generated
"""

import logging
import os
from typing import Dict, List, Any, Optional, Tuple

from ..models.state import AgentState
from ..models.schemas import ModuleSpec, TestCaseRow, PageMetadata
from ..parsers.module_parser import ModuleParser
from ..parsers.csv_parser import CSVParser
from ..parsers.element_parser import ElementParser
from ..tools.testcase_analyzer import TestCaseAnalyzer
from ..utils.scratchpad import AgentScratchpad

logger = logging.getLogger(__name__)


class OnboardingError(Exception):
    """Raised when onboarding fails."""
    pass


def _check_inputs_exist(inputs_path: str) -> Dict[str, bool]:
    """
    Check which input files exist.
    
    Args:
        inputs_path: Path to inputs directory
        
    Returns:
        Dict with existence status for each input type
    """
    status = {
        "module_spec": False,
        "testcases": False,
        "element_metadata": False,
        "element_files": []
    }
    
    # Check module_spec.json
    module_spec_path = os.path.join(inputs_path, "module_spec.json")
    status["module_spec"] = os.path.exists(module_spec_path)
    
    # Check testcases.csv
    testcases_path = os.path.join(inputs_path, "testcases.csv")
    status["testcases"] = os.path.exists(testcases_path)
    
    # Check element_metadata directory
    element_dir = os.path.join(inputs_path, "element_metadata")
    if os.path.isdir(element_dir):
        json_files = [f for f in os.listdir(element_dir) if f.endswith('.json')]
        status["element_metadata"] = len(json_files) > 0
        status["element_files"] = json_files
    
    return status


def _load_module_spec(inputs_path: str) -> Tuple[ModuleSpec, List[str]]:
    """
    Load and validate module_spec.json.
    
    Args:
        inputs_path: Path to inputs directory
        
    Returns:
        Tuple of (ModuleSpec, list of warnings)
    """
    warnings = []
    parser = ModuleParser()
    
    module_spec_path = os.path.join(inputs_path, "module_spec.json")
    module_spec = parser.parse(module_spec_path)
    
    # Validation warnings
    if not module_spec.pages:
        warnings.append("No pages defined in module_spec.json")
    
    if not module_spec.app_url:
        warnings.append("No app_url defined in module_spec.json")
    
    return module_spec, warnings


def _load_test_cases(inputs_path: str) -> Tuple[List[TestCaseRow], List[str]]:
    """
    Load and validate testcases.csv.
    
    Args:
        inputs_path: Path to inputs directory
        
    Returns:
        Tuple of (list of TestCaseRow, list of warnings)
    """
    warnings = []
    parser = CSVParser()
    
    testcases_path = os.path.join(inputs_path, "testcases.csv")
    test_cases = parser.parse(testcases_path)
    
    # Validation warnings
    if not test_cases:
        warnings.append("No test cases found in testcases.csv")
    
    # Check for missing pages
    pages_used = set(tc.page_name for tc in test_cases if tc.page_name)
    logger.info(f"Test cases reference pages: {pages_used}")
    
    return test_cases, warnings


def _load_element_metadata(inputs_path: str) -> Tuple[Dict[str, PageMetadata], List[str]]:
    """
    Load and validate element_metadata/*.json files.
    
    Args:
        inputs_path: Path to inputs directory
        
    Returns:
        Tuple of (dict of page_name -> PageMetadata, list of warnings)
    """
    warnings = []
    parser = ElementParser()
    
    element_dir = os.path.join(inputs_path, "element_metadata")
    
    if not os.path.isdir(element_dir):
        return {}, ["element_metadata directory not found"]
    
    page_metadata = parser.parse_directory(element_dir)
    
    # Validation
    if not page_metadata:
        warnings.append("No element metadata files found")
    
    # Check for unstable selectors
    for page_name, page in page_metadata.items():
        unstable = parser.find_unstable_selectors(page)
        if unstable:
            for selector_info in unstable:
                warnings.append(
                    f"Unstable selector in {page_name}: {selector_info['element']} "
                    f"uses {selector_info['selector_type']}"
                )
    
    return page_metadata, warnings


def onboarding_node(state: AgentState) -> AgentState:
    """
    Onboarding node - loads and validates all inputs.
    
    This is the first node in the agent pipeline.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with loaded inputs
    """
    logger.info("=" * 60)
    logger.info("ONBOARDING NODE")
    logger.info("=" * 60)
    
    inputs_path = state.get("inputs_path", "")
    errors = []
    warnings = []
    
    # Track what was generated
    generated_elements = False
    generated_testcases = False
    
    # Update current node
    state["current_node"] = "onboarding"
    state["node_history"] = state.get("node_history", []) + ["onboarding"]
    
    # Step 1: Check what exists
    logger.info(f"Checking inputs at: {inputs_path}")
    input_status = _check_inputs_exist(inputs_path)
    
    logger.info(f"  module_spec.json: {'✓' if input_status['module_spec'] else '✗'}")
    logger.info(f"  testcases.csv: {'✓' if input_status['testcases'] else '✗'}")
    logger.info(f"  element_metadata/: {'✓' if input_status['element_metadata'] else '✗'}")
    
    # Step 2: Load module_spec.json (REQUIRED)
    if not input_status["module_spec"]:
        errors.append("module_spec.json is required but not found")
        state["input_validation_errors"] = errors
        state["errors"] = state.get("errors", []) + errors
        logger.error("ONBOARDING FAILED: module_spec.json required")
        return state
    
    try:
        module_spec, spec_warnings = _load_module_spec(inputs_path)
        warnings.extend(spec_warnings)
        state["module_spec"] = module_spec.model_dump()
        logger.info(f"Loaded module_spec: {module_spec.module_name}")
    except Exception as e:
        errors.append(f"Failed to load module_spec.json: {e}")
        state["input_validation_errors"] = errors
        logger.error(f"ONBOARDING FAILED: {e}")
        return state
    
    # Step 3: Load testcases.csv (or flag for generation)
    test_cases_loaded = []
    if input_status["testcases"]:
        try:
            test_cases_loaded, tc_warnings = _load_test_cases(inputs_path)
            warnings.extend(tc_warnings)
            state["test_cases"] = [tc.model_dump() for tc in test_cases_loaded]
            logger.info(f"Loaded {len(test_cases_loaded)} test cases")
        except Exception as e:
            warnings.append(f"Failed to load testcases.csv: {e}")
            state["test_cases"] = []
            generated_testcases = True
    else:
        logger.info("testcases.csv not found - will need generation")
        state["test_cases"] = []
        generated_testcases = True
    
    # Step 3.5: Initialize scratchpad
    output_path = state.get("output_path", "")
    if output_path:
        scratchpad = AgentScratchpad(output_path)
        scratchpad.initialize(state)
        state["scratchpad"] = scratchpad
        logger.info("Initialized agent scratchpad")
    else:
        logger.warning("No output_path - skipping scratchpad initialization")
    
    # Step 3.6: Perform test case analysis if we have test cases
    if test_cases_loaded and len(test_cases_loaded) > 0:
        logger.info("=" * 60)
        logger.info("TEST CASE ANALYSIS")
        logger.info("=" * 60)
        
        try:
            # Initialize LLM for analysis
            from ..llm.bedrock_client import BedrockClient
            llm = BedrockClient(
                model_id=state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
                region_name=state.get("llm_region", "us-east-2"),
                profile_name=state.get("llm_profile", "bedrock-user"),
                max_tokens=16384
            )
            
            analyzer = TestCaseAnalyzer(llm)
            analysis = analyzer.analyze_test_cases(
                test_cases=test_cases_loaded,
                module_spec=state.get("module_spec", {}),
                page_metadata=state.get("page_metadata", {})
            )
            
            # Store analysis results
            state["test_case_analysis"] = analysis.model_dump()
            state["node_history"] = state.get("node_history", []) + ["test_analysis"]
            
            # Flag if test case modifications are needed (duplicates or suggestions)
            has_duplicates = analysis.duplicate_count > 0
            has_suggestions = len(analysis.suggested_tests) > 0
            state["needs_test_case_review"] = has_duplicates or has_suggestions
            
            # Add to scratchpad
            scratchpad = state.get("scratchpad")
            if scratchpad:
                scratchpad.add_test_analysis(analysis.model_dump())
            
            # Log summary
            logger.info("-" * 40)
            logger.info("ANALYSIS SUMMARY")
            logger.info(f"  Total input tests: {analysis.total_input_tests}")
            logger.info(f"  Duplicates found: {analysis.duplicate_count}")
            logger.info(f"  Efficient test count: {analysis.efficient_test_count}")
            logger.info(f"  Suggested tests: {len(analysis.suggested_tests)}")
            logger.info(f"  Recommended test count: {analysis.recommended_test_count}")
            logger.info(f"  Overall coverage: {analysis.overall_coverage:.1f}%")
            logger.info(f"  Critical tests: {len(analysis.critical_tests)}")
            logger.info("-" * 40)
            
            # Log duplicates
            if analysis.duplicates:
                logger.warning("DUPLICATE TEST CASES:")
                for dup in analysis.duplicates[:5]:
                    logger.warning(
                        f"  ⚠ {dup.test_id} duplicates {dup.duplicate_of} "
                        f"(similarity: {dup.similarity_score:.2f})"
                    )
                if len(analysis.duplicates) > 5:
                    logger.warning(f"  ... and {len(analysis.duplicates) - 5} more")
            
            # Log suggested tests
            if analysis.suggested_tests:
                logger.info("SUGGESTED TEST CASES:")
                for sug in analysis.suggested_tests[:5]:
                    logger.info(
                        f"  + {sug.test_id}: {sug.test_name} "
                        f"(Priority: {sug.priority}, Gap: {sug.coverage_gap})"
                    )
                if len(analysis.suggested_tests) > 5:
                    logger.info(f"  ... and {len(analysis.suggested_tests) - 5} more")
            
            # Log priority changes
            priority_changes = [
                p for p in analysis.priority_analysis 
                if p.current_priority != p.recommended_priority
            ]
            if priority_changes:
                logger.info("PRIORITY RECOMMENDATIONS:")
                for pc in priority_changes[:5]:
                    logger.info(
                        f"  {pc.test_id}: {pc.current_priority} → {pc.recommended_priority} "
                        f"({pc.priority_reason})"
                    )
                if len(priority_changes) > 5:
                    logger.info(f"  ... and {len(priority_changes) - 5} more")
            
            # Log coverage by module
            if analysis.coverage_by_module:
                logger.info("COVERAGE BY MODULE:")
                for module, metrics in list(analysis.coverage_by_module.items())[:3]:
                    logger.info(
                        f"  {module}: {metrics.coverage_percentage:.1f}% "
                        f"({metrics.total_test_cases} tests)"
                    )
                    if metrics.missing_scenarios:
                        logger.info(f"    Missing: {', '.join(metrics.missing_scenarios[:3])}")
            
            # Update LLM usage
            usage = llm.get_usage_stats()
            state["llm_calls"] = state.get("llm_calls", 0) + usage["call_count"]
            state["llm_input_tokens"] = state.get("llm_input_tokens", 0) + usage["total_input_tokens"]
            state["llm_output_tokens"] = state.get("llm_output_tokens", 0) + usage["total_output_tokens"]
            
        except Exception as e:
            logger.warning(f"Test case analysis failed: {e}")
            warnings.append(f"Test case analysis failed: {e}")
            state["test_case_analysis"] = None
    
    # Step 4: Load element_metadata (or flag for generation)
    if input_status["element_metadata"]:
        try:
            page_metadata, elem_warnings = _load_element_metadata(inputs_path)
            warnings.extend(elem_warnings)
            state["page_metadata"] = {
                name: page.model_dump() for name, page in page_metadata.items()
            }
            logger.info(f"Loaded element metadata for {len(page_metadata)} pages")
        except Exception as e:
            warnings.append(f"Failed to load element_metadata: {e}")
            state["page_metadata"] = {}
            generated_elements = True
    else:
        logger.info("element_metadata/ not found - will need generation")
        state["page_metadata"] = {}
        generated_elements = True
    
    # Step 5: Set generation flags
    state["generated_elements"] = generated_elements
    state["generated_testcases"] = generated_testcases
    state["inputs_generated"] = generated_elements or generated_testcases
    state["needs_input_review"] = generated_elements or generated_testcases
    
    # Step 6: Store validation results
    state["input_validation_errors"] = errors
    state["input_validation_warnings"] = warnings
    
    # Log summary
    logger.info("-" * 40)
    logger.info("ONBOARDING SUMMARY")
    logger.info(f"  Module: {module_spec.module_name}")
    logger.info(f"  App URL: {module_spec.app_url}")
    logger.info(f"  Test cases: {len(state.get('test_cases', []))}")
    logger.info(f"  Pages: {len(state.get('page_metadata', {}))}")
    logger.info(f"  Errors: {len(errors)}")
    logger.info(f"  Warnings: {len(warnings)}")
    logger.info(f"  Needs input review: {state['needs_input_review']}")
    logger.info("-" * 40)
    
    if warnings:
        for w in warnings:
            logger.warning(f"  ⚠ {w}")
    
    return state
