"""Reporting Node - Generates final AI report and saves outputs.

This node:
1. Generates AI analysis report
2. Saves all generated files to disk
3. Creates Allure configuration
4. Outputs summary statistics
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from ..models.state import AgentState
from ..models.schemas import AIReport, SelectorRisk

logger = logging.getLogger(__name__)


def _analyze_selector_risks(state: AgentState) -> list:
    """
    Analyze page metadata for selector risks.
    
    Args:
        state: Current agent state
        
    Returns:
        List of SelectorRisk objects
    """
    risks = []
    page_metadata = state.get("page_metadata", {})
    
    for page_name, page in page_metadata.items():
        for elem in page.get("elements", []):
            elem_name = elem.get("name", "unknown")
            
            for selector in elem.get("selectors", []):
                selector_type = selector.get("selector_type", "")
                value = selector.get("value", "")
                is_stable = selector.get("is_stable", True)
                
                # Check for risky selectors
                risk_reason = None
                suggestion = None
                
                if not is_stable:
                    risk_reason = "Marked as unstable"
                    suggestion = "Replace with id, data-testid, or name attribute"
                elif selector_type in ["css", "xpath"]:
                    # Check for fragile patterns
                    if ":nth-child" in value or "[class=" in value:
                        risk_reason = "Uses fragile CSS/class selector"
                        suggestion = "Request stable ID from developers"
                    elif "//" in value and "[@id" not in value:
                        risk_reason = "Complex XPath without ID anchor"
                        suggestion = "Simplify XPath or use data-testid"
                
                if risk_reason:
                    risks.append(SelectorRisk(
                        file_name=f"pages/{page_name.lower()}.py",
                        element_name=elem_name,
                        selector_type=selector_type,
                        selector_value=value,
                        risk_reason=risk_reason,
                        suggestion=suggestion
                    ))
    
    return risks


def _generate_recommendations(state: AgentState) -> list:
    """
    Generate recommendations based on analysis.
    
    Args:
        state: Current agent state
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Check verification status
    if not state.get("verification_passed", False):
        recommendations.append(
            "Review and fix verification failures before running tests"
        )
    
    # Check for recovery attempts
    if state.get("recovery_attempts", 0) > 0:
        recommendations.append(
            f"Code required {state['recovery_attempts']} recovery attempts - "
            "review generated code quality"
        )
    
    # Check test coverage
    test_cases = state.get("test_cases", [])
    plan = state.get("generation_plan", {})
    tests_generated = len(plan.get("tests", []))
    
    if tests_generated < len(test_cases):
        recommendations.append(
            f"Only {tests_generated}/{len(test_cases)} test cases were generated - "
            "review planning output"
        )
    
    # Check for missing pages
    page_metadata = state.get("page_metadata", {})
    pages_generated = len(plan.get("pages", []))
    
    if pages_generated < len(page_metadata):
        recommendations.append(
            f"Only {pages_generated}/{len(page_metadata)} page objects generated"
        )
    
    # Add general recommendations
    if not recommendations:
        recommendations.append("All checks passed - code is ready for execution")
        recommendations.append("Run pytest to execute generated tests")
        recommendations.append("Review and customize generated page objects as needed")
    
    return recommendations


def _save_files_to_disk(
    generated_files: Dict[str, str],
    output_path: str
) -> list:
    """
    Save all generated files to disk.
    
    Args:
        generated_files: Dict of filepath -> content
        output_path: Base output directory
        
    Returns:
        List of saved file paths
    """
    saved_files = []
    
    for filepath, content in generated_files.items():
        full_path = os.path.join(output_path, filepath)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        saved_files.append(full_path)
        logger.debug(f"Saved: {full_path}")
    
    return saved_files


