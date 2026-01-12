"""Human Gate Node - CLI interface for human-in-the-loop review.

Single human gate after test case analysis, before generation.
Allows human to review duplicates, P0 prioritization, and 10-test selection.
"""

import logging
from typing import Dict, Any, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..models.state import AgentState
from ..utils.event_logger import add_event_to_state

logger = logging.getLogger(__name__)
console = Console()


def _display_analysis_summary(state: AgentState):
    """Display the analysis summary."""
    analysis = state.get("analysis_summary", {})
    module_spec = state.get("module_spec", {})

    # Module info
    console.print(Panel.fit(
        f"[bold]Module:[/bold] {module_spec.get('module_name', 'N/A')}\n"
        f"[bold]App URL:[/bold] {module_spec.get('app_url', 'N/A')}",
        title="Module Information",
        border_style="cyan"
    ))

    # Summary stats
    total = analysis.get("total_tests", 0)
    dups = analysis.get("duplicates_count", 0)
    selected = analysis.get("selected_count", 0)
    by_priority = analysis.get("by_priority", {})

    console.print("\n[bold cyan]Analysis Summary[/bold cyan]")
    console.print(f"  Total test cases in CSV: {total}")
    console.print(f"  Duplicates identified: {dups}")
    console.print(f"  By priority: P0={by_priority.get('P0', 0)}, P1={by_priority.get('P1', 0)}, P2={by_priority.get('P2', 0)}")
    console.print(f"  Selected for generation: {selected} (capped at {analysis.get('capped_at', 10)})")


def _display_duplicates(duplicates: List[Dict[str, Any]]):
    """Display duplicate test cases."""
    if not duplicates:
        return

    console.print(f"\n[bold yellow]Duplicates Found ({len(duplicates)})[/bold yellow]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Test ID", style="cyan", width=20)
    table.add_column("Duplicate Of", style="yellow", width=20)
    table.add_column("Similarity", style="green", width=12)
    table.add_column("Recommendation", style="magenta", width=15)

    for dup in duplicates[:10]:
        table.add_row(
            dup.get("test_id", "N/A"),
            dup.get("duplicate_of", "N/A"),
            f"{dup.get('similarity', 0)}%",
            dup.get("recommendation", "review")
        )

    if len(duplicates) > 10:
        table.add_row("...", f"({len(duplicates) - 10} more)", "", "")

    console.print(table)


def _display_selected_tests(selected_tests: List[Dict[str, Any]]):
    """Display the selected test cases."""
    if not selected_tests:
        console.print("\n[yellow]No tests selected[/yellow]")
        return

    console.print(f"\n[bold green]Selected Tests ({len(selected_tests)})[/bold green]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Priority", style="yellow", width=8)
    table.add_column("Test ID", style="cyan", width=20)
    table.add_column("Test Name", style="white", width=50)

    for i, tc in enumerate(selected_tests, 1):
        priority = tc.get("priority", "P2")
        # Normalize priority display
        if priority not in ["P0", "P1", "P2"]:
            priority = "P2"
        table.add_row(
            str(i),
            priority,
            tc.get("test_id", "N/A"),
            (tc.get("test_name", "N/A") or "N/A")[:50]
        )

    console.print(table)


def _display_pages(state: AgentState):
    """Display pages and element counts."""
    page_metadata = state.get("page_metadata", {})

    if not page_metadata:
        return

    console.print(f"\n[bold cyan]Page Elements ({len(page_metadata)} pages)[/bold cyan]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Page", style="cyan", width=25)
    table.add_column("Elements", style="green", width=10)

    for page_name, page in page_metadata.items():
        elements = page.get("elements", [])
        table.add_row(page_name, str(len(elements)))

    console.print(table)


