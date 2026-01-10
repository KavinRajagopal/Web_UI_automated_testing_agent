"""Human Gate Nodes - CLI interfaces for human-in-the-loop review.

Three human gates:
1. human_gate_inputs: Review auto-generated elements and test cases
2. human_gate_plan: Review and approve the generation plan
3. human_gate_final: Final review before completion
"""

import json
import logging
from typing import Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.markdown import Markdown

from ..models.state import AgentState

logger = logging.getLogger(__name__)
console = Console()


def _display_module_info(state: AgentState):
    """Display module information."""
    module_spec = state.get("module_spec", {})
    
    table = Table(title="Module Information", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Module Name", module_spec.get("module_name", "N/A"))
    table.add_row("App Name", module_spec.get("app_name", "N/A"))
    table.add_row("App URL", module_spec.get("app_url", "N/A"))
    table.add_row("Browser", module_spec.get("browser", "N/A"))
    
    console.print(table)


def _display_test_cases(state: AgentState):
    """Display test cases summary."""
    test_cases = state.get("test_cases", [])
    
    if not test_cases:
        console.print("[yellow]No test cases loaded[/yellow]")
        return
    
    table = Table(title=f"Test Cases ({len(test_cases)} total)")
    table.add_column("ID", style="cyan", width=20)
    table.add_column("Name", style="white", width=40)
    table.add_column("Priority", style="yellow", width=8)
    table.add_column("Page", style="green", width=15)
    
    for tc in test_cases[:10]:  # Show first 10
        table.add_row(
            tc.get("test_id", "N/A"),
            tc.get("test_name", "N/A")[:40],
            tc.get("priority", "N/A"),
            tc.get("page_name", "N/A")
        )
    
    if len(test_cases) > 10:
        table.add_row("...", f"({len(test_cases) - 10} more)", "", "")
    
    console.print(table)


def _display_pages(state: AgentState):
    """Display pages and elements summary."""
    page_metadata = state.get("page_metadata", {})
    
    if not page_metadata:
        console.print("[yellow]No page metadata loaded[/yellow]")
        return
    
    table = Table(title=f"Page Elements ({len(page_metadata)} pages)")
    table.add_column("Page", style="cyan", width=20)
    table.add_column("Elements", style="green", width=10)
    table.add_column("URL", style="white", width=40)
    
    for page_name, page in page_metadata.items():
        elements = page.get("elements", [])
        table.add_row(
            page_name,
            str(len(elements)),
            page.get("page_url", "N/A")[:40]
        )
    
    console.print(table)


def _display_generation_plan(state: AgentState):
    """Display the generation plan."""
    plan = state.get("generation_plan", {})
    
    if not plan:
        console.print("[yellow]No generation plan available[/yellow]")
        return
    
    # Pages to generate
    pages = plan.get("pages", [])
    if pages:
        table = Table(title=f"Pages to Generate ({len(pages)})")
        table.add_column("Class Name", style="cyan")
        table.add_column("File", style="green")
        table.add_column("Elements", style="yellow")
        
        for page in pages:
            table.add_row(
                page.get("page_name", "N/A"),
                page.get("file_name", "N/A"),
                str(len(page.get("elements", [])))
            )
        console.print(table)
    
    # Flows to generate
    flows = plan.get("flows", [])
    if flows:
        table = Table(title=f"Flows to Generate ({len(flows)})")
        table.add_column("Class Name", style="cyan")
        table.add_column("File", style="green")
        table.add_column("Pages Used", style="yellow")
        
        for flow in flows:
            table.add_row(
                flow.get("flow_name", "N/A"),
                flow.get("file_name", "N/A"),
                ", ".join(flow.get("pages_used", []))
            )
        console.print(table)
    
    # Tests to generate
    tests = plan.get("tests", [])
    if tests:
        table = Table(title=f"Tests to Generate ({len(tests)})")
        table.add_column("Test ID", style="cyan", width=20)
        table.add_column("Test Name", style="green", width=40)
        table.add_column("Markers", style="yellow")
        
        for test in tests[:10]:
            table.add_row(
                test.get("test_id", "N/A"),
                test.get("test_name", "N/A")[:40],
                ", ".join(test.get("markers", []))
            )
        
        if len(tests) > 10:
            table.add_row("...", f"({len(tests) - 10} more)", "")
        
        console.print(table)


def _display_verification_results(state: AgentState):
    """Display verification results."""
    results = state.get("verification_results", {})
    
    if not results:
        console.print("[yellow]No verification results[/yellow]")
        return
    
    table = Table(title="Verification Results")
    table.add_column("Checkpoint", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="yellow")
    
    for checkpoint in ["checkpoint_a", "checkpoint_b", "checkpoint_c"]:
        cp = results.get(checkpoint, {})
        if cp:
            status = cp.get("status", "unknown")
            status_style = "green" if status == "passed" else "red"
            
            details = ""
            if cp.get("files_failed"):
                details = f"{len(cp['files_failed'])} failed"
            elif cp.get("files_passed"):
                details = f"{len(cp['files_passed'])} passed"
            
            table.add_row(
                cp.get("checkpoint_name", checkpoint),
                f"[{status_style}]{status}[/{status_style}]",
                details
            )
    
    console.print(table)


def human_gate_inputs(state: AgentState) -> AgentState:
    """
    Human Gate 0: Review generated/loaded inputs.
    
    Called when inputs were auto-generated or when validation warnings exist.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with approval status
    """
    logger.info("=" * 60)
    logger.info("HUMAN GATE: Input Review")
    logger.info("=" * 60)
    
    state["current_node"] = "human_gate_inputs"
    state["node_history"] = state.get("node_history", []) + ["human_gate_inputs"]
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Human Review: Input Data[/bold cyan]\n"
        "Please review the loaded/generated inputs before proceeding.",
        title="🔍 Input Review Gate"
    ))
    
    # Display module info
    console.print("\n")
    _display_module_info(state)
    
    # Display test cases
    console.print("\n")
    _display_test_cases(state)
    
    # Display pages
    console.print("\n")
    _display_pages(state)
    
    # Show warnings if any
    warnings = state.get("input_validation_warnings", [])
    if warnings:
        console.print("\n[yellow]⚠ Warnings:[/yellow]")
        for w in warnings:
            console.print(f"  • {w}")
    
    # Show generation status
    if state.get("generated_elements") or state.get("generated_testcases"):
        console.print("\n[cyan]ℹ Generated Data:[/cyan]")
        if state.get("generated_elements"):
            console.print("  • Element metadata was auto-generated")
        if state.get("generated_testcases"):
            console.print("  • Test cases were auto-generated")
    
    # Ask for approval
    console.print("\n")
    approved = Confirm.ask(
        "[bold]Do you approve these inputs and want to proceed?[/bold]",
        default=True
    )
    
    if not approved:
        feedback = Prompt.ask(
            "[yellow]Please provide feedback (or press Enter to cancel)[/yellow]",
            default=""
        )
        state["human_feedback"] = feedback
        state["plan_approved"] = False
        console.print("[red]Inputs not approved. Please modify and restart.[/red]")
    else:
        state["plan_approved"] = True
        state["needs_input_review"] = False
        console.print("[green]✓ Inputs approved! Proceeding to planning...[/green]")
    
    return state


