"""Event Logger Utility for the Web UI Test Generation Agent.

Provides structured JSON logging for agent trace visibility.
All events are captured with timestamps and stored for final output.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import os


class EventLogger:
    """
    Structured event logger for agent execution tracing.

    Events are stored in memory and written to JSON at the end of execution.

    Event Types:
        - node_start: When a node begins execution
        - node_complete: When a node finishes execution
        - analysis_complete: After CSV analysis with results
        - human_approval: Human gate decision
        - llm_call: LLM invocation with token counts
        - verification_result: Verification checkpoint results
        - recovery_attempt: Recovery attempt with details
        - error: Any error encountered
        - file_generated: When a file is generated
        - file_written: When a file is written to disk
    """

    def __init__(self, session_id: str):
        """
        Initialize the event logger.

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.started_at = datetime.now().isoformat()
        self.events: List[Dict[str, Any]] = []

    def log_event(
        self,
        event_type: str,
        node: str,
        data: Optional[Dict[str, Any]] = None,
        level: str = "info"
    ) -> Dict[str, Any]:
        """
        Log an event.

        Args:
            event_type: Type of event (node_start, llm_call, etc.)
            node: Name of the node where event occurred
            data: Additional event data
            level: Log level (info, warning, error)

        Returns:
            The logged event dict
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "node": node,
            "level": level,
            "data": data or {}
        }
        self.events.append(event)
        return event

    def log_node_start(self, node: str) -> Dict[str, Any]:
        """Log node start event."""
        return self.log_event("node_start", node)

    def log_node_complete(self, node: str, duration_ms: Optional[int] = None) -> Dict[str, Any]:
        """Log node completion event."""
        data = {}
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        return self.log_event("node_complete", node, data)

    def log_analysis(
        self,
        node: str,
        total_tests: int,
        duplicates_found: int,
        by_priority: Dict[str, int],
        selected_count: int
    ) -> Dict[str, Any]:
        """Log CSV analysis results."""
        return self.log_event("analysis_complete", node, {
            "total_tests": total_tests,
            "duplicates_found": duplicates_found,
            "by_priority": by_priority,
            "selected_count": selected_count,
            "capped_at": 10
        })

    def log_human_approval(
        self,
        node: str,
        approved: bool,
        modifications: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Log human gate decision."""
        return self.log_event("human_approval", node, {
            "approved": approved,
            "modifications": modifications or []
        })

    def log_llm_call(
        self,
        node: str,
        purpose: str,
        input_tokens: int,
        output_tokens: int,
        model_id: str
    ) -> Dict[str, Any]:
        """Log LLM invocation."""
        return self.log_event("llm_call", node, {
            "purpose": purpose,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_id": model_id
        })

    def log_verification(
        self,
        node: str,
        syntax_passed: bool,
        imports_passed: bool,
        collection_passed: bool,
        execution_passed: bool,
        errors: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Log verification results."""
        return self.log_event("verification_result", node, {
            "syntax_check": "passed" if syntax_passed else "failed",
            "import_check": "passed" if imports_passed else "failed",
            "pytest_collect": "passed" if collection_passed else "failed",
            "pytest_run": "passed" if execution_passed else "failed",
            "all_passed": all([syntax_passed, imports_passed, collection_passed, execution_passed]),
            "errors": errors or []
        })

    def log_recovery_attempt(
        self,
        node: str,
        attempt: int,
        files_fixed: List[str],
        errors_addressed: int
    ) -> Dict[str, Any]:
        """Log recovery attempt."""
        return self.log_event("recovery_attempt", node, {
            "attempt": attempt,
            "files_fixed": files_fixed,
            "errors_addressed": errors_addressed
        })

    def log_error(
        self,
        node: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Log an error."""
        return self.log_event("error", node, {
            "error_type": error_type,
            "message": message,
            "details": details or {}
        }, level="error")

    def log_file_generated(self, node: str, filepath: str, size_bytes: int) -> Dict[str, Any]:
        """Log file generation."""
        return self.log_event("file_generated", node, {
            "filepath": filepath,
            "size_bytes": size_bytes
        })

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all logged events."""
        return self.events.copy()

    def get_events_as_list(self) -> List[Dict[str, Any]]:
        """Get events as a list for state storage."""
        return self.events.copy()

    def to_dict(self, final_status: str = "unknown", summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert to full log dict.

        Args:
            final_status: Final status (success, failed, cancelled)
            summary: Summary statistics

        Returns:
            Complete log dict for JSON output
        """
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "completed_at": datetime.now().isoformat(),
            "status": final_status,
            "events": self.events,
            "summary": summary or self._generate_summary()
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary from events."""
        llm_calls = [e for e in self.events if e["event_type"] == "llm_call"]
        errors = [e for e in self.events if e["level"] == "error"]
        recovery_attempts = [e for e in self.events if e["event_type"] == "recovery_attempt"]

        total_input_tokens = sum(e["data"].get("input_tokens", 0) for e in llm_calls)
        total_output_tokens = sum(e["data"].get("output_tokens", 0) for e in llm_calls)

        return {
            "total_events": len(self.events),
            "llm_calls": len(llm_calls),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "errors_count": len(errors),
            "recovery_attempts": len(recovery_attempts)
        }

    def to_json(self, final_status: str = "unknown", summary: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert to JSON string.

        Args:
            final_status: Final status
            summary: Summary statistics

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(final_status, summary), indent=2)

    def save(
        self,
        output_path: str,
        filename: str = "event_log.json",
        final_status: str = "unknown",
        summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save event log to file.

        Args:
            output_path: Directory to save to
            filename: Output filename
            final_status: Final status
            summary: Summary statistics

        Returns:
            Full path to saved file
        """
        os.makedirs(output_path, exist_ok=True)
        filepath = os.path.join(output_path, filename)

        with open(filepath, "w") as f:
            f.write(self.to_json(final_status, summary))

        return filepath


def create_event_logger(session_id: str) -> EventLogger:
    """Factory function to create an EventLogger."""
    return EventLogger(session_id)


def events_from_state(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract events from agent state."""
    return state.get("event_log", [])


def add_event_to_state(
    state: Dict[str, Any],
    event_type: str,
    node: str,
    data: Optional[Dict[str, Any]] = None,
    level: str = "info"
) -> Dict[str, Any]:
    """
    Add an event directly to state's event_log.

    This is a helper for nodes that don't have access to the EventLogger instance.

    Args:
        state: Agent state dict
        event_type: Type of event
        node: Node name
        data: Event data
        level: Log level

    Returns:
        The event that was added
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "node": node,
        "level": level,
        "data": data or {}
    }

    if "event_log" not in state:
        state["event_log"] = []

    state["event_log"].append(event)
    return event
