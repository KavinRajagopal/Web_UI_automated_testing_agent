"""LangGraph state definition for the Web UI Test Generation Agent.

The AgentState TypedDict holds all data that flows through the agent's
state machine. Each node can read from and write to this state.

State Flow:
    onboarding -> planning -> human_review -> generation -> 
    verification -> (recovery) -> reporting -> END
"""
from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime


class AgentState(TypedDict, total=False):
    """
    Central state object that flows through all agent nodes.
    
    Uses TypedDict for LangGraph compatibility.
    Fields marked 'total=False' means all fields are optional.
    
    Sections:
    - Configuration: Input settings
    - Inputs: Parsed input data
    - Planning: LLM-generated plan
    - Generation: Generated code
    - Verification: Validation results
    - Human Interaction: HITL state
    - Reporting: Final outputs
    - Metadata: Session tracking
    """
    
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    
    # Paths
    inputs_path: str
    """Path to inputs directory (module_spec.json, testcases.csv, element_metadata/)"""
    
    output_path: str
    """Path to automation_repo output directory"""
    
    # LLM settings
    llm_model_id: str
    """Bedrock model ID to use"""
    
    llm_region: str
    """AWS region for Bedrock"""
    
    llm_profile: str
    """AWS profile name"""
    
    # =========================================================================
    # INPUTS (populated by onboarding node)
    # =========================================================================
    
    module_spec: Dict[str, Any]
    """Parsed module_spec.json as dict"""
    
    test_cases: List[Dict[str, Any]]
    """Parsed test case rows from CSV"""
    
    page_metadata: Dict[str, Dict[str, Any]]
    """Map of page_name -> PageMetadata dict"""
    
    # Validation results
    input_validation_errors: List[str]
    """Any validation errors found during onboarding"""
    
    input_validation_warnings: List[str]
    """Any validation warnings"""
    
    # =========================================================================
    # PLANNING (populated by planning node)
    # =========================================================================
    
    generation_plan: Dict[str, Any]
    """GenerationPlan as dict - what to generate"""
    
    planning_prompt: str
    """The prompt sent to LLM for planning (for debugging)"""
    
    planning_response: str
    """Raw LLM response (for debugging)"""
    
    # =========================================================================
    # HUMAN REVIEW (populated by human_review node)
    # =========================================================================
    
    plan_approved: bool
    """Whether human approved the plan"""
    
    human_feedback: Optional[str]
    """Feedback from human if plan was revised"""
    
    plan_revision_count: int
    """How many times the plan was revised"""
    
    # =========================================================================
    # GENERATION (populated by generation node)
    # =========================================================================
    
    generated_files: Dict[str, str]
    """Map of file_path -> file_content for all generated files"""
    
    generation_errors: List[str]
    """Any errors during generation"""
    
    # =========================================================================
    # VERIFICATION (populated by verification node)
    # =========================================================================
    
    verification_results: Dict[str, Any]
    """VerificationResults as dict"""
    
    verification_passed: bool
    """Whether all checkpoints passed"""
    
    # =========================================================================
    # RECOVERY (populated by recovery node)
    # =========================================================================
    
    recovery_attempts: int
    """Number of recovery attempts made"""
    
    max_recovery_attempts: int
    """Maximum recovery attempts allowed"""
    
    recovered_files: List[str]
    """Files that were successfully recovered"""
    
    unrecoverable_files: List[str]
    """Files that could not be recovered"""
    
    needs_human_intervention: bool
    """Whether human intervention is needed"""
    
    # =========================================================================
    # REPORTING (populated by reporting node)
    # =========================================================================
    
    ai_report: Dict[str, Any]
    """AIReport as dict"""
    
    report_markdown: str
    """Markdown version of the report"""
    
    # =========================================================================
    # METADATA
    # =========================================================================
    
    session_id: str
    """Unique session identifier"""
    
    started_at: str
    """ISO format timestamp when session started"""
    
    current_node: str
    """Name of the currently executing node"""
    
    node_history: List[str]
    """List of nodes that have executed"""
    
    errors: List[str]
    """Any errors encountered"""
    
    # LLM usage tracking
    llm_calls: int
    """Total LLM calls made"""
    
    llm_input_tokens: int
    """Total input tokens used"""
    
    llm_output_tokens: int
    """Total output tokens used"""


def create_initial_state(
    inputs_path: str,
    output_path: str,
    llm_model_id: str = "us.anthropic.claude-opus-4-5-20251101-v1:0",
    llm_region: str = "us-east-2",
    llm_profile: str = "tring-kavin",
    max_recovery_attempts: int = 3
) -> AgentState:
    """
    Create initial state with default values.
    
    Args:
        inputs_path: Path to inputs directory
        output_path: Path to output automation_repo
        llm_model_id: Bedrock model ID
        llm_region: AWS region
        llm_profile: AWS profile name
        max_recovery_attempts: Max retries for recovery
        
    Returns:
        Initialized AgentState
    """
    return AgentState(
        # Configuration
        inputs_path=inputs_path,
        output_path=output_path,
        llm_model_id=llm_model_id,
        llm_region=llm_region,
        llm_profile=llm_profile,
        
        # Inputs (will be populated)
        module_spec={},
        test_cases=[],
        page_metadata={},
        input_validation_errors=[],
        input_validation_warnings=[],
        
        # Planning (will be populated)
        generation_plan={},
        planning_prompt="",
        planning_response="",
        
        # Human review
        plan_approved=False,
        human_feedback=None,
        plan_revision_count=0,
        
        # Generation
        generated_files={},
        generation_errors=[],
        
        # Verification
        verification_results={},
        verification_passed=False,
        
        # Recovery
        recovery_attempts=0,
        max_recovery_attempts=max_recovery_attempts,
        recovered_files=[],
        unrecoverable_files=[],
        needs_human_intervention=False,
        
        # Reporting
        ai_report={},
        report_markdown="",
        
        # Metadata
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        started_at=datetime.now().isoformat(),
        current_node="",
        node_history=[],
        errors=[],
        
        # LLM usage
        llm_calls=0,
        llm_input_tokens=0,
        llm_output_tokens=0,
    )
