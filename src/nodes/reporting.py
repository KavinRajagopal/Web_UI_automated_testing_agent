"""Reporting Node - Generates final AI report and saves outputs.

This node:
1. Generates AI analysis report
2. Saves all generated files to disk
3. Creates Allure configuration
4. Saves event log (JSON trace of all events)
5. Outputs summary statistics
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from ..models.state import AgentState
from ..models.schemas import (
    AIReport, SelectorRisk, PlanningSection, DuplicateAnalysisSection,
    PriorityStackingSection, CoverageSection, RecoveryLogEntry,
    RecoveryLogSection, FinalSummarySection
)
from ..utils.cost_calculator import calculate_cost
from ..utils.event_logger import add_event_to_state
from typing import List, Optional

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


# =============================================================================
# ENHANCED REPORT SECTION BUILDERS
# =============================================================================

def _build_planning_section(state: AgentState) -> Optional[PlanningSection]:
    """Build planning section from analysis_summary. Returns None on error."""
    try:
        analysis = state.get("analysis_summary", {})
        if not analysis:
            return None

        return PlanningSection(
            total_test_cases_in_csv=analysis.get("total_tests", 0),
            selected_test_count=analysis.get("selected_count", 0),
            max_test_cap=analysis.get("capped_at", 10),
            selection_reason=f"Priority order P0 > P1 > P2, capped at {analysis.get('capped_at', 10)} tests"
        )
    except Exception as e:
        logger.warning(f"Failed to build planning section: {e}")
        return None


def _build_duplicate_analysis_section(state: AgentState) -> Optional[DuplicateAnalysisSection]:
    """Build duplicate analysis section from analysis_summary. Returns None on error."""
    try:
        analysis = state.get("analysis_summary", {})
        if not analysis:
            return None

        duplicates = analysis.get("duplicates", [])
        return DuplicateAnalysisSection(
            duplicates_count=len(duplicates),
            duplicate_pairs=duplicates
        )
    except Exception as e:
        logger.warning(f"Failed to build duplicate analysis section: {e}")
        return None


def _build_priority_stacking_section(state: AgentState) -> Optional[PriorityStackingSection]:
    """Build priority stacking section from analysis_summary. Returns None on error."""
    try:
        analysis = state.get("analysis_summary", {})
        if not analysis:
            return None

        by_priority = analysis.get("by_priority", {})
        selected_tests = analysis.get("selected_tests", [])

        # Categorize selected tests by priority
        p0_selected = []
        p1_selected = []
        p2_selected = []

        for tc in selected_tests:
            priority = tc.get("priority", "").upper()
            test_id = tc.get("test_id", "")
            if priority == "P0":
                p0_selected.append(test_id)
            elif priority == "P1":
                p1_selected.append(test_id)
            else:
                p2_selected.append(test_id)

        return PriorityStackingSection(
            p0_count=by_priority.get("P0", 0),
            p1_count=by_priority.get("P1", 0),
            p2_count=by_priority.get("P2", 0),
            p0_selected=p0_selected,
            p1_selected=p1_selected,
            p2_selected=p2_selected
        )
    except Exception as e:
        logger.warning(f"Failed to build priority stacking section: {e}")
        return None


def _build_recovery_log_section(state: AgentState) -> Optional[RecoveryLogSection]:
    """Build recovery log section from event_log. Returns None on error."""
    try:
        event_log = state.get("event_log", [])
        recovery_attempts = state.get("recovery_attempts", 0)
        max_attempts = state.get("max_recovery_attempts", 5)

        # Extract all recovery_attempt events
        recovery_events = [e for e in event_log if e.get("event_type") == "recovery_attempt"]

        # Also get error events that occurred before each recovery
        error_events = [e for e in event_log if e.get("event_type") == "verification_result" or e.get("level") == "error"]

        recovery_entries = []
        for event in recovery_events:
            data = event.get("data", {})
            attempt_num = data.get("attempt", 0)

            # Get error details from verification_errors at time of this attempt
            error_details = []
            verification_errors = state.get("verification_errors", [])
            for err in verification_errors[:5]:  # Limit to 5 errors
                if isinstance(err, dict):
                    error_details.append({
                        "file": err.get("file", "unknown"),
                        "error_type": err.get("error_type", "Unknown"),
                        "error_message": str(err.get("message", ""))[:200]
                    })

            entry = RecoveryLogEntry(
                attempt_number=attempt_num,
                timestamp=event.get("timestamp", ""),
                files_fixed=data.get("files_fixed", []),
                files_unrecoverable=data.get("files_unrecoverable", []),
                errors_addressed=data.get("errors_addressed", 0),
                error_details=error_details
            )
            recovery_entries.append(entry)

        # Determine final status
        if state.get("verification_passed", False):
            final_status = "success"
        elif state.get("needs_human_intervention", False):
            final_status = "exhausted"
        elif recovery_attempts > 0:
            final_status = "partial"
        else:
            final_status = "not_needed"

        return RecoveryLogSection(
            total_recovery_attempts=recovery_attempts,
            max_attempts_allowed=max_attempts,
            recovery_log=recovery_entries,
            final_status=final_status
        )
    except Exception as e:
        logger.warning(f"Failed to build recovery log section: {e}")
        return None


def _build_final_summary_section(state: AgentState, test_status: List[Dict]) -> Optional[FinalSummarySection]:
    """Build enhanced final summary section. Returns None on error."""
    try:
        plan = state.get("generation_plan", {})
        tests_generated = len(plan.get("tests", []))

        passed = [t for t in test_status if t.get("status") == "passed"]
        failed = [t for t in test_status if t.get("status") == "failed"]
        not_run = [t for t in test_status if t.get("status") == "not_run"]

        failed_details = []
        for t in failed:
            failed_details.append({
                "test_name": t.get("test_name", "unknown"),
                "file": t.get("file", "unknown"),
                "error_type": t.get("error_type", "Unknown"),
                "error_summary": str(t.get("error_summary", "No details available"))[:500]
            })

        total_runnable = len(passed) + len(failed)
        success_rate = (len(passed) / total_runnable * 100) if total_runnable > 0 else 0

        return FinalSummarySection(
            total_tests_generated=tests_generated,
            tests_passed=len(passed),
            tests_failed=len(failed),
            tests_not_run=len(not_run),
            failed_test_details=failed_details,
            success_rate_percent=round(success_rate, 1)
        )
    except Exception as e:
        logger.warning(f"Failed to build final summary section: {e}")
        return None


def _build_coverage_section(state: AgentState, bedrock_client=None) -> Optional[CoverageSection]:
    """
    Build coverage section using LLM to analyze test types and suggest missing scenarios.
    Returns None on error.
    """
    try:
        approved_tests = state.get("approved_tests", [])
        page_metadata = state.get("page_metadata", {})

        if not approved_tests:
            return None

        # Group tests by page
        tests_by_page = {}
        for tc in approved_tests:
            page = tc.get("page_name", "Unknown")
            if page not in tests_by_page:
                tests_by_page[page] = []
            tests_by_page[page].append(tc)

        # Build coverage by page (basic metrics)
        coverage_by_page = {}
        for page_name, tests in tests_by_page.items():
            # Analyze test types from test names/steps
            test_types = set()
            for tc in tests:
                test_name = tc.get("test_name", "").lower()
                steps = tc.get("steps", "").lower()

                if "invalid" in test_name or "wrong" in test_name or "error" in test_name:
                    test_types.add("negative")
                elif "empty" in test_name or "special" in test_name or "edge" in test_name:
                    test_types.add("edge_case")
                elif "valid" in test_name or "success" in test_name:
                    test_types.add("positive")
                else:
                    test_types.add("positive")  # Default

            coverage_by_page[page_name] = {
                "test_count": len(tests),
                "test_types_covered": list(test_types)
            }

        # Generate suggestions based on analysis
        suggestions = []
        summary_parts = []

        for page_name, data in coverage_by_page.items():
            test_types = set(data.get("test_types_covered", []))
            test_count = data.get("test_count", 0)

            # Calculate approximate coverage
            expected_types = {"positive", "negative", "edge_case"}
            covered_types = test_types & expected_types
            coverage_pct = int(len(covered_types) / len(expected_types) * 100)

            summary_parts.append(f"{page_name} has ~{coverage_pct}% test type coverage")

            # Suggest missing test types
            if "negative" not in test_types:
                suggestions.append(f"{page_name}: Add negative test cases (e.g., invalid input handling)")
            if "edge_case" not in test_types:
                suggestions.append(f"{page_name}: Add edge case tests (e.g., empty fields, special characters)")
            if test_count < 3:
                suggestions.append(f"{page_name}: Consider adding more test cases (currently only {test_count})")

        # Use LLM for detailed analysis if available
        if bedrock_client and approved_tests:
            try:
                llm_suggestions = _get_llm_coverage_suggestions(
                    bedrock_client, approved_tests, page_metadata, state
                )
                if llm_suggestions:
                    suggestions.extend(llm_suggestions.get("suggestions", []))
                    if llm_suggestions.get("summary"):
                        summary_parts.append(llm_suggestions["summary"])
            except Exception as llm_err:
                logger.warning(f"LLM coverage analysis failed (non-fatal): {llm_err}")

        return CoverageSection(
            coverage_by_page=coverage_by_page,
            missing_coverage_suggestions=suggestions[:10],  # Cap at 10
            coverage_analysis_summary=". ".join(summary_parts) if summary_parts else ""
        )
    except Exception as e:
        logger.warning(f"Failed to build coverage section: {e}")
        return None


def _get_llm_coverage_suggestions(
    bedrock_client, approved_tests: List[Dict], page_metadata: Dict, state: AgentState
) -> Optional[Dict]:
    """
    Use LLM to analyze test coverage and generate suggestions.
    Returns None on error.
    """
    try:
        # Build prompt for coverage analysis
        test_summary = []
        for tc in approved_tests[:15]:  # Limit to first 15 tests
            test_summary.append(f"- {tc.get('test_name', 'Unknown')}: {tc.get('steps', '')[:100]}")

        pages_summary = []
        for page_name, page_data in page_metadata.items():
            elements = page_data.get("elements", [])
            element_names = [e.get("name", "") for e in elements[:10]]
            pages_summary.append(f"{page_name}: {', '.join(element_names)}")

        prompt = f"""Analyze these test cases and suggest missing test coverage:

