"""Main Agent - LangGraph wiring for the Web UI Test Generation Agent.

This module wires all nodes together into a LangGraph StateGraph
and provides the main entry point for running the agent.

Supports:
- LangSmith tracing (set LANGCHAIN_TRACING_V2=true)
- LangGraph Studio (langgraph dev)
- Checkpoint/resume capabilities
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .models.state import AgentState, create_initial_state
from .nodes.onboarding import onboarding_node
from .nodes.human_gates import (
    human_gate_inputs,
    human_gate_plan,
    human_gate_final,
    skip_human_gate
)
from .nodes.planning import planning_node
from .nodes.generation import generation_node
from .nodes.verification import verification_node
from .nodes.recovery import recovery_node, should_retry_verification
from .nodes.reporting import reporting_node

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_after_onboarding(state: AgentState) -> str:
    """Determine next node after onboarding."""
    # Check for critical errors
    if state.get("input_validation_errors"):
        logger.error("Onboarding failed with errors")
        return END
    
    # Check if inputs need review
    if state.get("needs_input_review", False):
        return "human_gate_inputs"
    
    # Skip to planning if inputs are pre-validated
    return "planning"


def route_after_input_review(state: AgentState) -> str:
    """Determine next node after input review."""
    if state.get("plan_approved", False):
        return "planning"
    else:
        logger.info("Inputs not approved - ending")
        return END


def route_after_plan_review(state: AgentState) -> str:
    """Determine next node after plan review."""
    if state.get("plan_approved", False):
        return "generation"
    elif state.get("plan_revision_count", 0) < 3:
        # Allow re-planning with feedback
        return "planning"
    else:
        logger.info("Plan not approved after max revisions - ending")
        return END


def route_after_verification(state: AgentState) -> str:
    """Determine next node after verification."""
    if state.get("verification_passed", False):
        return "human_gate_final"
    elif should_retry_verification(state):
        return "recovery"
    else:
        return "human_gate_final"


def route_after_recovery(state: AgentState) -> str:
    """Determine next node after recovery."""
    if state.get("needs_human_intervention", False):
        return "human_gate_final"
    else:
        return "verification"


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def build_agent_graph(auto_approve: bool = False, checkpointer=None) -> StateGraph:
    """
    Build the LangGraph StateGraph for the agent.
    
    Args:
        auto_approve: If True, skip human gates (for batch mode)
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Compiled StateGraph
        
    Graph Structure:
        onboarding → [human_gate_inputs] → planning → human_gate_plan
                                                           ↓
                        ┌─────────────────────────── generation
                        │                                  ↓
                        │                           verification
                        │                          ↙           ↘
                        │                   (pass)              (fail)
                        │                      ↓                  ↓
                        │             human_gate_final ←─── recovery
                        │                      ↓                  │
                        │                  reporting              │
                        │                      ↓                  │
                        └─────────────────── END ←────────────────┘
                                                    (max 3 retries)
    """
    # Create graph with AgentState
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("onboarding", onboarding_node)
    
    if auto_approve:
        graph.add_node("human_gate_inputs", 
                       lambda s: skip_human_gate(s, "human_gate_inputs"))
        graph.add_node("human_gate_plan",
                       lambda s: skip_human_gate(s, "human_gate_plan"))
        graph.add_node("human_gate_final",
                       lambda s: skip_human_gate(s, "human_gate_final"))
    else:
        graph.add_node("human_gate_inputs", human_gate_inputs)
        graph.add_node("human_gate_plan", human_gate_plan)
        graph.add_node("human_gate_final", human_gate_final)
    
    graph.add_node("planning", planning_node)
    graph.add_node("generation", generation_node)
    graph.add_node("verification", verification_node)
    graph.add_node("recovery", recovery_node)
    graph.add_node("reporting", reporting_node)
    
    # Set entry point
    graph.set_entry_point("onboarding")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "onboarding",
        route_after_onboarding,
        {
            "human_gate_inputs": "human_gate_inputs",
            "planning": "planning",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "human_gate_inputs",
        route_after_input_review,
        {
            "planning": "planning",
            END: END
        }
    )
    
    graph.add_edge("planning", "human_gate_plan")
    
    graph.add_conditional_edges(
        "human_gate_plan",
        route_after_plan_review,
        {
            "generation": "generation",
            "planning": "planning",
            END: END
        }
    )
    
    graph.add_edge("generation", "verification")
    
    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "recovery": "recovery",
            "human_gate_final": "human_gate_final"
        }
    )
    
    graph.add_conditional_edges(
        "recovery",
        route_after_recovery,
        {
            "verification": "verification",
            "human_gate_final": "human_gate_final"
        }
    )
    
    graph.add_edge("human_gate_final", "reporting")
    graph.add_edge("reporting", END)
    
    # Compile with optional checkpointer for debugging/resume
    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# =============================================================================
# AGENT RUNNER
# =============================================================================

class TestGenerationAgent:
    """
    Main agent class for running the test generation pipeline.
    
    Usage:
        agent = TestGenerationAgent(
            inputs_path="inputs/saucedemo",
            output_path="output/saucedemo_tests"
        )
        result = agent.run()
        
    Debugging:
        # Enable LangSmith tracing
        export LANGCHAIN_TRACING_V2=true
        export LANGCHAIN_API_KEY=your_key
        export LANGCHAIN_PROJECT=web-ui-agent
        
        # Use checkpointing for resume/debug
        agent = TestGenerationAgent(..., enable_checkpointing=True)
    """
    
    def __init__(
        self,
        inputs_path: str,
        output_path: str,
        llm_model_id: str = "us.anthropic.claude-opus-4-5-20251101-v1:0",
        llm_region: str = "us-east-2",
        llm_profile: str = "bedrock-user",
        max_recovery_attempts: int = 3,
        auto_approve: bool = False,
        enable_checkpointing: bool = False
    ):
        """
        Initialize the agent.
        
        Args:
            inputs_path: Path to inputs directory
            output_path: Path to output directory
            llm_model_id: Bedrock model ID
            llm_region: AWS region
            llm_profile: AWS profile name
            max_recovery_attempts: Max recovery retries
            auto_approve: Skip human gates if True
            enable_checkpointing: Enable state checkpointing for debugging
        """
        self.inputs_path = os.path.abspath(inputs_path)
        self.output_path = os.path.abspath(output_path)
        self.llm_model_id = llm_model_id
        self.llm_region = llm_region
        self.llm_profile = llm_profile
        self.max_recovery_attempts = max_recovery_attempts
        self.auto_approve = auto_approve
        self.enable_checkpointing = enable_checkpointing
        
        # Setup checkpointer for debugging/resume
        self.checkpointer = MemorySaver() if enable_checkpointing else None
        
        # Build the graph
        self.graph = build_agent_graph(
            auto_approve=auto_approve,
            checkpointer=self.checkpointer
        )
        
        # Log LangSmith status
        if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
            logger.info("LangSmith tracing ENABLED")
            logger.info(f"  Project: {os.environ.get('LANGCHAIN_PROJECT', 'default')}")
    
    def run(self, stream: bool = False):
        """
        Run the agent pipeline.
        
        Args:
            stream: If True, yield intermediate states (for debugging)
        
        Returns:
            Final AgentState with all results (or generator if stream=True)
        """
        logger.info("=" * 60)
        logger.info("WEB UI TEST GENERATION AGENT")
        logger.info("=" * 60)
        logger.info(f"Inputs: {self.inputs_path}")
        logger.info(f"Output: {self.output_path}")
        logger.info(f"Auto-approve: {self.auto_approve}")
        logger.info(f"Checkpointing: {self.enable_checkpointing}")
        logger.info("=" * 60)
        
        # Create initial state
        initial_state = create_initial_state(
            inputs_path=self.inputs_path,
            output_path=self.output_path,
            llm_model_id=self.llm_model_id,
            llm_region=self.llm_region,
            llm_profile=self.llm_profile,
            max_recovery_attempts=self.max_recovery_attempts
        )
        
        # Config for checkpointing
        config = {"configurable": {"thread_id": initial_state.get("session_id", "default")}}
        
        # Run the graph - split into separate methods to avoid generator issue
        if stream:
            return self._run_streaming(initial_state, config)
        else:
            return self._run_normal(initial_state, config)
    
    def _run_normal(self, initial_state: AgentState, config: dict) -> AgentState:
        """Run agent in normal mode (non-streaming)."""
        try:
            final_state = self.graph.invoke(initial_state, config=config)
            
            logger.info("=" * 60)
            logger.info("AGENT COMPLETED")
            logger.info(f"Session ID: {final_state.get('session_id')}")
            logger.info(f"Nodes executed: {' -> '.join(final_state.get('node_history', []))}")
            logger.info(f"Files generated: {len(final_state.get('generated_files', {}))}")
            logger.info(f"Recovery attempts: {final_state.get('recovery_attempts', 0)}")
            logger.info(f"Verification: {'PASSED' if final_state.get('verification_passed') else 'FAILED'}")
            logger.info(f"LLM calls: {final_state.get('llm_calls', 0)}")
            logger.info("=" * 60)
            
            return final_state
            
        except Exception as e:
            logger.error(f"Agent failed: {e}")
            raise
    
    def _run_streaming(self, initial_state: AgentState, config: dict):
        """Run agent in streaming mode (yields each step)."""
        try:
            final_state = None
            for step in self.graph.stream(initial_state, config=config):
                node_name = list(step.keys())[0]
                logger.info(f"[STREAM] Completed node: {node_name}")
                final_state = step[node_name]
                yield step
            
            # Log final summary
            if final_state:
                logger.info("=" * 60)
                logger.info("AGENT COMPLETED")
                logger.info(f"Session ID: {final_state.get('session_id')}")
                logger.info(f"Nodes executed: {' -> '.join(final_state.get('node_history', []))}")
                logger.info(f"Files generated: {len(final_state.get('generated_files', {}))}")
                logger.info(f"Recovery attempts: {final_state.get('recovery_attempts', 0)}")
                logger.info(f"Verification: {'PASSED' if final_state.get('verification_passed') else 'FAILED'}")
                logger.info(f"LLM calls: {final_state.get('llm_calls', 0)}")
                logger.info("=" * 60)
                
        except Exception as e:
            logger.error(f"Agent failed: {e}")
            raise
    
    def get_state_history(self) -> list:
        """Get state history from checkpointer (for debugging)."""
        if not self.checkpointer:
            logger.warning("Checkpointing not enabled")
            return []
        # Return checkpoint history
        return list(self.checkpointer.list())


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """CLI entry point for the agent."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Web UI Test Generation Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (with human gates)
  python -m src.agent --inputs inputs/saucedemo --output output/saucedemo
  
  # Auto-approve mode (skip human gates)
  python -m src.agent --inputs inputs/saucedemo --output output/saucedemo --auto
  
  # Custom LLM settings
  python -m src.agent --inputs inputs/saucedemo --output output/saucedemo --profile my-profile
  
  # With LangSmith tracing
  export LANGCHAIN_TRACING_V2=true
  export LANGCHAIN_API_KEY=your_key
  export LANGCHAIN_PROJECT=web-ui-agent
  python -m src.agent --inputs inputs/saucedemo --output output/saucedemo
"""
    )
    
    parser.add_argument(
        "--inputs", "-i",
        required=True,
        help="Path to inputs directory (module_spec.json, testcases.csv, element_metadata/)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path to output directory for generated code"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-approve mode (skip human gates)"
    )
    parser.add_argument(
        "--profile",
        default="bedrock-user",
        help="AWS profile name (default: bedrock-user)"
    )
    parser.add_argument(
        "--region",
        default="us-east-2",
        help="AWS region (default: us-east-2)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max recovery retries (default: 3)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help="Enable checkpointing for debugging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run agent
    agent = TestGenerationAgent(
        inputs_path=args.inputs,
        output_path=args.output,
        llm_profile=args.profile,
        llm_region=args.region,
        max_recovery_attempts=args.max_retries,
        auto_approve=args.auto,
        enable_checkpointing=args.checkpoint
    )
    
    try:
        result = agent.run()
        
        # Exit with appropriate code
        if result.get("verification_passed"):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