def human_gate_node(state: AgentState) -> AgentState:
    """
    Single human gate after analysis, before generation.

    Displays:
    - Analysis summary (total tests, duplicates, priorities)
    - Duplicate test cases with recommendations
    - Selected tests (P0 first, capped at 10)
    - Page element summary

    Options:
    - Approve: Continue with selected tests
    - Modify: Interactively modify selection
    - Cancel: End execution

    Args:
        state: Current agent state

    Returns:
        Updated state with approval status
    """
    logger.info("=" * 60)
    logger.info("HUMAN GATE: Test Case Review")
    logger.info("=" * 60)

    state["current_node"] = "human_gate"
    state["node_history"] = state.get("node_history", []) + ["human_gate"]

    # Log node start
    add_event_to_state(state, "node_start", "human_gate")

    console.print("\n")
    console.print("=" * 70)
    console.print(Panel.fit(
        "[bold cyan]TEST CASE ANALYSIS REVIEW[/bold cyan]\n"
        "Review the analysis before proceeding to code generation.",
        title="Human Review Gate",
        border_style="cyan"
    ))
    console.print("=" * 70)

    # Display analysis summary
    console.print("\n")
    _display_analysis_summary(state)

    # Display duplicates
    analysis = state.get("analysis_summary", {})
    duplicates = analysis.get("duplicates", [])
    _display_duplicates(duplicates)

    # Display selected tests
    selected_tests = analysis.get("selected_tests", [])
    _display_selected_tests(selected_tests)

    # Display page info
    _display_pages(state)

    # Ask for approval
    console.print("\n" + "-" * 70)
    console.print("[bold]Options:[/bold]")
    console.print("  [A]pprove - Continue with selected tests")
    console.print("  [M]odify  - Modify test selection")
    console.print("  [C]ancel  - Cancel generation")
    console.print("-" * 70 + "\n")

    choice = Prompt.ask(
        "[bold]Choose action[/bold]",
        choices=["a", "m", "c", "approve", "modify", "cancel"],
        default="a"
    ).lower()

    if choice in ["a", "approve"]:
        state["plan_approved"] = True
        state["approved_tests"] = selected_tests

        add_event_to_state(state, "human_approval", "human_gate", {
            "approved": True,
            "tests_count": len(selected_tests)
        })

        console.print("\n[green]Approved! Proceeding to planning and generation...[/green]\n")

    elif choice in ["m", "modify"]:
        # Allow modification
        modified_tests = _modify_test_selection(state, selected_tests)
        state["approved_tests"] = modified_tests
        state["plan_approved"] = True

        add_event_to_state(state, "human_approval", "human_gate", {
            "approved": True,
            "modified": True,
            "tests_count": len(modified_tests)
        })

        console.print(f"\n[green]Modified! Proceeding with {len(modified_tests)} tests...[/green]\n")

    else:  # cancel
        state["plan_approved"] = False
        state["approved_tests"] = []

        add_event_to_state(state, "human_approval", "human_gate", {
            "approved": False,
            "cancelled": True
        })

        console.print("\n[red]Cancelled. Generation will not proceed.[/red]\n")

    # Log node complete
    add_event_to_state(state, "node_complete", "human_gate")

    return state


def _modify_test_selection(state: AgentState, current_selection: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Interactive modification of test selection.

    Args:
        state: Agent state
        current_selection: Currently selected tests

    Returns:
        Modified test selection
    """
    all_tests = state.get("test_cases", [])
    analysis = state.get("analysis_summary", {})
    duplicates = {d["test_id"] for d in analysis.get("duplicates", [])}

    console.print("\n[bold cyan]Modify Test Selection[/bold cyan]")
    console.print("Enter test IDs to add/remove, or 'done' to finish.")
    console.print("Prefix with '-' to remove (e.g., '-TC_001'), or just ID to add.")
    console.print(f"Max tests: 10 (current: {len(current_selection)})\n")

    # Create a set of currently selected IDs for easy lookup
    selected_ids = {tc.get("test_id") for tc in current_selection}
    all_tests_by_id = {tc.get("test_id"): tc for tc in all_tests}

    while True:
        action = Prompt.ask("[bold]Action[/bold] (ID or -ID or 'done')", default="done")

        if action.lower() == "done":
            break

        if action.startswith("-"):
            # Remove
            test_id = action[1:]
            if test_id in selected_ids:
                selected_ids.remove(test_id)
                console.print(f"[yellow]Removed: {test_id}[/yellow]")
            else:
                console.print(f"[red]{test_id} not in selection[/red]")
        else:
            # Add
            test_id = action
            if test_id in duplicates:
                console.print(f"[red]{test_id} is marked as duplicate - skip[/red]")
            elif test_id not in all_tests_by_id:
                console.print(f"[red]{test_id} not found in test cases[/red]")
            elif len(selected_ids) >= 10:
                console.print("[red]Max 10 tests - remove one first[/red]")
            elif test_id in selected_ids:
                console.print(f"[yellow]{test_id} already selected[/yellow]")
            else:
                selected_ids.add(test_id)
                console.print(f"[green]Added: {test_id}[/green]")

        console.print(f"Current count: {len(selected_ids)}/10")

    # Rebuild selection maintaining priority order
    modified = [all_tests_by_id[tid] for tid in selected_ids if tid in all_tests_by_id]

    # Sort by priority
    def priority_key(tc):
        p = str(tc.get("priority", "P2")).upper()
        if p == "P0":
            return 0
        elif p == "P1":
            return 1
        return 2

    modified.sort(key=priority_key)

    console.print(f"\n[green]Modified selection: {len(modified)} tests[/green]")
    return modified


def skip_human_gate(state: AgentState, gate_name: str = "human_gate") -> AgentState:
    """
    Skip human gate (for automated/batch mode).

    Auto-approves with the pre-selected tests from analysis.

    Args:
        state: Current agent state
        gate_name: Name of the gate being skipped

    Returns:
        Updated state with gate marked as approved
    """
    logger.info(f"Skipping human gate: {gate_name} (auto-approve mode)")

    state["current_node"] = gate_name
    state["node_history"] = state.get("node_history", []) + [gate_name]

    # Auto-approve with pre-selected tests
    analysis = state.get("analysis_summary", {})
    selected_tests = analysis.get("selected_tests", [])

    state["plan_approved"] = True
    state["approved_tests"] = selected_tests

    add_event_to_state(state, "human_approval", gate_name, {
        "approved": True,
        "auto_approved": True,
        "tests_count": len(selected_tests)
    })

    logger.info(f"Auto-approved {len(selected_tests)} tests")

    return state


# Backwards compatibility aliases
human_gate_inputs = human_gate_node
human_gate_plan = skip_human_gate
human_gate_final = skip_human_gate
human_gate_test_cases = human_gate_node