def _create_allure_config(output_path: str, module_name: str):
    """
    Create Allure configuration files.
    
    Args:
        output_path: Output directory
        module_name: Module name for labels
    """
    # Create allure results directory
    allure_dir = os.path.join(output_path, "allure-results")
    os.makedirs(allure_dir, exist_ok=True)
    
    # Create environment.properties
    env_props = f"""# Allure Environment
app.name={module_name}
generated.by=Web UI Test Generation Agent
generated.at={datetime.now().isoformat()}
"""
    with open(os.path.join(allure_dir, "environment.properties"), 'w') as f:
        f.write(env_props)
    
    # Create categories.json
    categories = [
        {
            "name": "Product defects",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*AssertionError.*"
        },
        {
            "name": "Test defects",
            "matchedStatuses": ["broken"],
            "messageRegex": ".*"
        },
        {
            "name": "Passed tests",
            "matchedStatuses": ["passed"]
        }
    ]
    with open(os.path.join(allure_dir, "categories.json"), 'w') as f:
        json.dump(categories, f, indent=2)


def reporting_node(state: AgentState) -> AgentState:
    """
    Reporting node - generates final report and saves outputs.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with report
    """
    logger.info("=" * 60)
    logger.info("REPORTING NODE")
    logger.info("=" * 60)
    
    state["current_node"] = "reporting"
    state["node_history"] = state.get("node_history", []) + ["reporting"]
    
    output_path = state.get("output_path", "")
    module_spec = state.get("module_spec", {})
    module_name = module_spec.get("module_name", "unknown")
    generated_files = state.get("generated_files", {})
    plan = state.get("generation_plan", {})
    
    # Save files to disk
    logger.info("Saving generated files...")
    saved_files = _save_files_to_disk(generated_files, output_path)
    
    # Analyze selector risks
    logger.info("Analyzing selector risks...")
    selector_risks = _analyze_selector_risks(state)
    
    # Generate recommendations
    logger.info("Generating recommendations...")
    recommendations = _generate_recommendations(state)
    
    # Create Allure config
    logger.info("Creating Allure configuration...")
    _create_allure_config(output_path, module_name)
    
    # Build AI Report
    report = AIReport(
        session_id=state.get("session_id", "unknown"),
        module_name=module_name,
        created_at=datetime.now(),
        files_generated=[os.path.basename(f) for f in saved_files],
        tests_generated=len(plan.get("tests", [])),
        pages_generated=len(plan.get("pages", [])),
        flows_generated=len(plan.get("flows", [])),
        verification_passed=state.get("verification_passed", False),
        checkpoints_summary={
            "A": state.get("verification_results", {}).get("checkpoint_a", {}).get("status", "unknown"),
            "B": state.get("verification_results", {}).get("checkpoint_b", {}).get("status", "unknown"),
            "C": state.get("verification_results", {}).get("checkpoint_c", {}).get("status", "unknown"),
        },
        selector_risks=selector_risks,
        recommendations=recommendations,
        llm_calls=state.get("llm_calls", 0),
        total_tokens=state.get("llm_input_tokens", 0) + state.get("llm_output_tokens", 0),
        duration_seconds=None  # Could calculate from started_at
    )
    
    # Save report as JSON
    report_json_path = os.path.join(output_path, "ai_report.json")
    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump(report.model_dump(mode='json'), f, indent=2, default=str)
    
    # Save report as Markdown
    report_md_path = os.path.join(output_path, "ai_report.md")
    with open(report_md_path, 'w', encoding='utf-8') as f:
        f.write(report.to_markdown())
    
    # Update state
    state["ai_report"] = report.model_dump(mode='json')
    state["report_markdown"] = report.to_markdown()
    
    # Log summary
    logger.info("-" * 40)
    logger.info("REPORTING SUMMARY")
    logger.info(f"  Output directory: {output_path}")
    logger.info(f"  Files saved: {len(saved_files)}")
    logger.info(f"  Tests generated: {report.tests_generated}")
    logger.info(f"  Pages generated: {report.pages_generated}")
    logger.info(f"  Flows generated: {report.flows_generated}")
    logger.info(f"  Verification: {'PASSED' if report.verification_passed else 'FAILED'}")
    logger.info(f"  Selector risks: {len(selector_risks)}")
    logger.info(f"  LLM calls: {report.llm_calls}")
    logger.info(f"  Total tokens: {report.total_tokens:,}")
    logger.info("-" * 40)
    
    # Print recommendations
    logger.info("RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        logger.info(f"  {i}. {rec}")
    
    logger.info("=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info(f"Report saved to: {report_md_path}")
    logger.info("=" * 60)
    
    return state