def human_gate_plan(state: AgentState) -> AgentState:
    """
    Human Gate 1: Review and approve generation plan.
    
    Shows the LLM-generated plan and asks for approval.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with plan approval status
    """
    logger.info("=" * 60)
    logger.info("HUMAN GATE: Plan Review")
    logger.info("=" * 60)
    
    state["current_node"] = "human_gate_plan"
    state["node_history"] = state.get("node_history", []) + ["human_gate_plan"]
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Human Review: Generation Plan[/bold cyan]\n"
        "Please review the code generation plan before proceeding.",
        title="📋 Plan Review Gate"
    ))
    
    # Display the plan
    console.print("\n")
    _display_generation_plan(state)
    
    # Show plan summary
    plan = state.get("generation_plan", {})
    console.print("\n[cyan]Plan Summary:[/cyan]")
    console.print(f"  • Pages: {len(plan.get('pages', []))}")
    console.print(f"  • Flows: {len(plan.get('flows', []))}")
    console.print(f"  • Tests: {len(plan.get('tests', []))}")
    console.print(f"  • Fixtures: {len(plan.get('conftest_fixtures', []))}")
    
    # Ask for approval
    console.print("\n")
    choice = Prompt.ask(
        "[bold]Choose action[/bold]",
        choices=["approve", "revise", "cancel"],
        default="approve"
    )
    
    if choice == "approve":
        state["plan_approved"] = True
        console.print("[green]✓ Plan approved! Proceeding to generation...[/green]")
    elif choice == "revise":
        feedback = Prompt.ask(
            "[yellow]What changes would you like to make?[/yellow]"
        )
        state["human_feedback"] = feedback
        state["plan_approved"] = False
        state["plan_revision_count"] = state.get("plan_revision_count", 0) + 1
        console.print("[yellow]Plan revision requested. Re-planning...[/yellow]")
    else:
        state["plan_approved"] = False
        console.print("[red]Generation cancelled.[/red]")
    
    return state


