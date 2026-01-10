"""Agent Scratchpad - Living markdown document for tracking agent progress."""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AgentScratchpad:
    """Manages the agent scratchpad markdown file."""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.scratchpad_path = os.path.join(output_path, "generation_plan.md")
        self.sections = {}
    
    def initialize(self, state: Dict[str, Any]) -> None:
        """Initialize scratchpad with module info."""
        module_spec = state.get("module_spec", {})
        session_id = state.get("session_id", "unknown")
        
        self.sections["header"] = self._build_header(module_spec, session_id)
        self._write_scratchpad()
    
    def add_test_analysis(self, analysis: Dict[str, Any]) -> None:
        """Add test case analysis section."""
        self.sections["test_analysis"] = self._build_test_analysis(analysis)
        self._write_scratchpad()
    
    def add_generation_plan(self, plan: Dict[str, Any]) -> None:
        """Add generation plan section."""
        self.sections["generation_plan"] = self._build_generation_plan(plan)
        self._write_scratchpad()
    
    def update_progress(self, state: Dict[str, Any]) -> None:
        """Update progress checkpoints."""
        self.sections["progress"] = self._build_progress(state)
        self._write_scratchpad()
    
    def add_incremental_verification(self, stage: int, results: Dict[str, Any]) -> None:
        """Add incremental verification results."""
        self.sections[f"verification_stage{stage}"] = self._build_incremental_verification(stage, results)
        self._write_scratchpad()
    
    def add_decision(self, decision: str, notes: Optional[str] = None) -> None:
        """Add a decision or note."""
        if "decisions" not in self.sections:
            self.sections["decisions"] = []
        self.sections["decisions"].append({
            "timestamp": datetime.now(),
            "decision": decision,
            "notes": notes
        })
        self._write_scratchpad()
    
    def _build_header(self, module_spec: Dict, session_id: str) -> str:
        """Build header section."""
        return f"""# Test Generation Plan & Analysis

**Module:** {module_spec.get('module_name', 'unknown')}  
**Session ID:** {session_id}  
**Status:** 🟡 In Progress  
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---"""
    
    def _build_test_analysis(self, analysis: Dict) -> str:
        """Build test case analysis section."""
        lines = ["## 📊 Test Case Analysis", ""]
        
        # Summary
        lines.extend([
            "### Summary",
            f"- **Total Input Tests:** {analysis.get('total_input_tests', 0)}",
            f"- **Duplicates Found:** {analysis.get('duplicate_count', 0)}",
            f"- **Efficient Test Count:** {analysis.get('efficient_test_count', 0)}",
            f"- **Suggested Additional Tests:** {len(analysis.get('suggested_tests', []))}",
            f"- **Recommended Final Count:** {analysis.get('recommended_test_count', 0)}",
            f"- **Overall Coverage:** {analysis.get('overall_coverage', 0):.1f}%",
            ""
        ])
        
        # Duplicates
        duplicates = analysis.get('duplicates', [])
        if duplicates:
            lines.extend([
                "### 🔍 Duplicate Test Cases", "",
                "| Test ID | Duplicates | Similarity | Recommendation | Reason |",
                "|---------|-----------|------------|----------------|--------|"
            ])
            for dup in duplicates[:10]:  # Limit to 10
                lines.append(
                    f"| {dup.get('test_id', '')} | {dup.get('duplicate_of', '')} | "
                    f"{dup.get('similarity_score', 0):.2f} | {dup.get('recommendation', '')} | "
                    f"{dup.get('reason', '')[:50]} |"
                )
            if len(duplicates) > 10:
                lines.append(f"| ... | ({len(duplicates) - 10} more) | | | |")
            lines.append("")
        
        # Suggested tests
        suggestions = analysis.get('suggested_tests', [])
        if suggestions:
            lines.extend([
                "### ➕ Suggested Test Cases", "",
                "| Test ID | Name | Priority | Coverage Gap | Status |",
                "|---------|------|----------|--------------|--------|"
            ])
            for sug in suggestions[:10]:
                lines.append(
                    f"| {sug.get('test_id', '')} | {sug.get('test_name', '')[:40]} | "
                    f"{sug.get('priority', '')} | {sug.get('coverage_gap', '')[:30]} | ⏳ Pending |"
                )
            lines.append("")
        
        # Priority analysis
        priorities = analysis.get('priority_analysis', [])
        priority_changes = [p for p in priorities if p.get('current_priority') != p.get('recommended_priority')]
        if priority_changes:
            lines.extend([
                "### 🎯 Priority Recommendations", "",
                "| Test ID | Current | Recommended | Reason |",
                "|---------|---------|-------------|--------|"
            ])
            for pc in priority_changes[:10]:
                lines.append(
                    f"| {pc.get('test_id', '')} | {pc.get('current_priority', '')} | "
                    f"{pc.get('recommended_priority', '')} | {pc.get('priority_reason', '')[:40]} |"
                )
            lines.append("")
        
        # Coverage
        coverage_module = analysis.get('coverage_by_module', {})
        if coverage_module:
            lines.extend(["### 📈 Coverage Analysis", "", "#### By Module", ""])
            for module, metrics in list(coverage_module.items())[:5]:
                lines.extend([
                    f"- **{module}:** {metrics.get('coverage_percentage', 0):.1f}% coverage "
                    f"({metrics.get('total_test_cases', 0)} tests)",
                    f"  - ✅ Covered: {', '.join(metrics.get('covered_scenarios', [])[:3])}",
                    f"  - ❌ Missing: {', '.join(metrics.get('missing_scenarios', [])[:3])}",
                    ""
                ])
        
        coverage_page = analysis.get('coverage_by_page', {})
        if coverage_page:
            lines.extend(["#### By Page", ""])
            for page, metrics in list(coverage_page.items())[:5]:
                lines.extend([
                    f"- **{page}:** {metrics.get('coverage_percentage', 0):.1f}% coverage "
                    f"({metrics.get('total_test_cases', 0)} tests)",
                    f"  - ✅ Covered: {', '.join(metrics.get('covered_scenarios', [])[:3])}",
                    f"  - ❌ Missing: {', '.join(metrics.get('missing_scenarios', [])[:3])}",
                    ""
                ])
        
        return "\n".join(lines)
    
    def _build_generation_plan(self, plan: Dict) -> str:
        """Build generation plan section."""
        lines = ["## 📋 Generation Plan", ""]
        
        # Pages
        pages = plan.get('pages', [])
        if pages:
            lines.extend([
                f"### Pages to Generate ({len(pages)})",
                "| # | Page | File | Elements | Methods | Status |",
                "|---|------|------|----------|---------|--------|"
            ])
            for i, page in enumerate(pages, 1):
                status = "✅ Generated" if page.get('generated') else "⏳ Pending"
                lines.append(
                    f"| {i} | {page.get('page_name', '')} | {page.get('file_name', '')} | "
                    f"{len(page.get('elements', []))} | {len(page.get('methods', []))} | {status} |"
                )
            lines.append("")
        
        # Flows
        flows = plan.get('flows', [])
        if flows:
            lines.extend([
                f"### Flows to Generate ({len(flows)})",
                "| # | Flow | File | Pages Used | Status |",
                "|---|------|------|------------|--------|"
            ])
            for i, flow in enumerate(flows, 1):
                status = "✅ Generated" if flow.get('generated') else "⏳ Pending"
                lines.append(
                    f"| {i} | {flow.get('flow_name', '')} | {flow.get('file_name', '')} | "
                    f"{', '.join(flow.get('pages_used', []))} | {status} |"
                )
            lines.append("")
        
        # Tests
        tests = plan.get('tests', [])
        if tests:
            lines.extend([
                f"### Tests to Generate ({len(tests)})",
                "| # | Test ID | Test Name | Status |",
                "|---|---------|-----------|--------|"
            ])
            for i, test in enumerate(tests[:20], 1):  # Limit to 20
                status = "✅ Generated" if test.get('generated') else "⏳ Pending"
                lines.append(
                    f"| {i} | {test.get('test_id', '')} | {test.get('test_name', '')[:40]} | {status} |"
                )
            if len(tests) > 20:
                lines.append(f"| ... | ({len(tests) - 20} more) | | |")
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_progress(self, state: Dict[str, Any]) -> str:
        """Build progress section."""
        lines = ["## 🔄 Agent Progress", "", "### Checkpoints", ""]
        
        checkpoints = [
            ("Onboarding", "onboarding"),
            ("Test Case Analysis", "test_analysis"),
            ("Planning", "planning"),
            ("Human Gate", "human_gate_plan"),
            ("Generation Stage 1", "generation_stage1"),
            ("Generation Stage 2", "generation_stage2"),
            ("Generation Stage 3", "generation_stage3"),
            ("Verification A", "checkpoint_a"),
            ("Verification B", "checkpoint_b"),
            ("Verification C", "checkpoint_c"),
            ("Verification D1", "checkpoint_d1"),
            ("Verification D2", "checkpoint_d2"),
            ("Verification D3", "checkpoint_d3"),
            ("Verification D4", "checkpoint_d4"),
        ]
        
        node_history = state.get("node_history", [])
        verification_results = state.get("verification_results", {})
        
        for name, key in checkpoints:
            # Check if completed
            if key in node_history or any(key in str(h) for h in node_history):
                # Check if passed
                if key.startswith("checkpoint_"):
                    cp = verification_results.get(key, {})
                    if cp and cp.get("status") == "passed":
                        lines.append(f"- [x] {name} ✅")
                    elif cp and cp.get("status") == "failed":
                        lines.append(f"- [x] {name} ❌")
                    else:
                        lines.append(f"- [x] {name} ⏳")
                else:
                    lines.append(f"- [x] {name} ✅")
            else:
                lines.append(f"- [ ] {name} ⏳")
        
        # Recovery attempts
        recovery_attempts = state.get("recovery_attempts", 0)
        if recovery_attempts > 0:
            lines.append("")
            lines.append("### Recovery Attempts")
            for i in range(1, recovery_attempts + 1):
                lines.append(f"- Attempt {i}: Fixed issues")
        
        return "\n".join(lines)
    
    def _build_incremental_verification(self, stage: int, results: Dict[str, Any]) -> str:
        """Build incremental verification section."""
        lines = [
            f"## 🔍 Incremental Verification Stage {stage}",
            "",
            f"**Status:** {'✅ Passed' if results.get('all_passed') else '❌ Failed'}",
            "",
            "**Checkpoints:**"
        ]
        
        if stage == 1:
            cp_a = results.get('checkpoint_a', {})
            cp_b = results.get('checkpoint_b', {})
            cp_d1 = results.get('checkpoint_d1', {})
            lines.extend([
                f"- Checkpoint A (Syntax): {cp_a.get('status', 'unknown')}",
                f"- Checkpoint B (Imports): {cp_b.get('status', 'unknown')}",
                f"- Checkpoint D1 (Structure): {cp_d1.get('status', 'unknown')}"
            ])
        elif stage == 2:
            cp_a = results.get('checkpoint_a', {})
            cp_b = results.get('checkpoint_b', {})
            cp_d2 = results.get('checkpoint_d2', {})
            lines.extend([
                f"- Checkpoint A (Syntax): {cp_a.get('status', 'unknown')}",
                f"- Checkpoint B (Imports): {cp_b.get('status', 'unknown')}",
                f"- Checkpoint D2-Partial (Flow Calls): {cp_d2.get('status', 'unknown')}"
            ])
        elif stage == 3:
            cp_a = results.get('checkpoint_a', {})
            cp_b = results.get('checkpoint_b', {})
            cp_c = results.get('checkpoint_c', {})
            cp_d2 = results.get('checkpoint_d2', {})
            cp_d3 = results.get('checkpoint_d3', {})
            lines.extend([
                f"- Checkpoint A (Syntax): {cp_a.get('status', 'unknown')}",
                f"- Checkpoint B (Imports): {cp_b.get('status', 'unknown')}",
                f"- Checkpoint C (Collection): {cp_c.get('status', 'unknown')}",
                f"- Checkpoint D2 (Contracts): {cp_d2.get('status', 'unknown')}",
                f"- Checkpoint D3 (Signatures): {cp_d3.get('status', 'unknown')}"
            ])
        
        # Add errors if any
        all_errors = {}
        for key in results:
            if key.startswith('checkpoint_'):
                cp = results.get(key, {})
                if cp.get('errors'):
                    all_errors.update(cp.get('errors', {}))
        
        if all_errors:
            lines.append("")
            lines.append("**Errors:**")
            for filepath, error in list(all_errors.items())[:5]:
                error_str = str(error)[:200] + ("..." if len(str(error)) > 200 else "")
                lines.append(f"- `{filepath}`: {error_str}")
        
        return "\n".join(lines)
    
    def _write_scratchpad(self) -> None:
        """Write all sections to scratchpad file."""
        os.makedirs(self.output_path, exist_ok=True)
        
        content = []
        content.append(self.sections.get("header", ""))
        content.append("")
        content.append(self.sections.get("test_analysis", ""))
        content.append("")
        content.append(self.sections.get("generation_plan", ""))
        content.append("")
        content.append(self.sections.get("progress", ""))
        
        # Add incremental verification stages
        for stage in [1, 2, 3]:
            if f"verification_stage{stage}" in self.sections:
                content.append("")
                content.append(self.sections[f"verification_stage{stage}"])
        
        # Add decisions
        if "decisions" in self.sections:
            content.append("")
            content.append("## 📝 Decisions & Notes")
            content.append("")
            for decision in self.sections["decisions"]:
                content.append(f"**{decision['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}:** {decision['decision']}")
                if decision.get('notes'):
                    content.append(f"  - {decision['notes']}")
                content.append("")
        
        # Update last updated time in header
        header = content[0] if content else ""
        if header:
            header_lines = header.split('\n')
            for i, line in enumerate(header_lines):
                if "Last Updated:" in line:
                    header_lines[i] = f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    break
            content[0] = '\n'.join(header_lines)
        
        with open(self.scratchpad_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        
        logger.info(f"Scratchpad updated: {self.scratchpad_path}")
