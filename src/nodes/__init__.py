"""Agent nodes for the Web UI Test Generation Agent.

Each node is a function that takes AgentState and returns updated AgentState.
Nodes are wired together using LangGraph.

Node Flow:
    onboarding -> [human_gate_0] -> planning -> human_gate_1 -> 
    generation -> verification -> [recovery] -> reporting -> END

Human gates are conditional based on whether inputs were auto-generated
or if the plan needs approval.
"""

from .onboarding import onboarding_node
from .human_gates import (
    human_gate_inputs,
    human_gate_plan,
    human_gate_final
)
from .planning import planning_node
from .generation import generation_node
from .verification.verification_node import verification_node
from .recovery import recovery_node
from .reporting import reporting_node

__all__ = [
    "onboarding_node",
    "human_gate_inputs",
    "human_gate_plan",
    "human_gate_final",
    "planning_node",
    "generation_node",
    "verification_node",
    "recovery_node",
    "reporting_node",
]