def human_gate_final(state: AgentState) -> AgentState:
    """
    Human Gate 2: Final review before completion.
    
    Shows verification results and asks for final approval.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with final approval
    """
    logger.info("=" * 60)
    logger.info("HUMAN GATE: Final Review")
    logger.info("=" * 60)
    
    state["current_node"] = "human_gate_final"
    state["node_history"] = state.get("node_history", []) + ["human_gate_final"]
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Human Review: Final Check[/bold cyan]\n"
        "Review the generation results before finalizing.",
        title="✅ Final Review Gate"
    ))
    
    # Show verification results
    console.print("\n")
    _display_verification_results(state)
    
    # Show generated files
    generated_files = state.get("generated_files", {})
    console.print(f"\n[cyan]Generated Files: {len(generated_files)}[/cyan]")
    for filepath in list(generated_files.keys())[:10]:
        console.print(f"  • {filepath}")
    if len(generated_files) > 10:
        console.print(f"  ... and {len(generated_files) - 10} more")
    
    # Show any errors
    errors = state.get("generation_errors", [])
    if errors:
        console.print("\n[red]Errors:[/red]")
        for e in errors:
            console.print(f"  • {e}")
    
    # Show recovery info if applicable
    if state.get("recovery_attempts", 0) > 0:
        console.print(f"\n[yellow]Recovery attempts: {state['recovery_attempts']}[/yellow]")
        if state.get("recovered_files"):
            console.print(f"  Recovered: {len(state['recovered_files'])} files")
        if state.get("unrecoverable_files"):
            console.print(f"  Unrecoverable: {len(state['unrecoverable_files'])} files")
    
    # Overall status
    verification_passed = state.get("verification_passed", False)
    if verification_passed:
        console.print("\n[green]✓ All verification checks passed![/green]")
    else:
        console.print("\n[yellow]⚠ Some verification checks failed[/yellow]")
    
    # Ask for final approval
    console.print("\n")
    approved = Confirm.ask(
        "[bold]Finalize and generate report?[/bold]",
        default=verification_passed
    )
    
    if approved:
        console.print("[green]✓ Finalizing and generating report...[/green]")
    else:
        feedback = Prompt.ask(
            "[yellow]Additional feedback (optional)[/yellow]",
            default=""
        )
        if feedback:
            state["human_feedback"] = feedback
        console.print("[yellow]Please review the generated code manually.[/yellow]")
    
    return state