TEST CASES:
{chr(10).join(test_summary)}

PAGES AND ELEMENTS:
{chr(10).join(pages_summary)}

Provide:
1. A one-sentence summary of overall coverage gaps
2. Up to 5 specific test case suggestions (format: "PageName: Add test for X")

Respond in this exact JSON format:
{{"summary": "...", "suggestions": ["PageName: Add test for X", ...]}}"""

        response = bedrock_client.generate(prompt, max_tokens=500)

        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return None
    except Exception as e:
        logger.debug(f"LLM coverage analysis error: {e}")
        return None


def _generate_markdown_report(report: AIReport) -> str:
    """
    Generate markdown report from AIReport.

    Args:
        report: AIReport object

    Returns:
        Markdown string
    """
    lines = []
    lines.append("# Test Generation Report")
    lines.append("")
    lines.append(f"**Module:** {report.module_name}")
    lines.append(f"**Session ID:** {report.session_id}")
    lines.append(f"**Created:** {report.created_at}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Planning Section (NEW)
    if report.planning:
        lines.append("## Planning")
        lines.append("")
        lines.append(f"- **Total Test Cases in CSV:** {report.planning.total_test_cases_in_csv}")
        lines.append(f"- **Selected for Generation:** {report.planning.selected_test_count}")
        lines.append(f"- **Max Test Cap:** {report.planning.max_test_cap}")
        lines.append(f"- **Selection Method:** {report.planning.selection_reason}")
        lines.append("")

    # Duplicate Analysis Section (NEW)
    if report.duplicate_analysis and report.duplicate_analysis.duplicates_count > 0:
        lines.append("## Duplicate Analysis")
        lines.append("")
        lines.append(f"**{report.duplicate_analysis.duplicates_count} duplicates identified**")
        lines.append("")
        lines.append("| Test ID | Duplicate Of | Similarity | Recommendation |")
        lines.append("|---------|--------------|------------|----------------|")
        for dup in report.duplicate_analysis.duplicate_pairs[:10]:
            test_id = dup.get("test_id", "?")
            dup_of = dup.get("duplicate_of", "?")
            sim = dup.get("similarity", 0)
            rec = dup.get("recommendation", "review")
            lines.append(f"| {test_id} | {dup_of} | {sim}% | {rec} |")
        lines.append("")

    # Priority Breakdown Section (NEW)
    if report.priority_breakdown:
        pb = report.priority_breakdown
        lines.append("## Priority Breakdown")
        lines.append("")
        lines.append(f"- **P0 (Critical):** {pb.p0_count} total, {len(pb.p0_selected)} selected")
        lines.append(f"- **P1 (Major):** {pb.p1_count} total, {len(pb.p1_selected)} selected")
        lines.append(f"- **P2 (Minor):** {pb.p2_count} total, {len(pb.p2_selected)} selected")
        lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Tests Generated:** {report.tests_generated}")
    lines.append(f"- **Pages Generated:** {report.pages_generated}")
    lines.append(f"- **Flows Generated:** {report.flows_generated}")
    lines.append(f"- **Verification Status:** {'✅ PASSED' if report.verification_passed else '❌ FAILED'}")
    lines.append("")

    if report.checkpoints_summary:
        lines.append("## Verification Checkpoints")
        lines.append("")
        for cp_name, cp_status in report.checkpoints_summary.items():
            status_icon = "✅" if cp_status == "passed" else "❌"
            lines.append(f"- {status_icon} **Checkpoint {cp_name}:** {cp_status.upper()}")
        lines.append("")

    # Coverage Section (NEW)
    if report.coverage:
        lines.append("## Coverage Analysis")
        lines.append("")
        if report.coverage.coverage_analysis_summary:
            lines.append(f"**Summary:** {report.coverage.coverage_analysis_summary}")
            lines.append("")
        if report.coverage.coverage_by_page:
            lines.append("### By Page")
            lines.append("")
            lines.append("| Page | Tests | Test Types |")
            lines.append("|------|-------|------------|")
            for page, data in report.coverage.coverage_by_page.items():
                test_count = data.get("test_count", 0)
                test_types = ", ".join(data.get("test_types_covered", []))
                lines.append(f"| {page} | {test_count} | {test_types} |")
            lines.append("")
        if report.coverage.missing_coverage_suggestions:
            lines.append("### Missing Coverage Suggestions")
            lines.append("")
            for suggestion in report.coverage.missing_coverage_suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")

    # Recovery Log Section (NEW)
    if report.recovery_log and report.recovery_log.total_recovery_attempts > 0:
        rl = report.recovery_log
        lines.append("## Recovery Log")
        lines.append("")
        lines.append(f"**Total Attempts:** {rl.total_recovery_attempts}/{rl.max_attempts_allowed}")
        lines.append(f"**Final Status:** {rl.final_status}")
        lines.append("")
        if rl.recovery_log:
            lines.append("| Attempt | Timestamp | Files Fixed | Errors Addressed |")
            lines.append("|---------|-----------|-------------|------------------|")
            for entry in rl.recovery_log:
                ts = entry.timestamp[:19] if entry.timestamp else "N/A"
                lines.append(f"| {entry.attempt_number} | {ts} | {len(entry.files_fixed)} | {entry.errors_addressed} |")
            lines.append("")
            # Show error details for first few entries
            for entry in rl.recovery_log[:3]:
                if entry.error_details:
                    lines.append(f"### Attempt {entry.attempt_number} Errors")
                    for err in entry.error_details[:3]:
                        lines.append(f"- **{err.get('error_type', 'Error')}** in `{err.get('file', 'unknown')}`")
                        lines.append(f"  - {err.get('error_message', 'No message')[:100]}")
                    lines.append("")

    # Final Summary Section (NEW)
    if report.final_summary:
        fs = report.final_summary
        lines.append("## Final Summary")
        lines.append("")
        lines.append(f"- **Total Tests Generated:** {fs.total_tests_generated}")
        lines.append(f"- **Tests Passed:** {fs.tests_passed}")
        lines.append(f"- **Tests Failed:** {fs.tests_failed}")
        lines.append(f"- **Tests Not Run:** {fs.tests_not_run}")
        lines.append(f"- **Success Rate:** {fs.success_rate_percent}%")
        lines.append("")
        if fs.failed_test_details:
            lines.append("### Failed Test Details")
            lines.append("")
            for detail in fs.failed_test_details:
                lines.append(f"#### {detail['test_name']}")
                lines.append(f"- **File:** `{detail['file']}`")
                lines.append(f"- **Error Type:** {detail['error_type']}")
                error_preview = detail['error_summary'][:200] if detail['error_summary'] else "N/A"
                lines.append(f"- **Error:** {error_preview}...")
                lines.append("")

    if report.test_execution_results:
        lines.append("## Test Execution Results")
        lines.append("")
        lines.append(f"- **Tests Passed:** {report.tests_passed_count}")
        lines.append(f"- **Tests Failed:** {report.tests_failed_count}")
        lines.append("")

        if report.test_status:
            lines.append("### Test Status")
            lines.append("")
            for test_info in report.test_status:
                test_name = test_info.get("test_name", "Unknown")
                status = test_info.get("status", "unknown")
                status_icon = "✅" if status == "passed" else "❌"
                lines.append(f"- {status_icon} {test_name}: {status}")
                if status == "failed" and test_info.get("error"):
                    error = test_info["error"][:200]  # Truncate long errors
                    lines.append(f"  - Error: {error}")
            lines.append("")

    if report.selector_risks:
        lines.append("## Selector Risks")
        lines.append("")
        for risk in report.selector_risks:
            lines.append(f"- **{risk.element_name}** in `{risk.file_name}`")
            lines.append(f"  - Selector: `{risk.selector_value}` ({risk.selector_type})")
            lines.append(f"  - Risk: {risk.risk_reason}")
            lines.append(f"  - Suggestion: {risk.suggestion}")
            lines.append("")

    if report.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    lines.append("## Cost Analysis")
    lines.append("")
    lines.append(f"- **Total Cost:** ${report.total_cost:.4f}")
    lines.append(f"  - Input tokens: {report.input_tokens:,} (${report.input_cost:.4f})")
    lines.append(f"  - Output tokens: {report.output_tokens:,} (${report.output_cost:.4f})")
    lines.append(f"- **Model:** {report.model_id}")
    lines.append(f"- **LLM Calls:** {report.llm_calls}")
    lines.append("")

    return "\n".join(lines)


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


def _save_event_log(state: AgentState, output_path: str) -> str:
    """
    Save the event log to a JSON file.

    Args:
        state: Current agent state
        output_path: Output directory

    Returns:
        Path to saved event log file
    """
    event_log = state.get("event_log", [])
    session_id = state.get("session_id", "unknown")
    started_at = state.get("started_at", datetime.now().isoformat())

    # Build summary
    llm_events = [e for e in event_log if e.get("event_type") == "llm_call"]
    error_events = [e for e in event_log if e.get("level") == "error"]
    recovery_events = [e for e in event_log if e.get("event_type") == "recovery_attempt"]

    total_input_tokens = sum(e.get("data", {}).get("input_tokens", 0) for e in llm_events)
    total_output_tokens = sum(e.get("data", {}).get("output_tokens", 0) for e in llm_events)

    # Build final status
    if state.get("verification_passed", False):
        final_status = "success"
    elif state.get("needs_human_intervention", False):
        final_status = "failed_needs_intervention"
    else:
        final_status = "failed"

    event_log_data = {
        "session_id": session_id,
        "started_at": started_at,
        "completed_at": datetime.now().isoformat(),
        "status": final_status,
        "events": event_log,
        "summary": {
            "total_events": len(event_log),
            "llm_calls": len(llm_events),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "errors_count": len(error_events),
            "recovery_attempts": len(recovery_events),
            "verification_passed": state.get("verification_passed", False),
            "files_generated": len(state.get("generated_files", {})),
            "nodes_executed": state.get("node_history", [])
        }
    }

    # Save to file
    event_log_path = os.path.join(output_path, "event_log.json")
    with open(event_log_path, 'w', encoding='utf-8') as f:
        json.dump(event_log_data, f, indent=2, default=str)

    logger.info(f"Event log saved to: {event_log_path}")
    return event_log_path


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

    # Log node start
    add_event_to_state(state, "node_start", "reporting")

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
    
    # Calculate cost
    input_tokens = state.get("llm_input_tokens", 0)
    output_tokens = state.get("llm_output_tokens", 0)
    model_id = state.get("llm_model_id", "us.anthropic.claude-opus-4-5-20251101-v1:0")
    
    cost_info = calculate_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model_id=model_id
    )
    
    # Extract test execution results
    test_execution_results = {}
    tests_passed_count = 0
    tests_failed_count = 0
    test_status = []
    verification_errors = {}

    # Get checkpoint D results (simplified from D1-D4)
    checkpoint_d = state.get("verification_results", {}).get("checkpoint_d", {})
    failed_test_names = set()

    if checkpoint_d:
        metadata = checkpoint_d.get("metadata", {})
        tests_passed_count = metadata.get("tests_passed", 0)
        tests_failed_count = metadata.get("tests_failed", 0)
        test_execution_results = {
            "tests_passed": tests_passed_count,
            "tests_failed": tests_failed_count
        }

        # Extract individual test status from verification_errors in state
        verification_errors_list = state.get("verification_errors", [])
        for error_info in verification_errors_list:
            if isinstance(error_info, dict):
                test_name = error_info.get("test_name", "unknown")
                failed_test_names.add(test_name)
                error_msg = error_info.get("message", "")
                traceback = error_info.get("traceback", [])
                error_summary = '\n'.join(traceback[:10]) if traceback else error_msg

                test_status.append({
                    "test_name": test_name,
                    "file": error_info.get("file", "unknown"),
                    "status": "failed",
                    "error_type": error_info.get("error_type", "Unknown"),
                    "error_summary": error_summary
                })
    
    # Extract all test names from generated test files and mark passed ones
    import re
    generated_files = state.get("generated_files", {})
    d_ran = checkpoint_d and checkpoint_d.get("status") not in ["skipped", None]
    
    for filepath, code in generated_files.items():
        if filepath.startswith("tests/") and filepath.endswith(".py"):
            # Extract test function names
            test_matches = re.findall(r'def\s+(test_\w+)', code)
            for test_name in test_matches:
                if test_name not in failed_test_names:
                    # This test passed (or wasn't run)
                    test_status.append({
                        "test_name": test_name,
                        "file": filepath,
                        "status": "passed" if d_ran else "not_run",
                        "error_type": None,
                        "error_summary": None
                    })
    
    # Collect all verification errors by checkpoint (simplified to A, B, C, D)
    verification_results = state.get("verification_results", {})
    for checkpoint_key in ["checkpoint_a", "checkpoint_b", "checkpoint_c", "checkpoint_d"]:
        checkpoint = verification_results.get(checkpoint_key, {})
        if checkpoint and checkpoint.get("status") == "failed":
            checkpoint_name = checkpoint.get("checkpoint_name", checkpoint_key[-1].upper())
            verification_errors[checkpoint_name] = {
                "status": checkpoint.get("status"),
                "files_failed": checkpoint.get("files_failed", []),
                "error_count": len(checkpoint.get("errors", {})),
                "errors": {k: str(v)[:500] for k, v in list(checkpoint.get("errors", {}).items())[:5]}
            }

    # Count actual test results
    tests_passed_count = len([t for t in test_status if t.get("status") == "passed"])
    tests_failed_count = len([t for t in test_status if t.get("status") == "failed"])

    # Build enhanced report sections with full protection (graceful degradation)
    logger.info("Building enhanced report sections...")
    planning_section = None
    duplicate_section = None
    priority_section = None
    coverage_section = None
    recovery_section = None
    final_summary_section = None

    try:
        planning_section = _build_planning_section(state)
        duplicate_section = _build_duplicate_analysis_section(state)
        priority_section = _build_priority_stacking_section(state)
        recovery_section = _build_recovery_log_section(state)
        final_summary_section = _build_final_summary_section(state, test_status)
        # Coverage analysis (may use LLM if available)
        coverage_section = _build_coverage_section(state, bedrock_client=None)
    except Exception as e:
        logger.error(f"Enhanced reporting sections failed (non-fatal): {e}")
        # All sections remain None, basic report still works

    # Build AI Report with simplified checkpoints
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
            "A_syntax": state.get("verification_results", {}).get("checkpoint_a", {}).get("status", "unknown"),
            "B_imports": state.get("verification_results", {}).get("checkpoint_b", {}).get("status", "unknown"),
            "C_collection": state.get("verification_results", {}).get("checkpoint_c", {}).get("status", "unknown"),
            "D_execution": state.get("verification_results", {}).get("checkpoint_d", {}).get("status", "unknown"),
        },
        selector_risks=selector_risks,
        recommendations=recommendations,
        llm_calls=state.get("llm_calls", 0),
        total_tokens=input_tokens + output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=cost_info["input_cost"],
        output_cost=cost_info["output_cost"],
        total_cost=cost_info["total_cost"],
        model_id=model_id,
        test_execution_results=test_execution_results,
        tests_passed_count=tests_passed_count,
        tests_failed_count=tests_failed_count,
        test_status=test_status,
        verification_errors=verification_errors,
        duration_seconds=None,  # Could calculate from started_at
        # Enhanced reporting sections (optional - None if not available)
        planning=planning_section,
        duplicate_analysis=duplicate_section,
        priority_breakdown=priority_section,
        coverage=coverage_section,
        recovery_log=recovery_section,
        final_summary=final_summary_section
    )
    
    # Save comprehensive report as single JSON file
    report_json_path = os.path.join(output_path, "report.json")
    report_data = report.model_dump(mode='json')

    # Add markdown summary inside JSON for readability
    report_data["markdown_summary"] = _generate_markdown_report(report)

    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, default=str)

    # Save event log (trace of all events)
    logger.info("Saving event log...")
    event_log_path = _save_event_log(state, output_path)

    # Update state
    state["ai_report"] = report_data

    # Log node complete
    add_event_to_state(state, "node_complete", "reporting")
    
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
    logger.info(f"    - Input tokens: {report.input_tokens:,}")
    logger.info(f"    - Output tokens: {report.output_tokens:,}")
    logger.info(f"  **Approximate Cost: ${report.total_cost:.4f}**")
    logger.info(f"    - Input cost: ${report.input_cost:.4f}")
    logger.info(f"    - Output cost: ${report.output_cost:.4f}")
    logger.info(f"  Model: {report.model_id}")
    logger.info("-" * 40)
    
    # Print recommendations
    logger.info("RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        logger.info(f"  {i}. {rec}")
    
    logger.info("=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info(f"Report saved to: {report_json_path}")
    logger.info(f"Event log saved to: {event_log_path}")
    logger.info("=" * 60)

    return state