def human_gate_test_cases(state: AgentState) -> AgentState:
    """
    Human gate for reviewing test case analysis (duplicates, suggestions).
    
    Allows human to:
    - Review duplicate test cases
    - Approve/reject suggested test cases
    - Approve test case modifications
    """
    logger.info("=" * 60)
    logger.info("HUMAN GATE: Test Case Analysis Review")
    logger.info("=" * 60)
    
    state["current_node"] = "human_gate_test_cases"
    state["node_history"] = state.get("node_history", []) + ["human_gate_test_cases"]
    
    console.print("\n" + "=" * 80)
    console.print(Panel.fit("[bold cyan]TEST CASE ANALYSIS REVIEW[/bold cyan]", border_style="cyan"))
    console.print("=" * 80 + "\n")
    
    analysis = state.get("test_case_analysis", {})
    
    if not analysis:
        console.print("[yellow]No test case analysis available[/yellow]")
        state["test_case_modifications_approved"] = False
        return state
    
    # Display duplicates
    duplicates = analysis.get("duplicates", [])
    if duplicates:
        console.print(f"[bold yellow]Found {len(duplicates)} Duplicate Test Cases[/bold yellow]\n")
        
        table = Table(title="Duplicate Test Cases")
        table.add_column("Test ID", style="cyan")
        table.add_column("Duplicates", style="yellow")
        table.add_column("Similarity", style="green")
        table.add_column("Reason", style="white", width=40)
        table.add_column("Recommendation", style="magenta")
        
        for dup in duplicates[:10]:
            table.add_row(
                dup.get("test_id", "N/A"),
                dup.get("duplicate_of", "N/A"),
                f"{dup.get('similarity_score', 0):.0%}",
                dup.get("reason", "N/A")[:40],
                dup.get("recommendation", "N/A")
            )
        
        if len(duplicates) > 10:
            table.add_row("...", f"({len(duplicates) - 10} more)", "", "", "")
        
        console.print(table)
        console.print("\n[yellow]Note: These are SUGGESTIONS. You can approve modifications to remove/merge duplicates.[/yellow]\n")
    
    # Display suggested tests
    suggestions = analysis.get("suggested_tests", [])
    if suggestions:
        console.print(f"[bold green]Suggested {len(suggestions)} Additional Test Cases[/bold green]\n")
        
        table = Table(title="Suggested Test Cases")
        table.add_column("Test ID", style="cyan")
        table.add_column("Name", style="white", width=40)
        table.add_column("Priority", style="yellow")
        table.add_column("Coverage Gap", style="green", width=30)
        
        for sug in suggestions[:10]:
            table.add_row(
                sug.get("test_id", "N/A"),
                sug.get("test_name", "N/A")[:40],
                sug.get("priority", "N/A"),
                sug.get("coverage_gap", "N/A")[:30]
            )
        
        if len(suggestions) > 10:
            table.add_row("...", f"({len(suggestions) - 10} more)", "", "")
        
        console.print(table)
        console.print("\n[yellow]Note: These are SUGGESTIONS. You can approve adding these to the test suite.[/yellow]\n")
    
    # Summary
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  - Total input tests: {analysis.get('total_input_tests', 0)}")
    console.print(f"  - Duplicates found: {analysis.get('duplicate_count', 0)}")
    console.print(f"  - Suggested tests: {len(suggestions)}")
    console.print(f"  - Efficient test count: {analysis.get('efficient_test_count', 0)}")
    console.print(f"  - Overall coverage: {analysis.get('overall_coverage', 0):.1f}%\n")
    
    # Ask for approval
    if duplicates or suggestions:
        approve = Confirm.ask(
            "[bold cyan]Do you want to approve test case modifications?[/bold cyan]\n"
            "[dim](This will remove duplicates and/or add suggested tests)[/dim]",
            default=False
        )
        
        if approve:
            console.print("[green]✓ Test case modifications approved[/green]")
            state["test_case_modifications_approved"] = True
            # TODO: Apply modifications to test cases CSV
            # For now, we'll just flag it - actual modification can be done in a separate step
        else:
            console.print("[yellow]Test case modifications not approved - continuing with original test cases[/yellow]")
            state["test_case_modifications_approved"] = False
    else:
        console.print("[green]No test case modifications needed[/green]")
        state["test_case_modifications_approved"] = True  # Auto-approve if no changes needed
    
    console.print()
    return state


def skip_human_gate(state: AgentState, gate_name: str) -> AgentState:
    """
    Skip a human gate (for automated/batch mode).
    
    Args:
        state: Current agent state
        gate_name: Name of the gate being skipped
        
    Returns:
        Updated state with gate marked as approved
    """
    logger.info(f"Skipping human gate: {gate_name} (auto-approve mode)")
    
    state["current_node"] = gate_name
    state["node_history"] = state.get("node_history", []) + [gate_name]
    
    # For test case gate, auto-approve means don't modify
    if gate_name == "human_gate_test_cases":
        state["test_case_modifications_approved"] = False
    else:
        state["plan_approved"] = True
    
    return state
