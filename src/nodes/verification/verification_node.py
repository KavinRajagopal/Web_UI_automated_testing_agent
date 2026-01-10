"""Verification Node - Orchestrates all verification checkpoints."""

import logging
import os
from typing import Dict

from ...models.state import AgentState
from ...models.schemas import CheckpointStatus, CheckpointResult, VerificationResults
from .checkpoint_a import checkpoint_a_syntax
from .checkpoint_b import checkpoint_b_imports
from .checkpoint_c import checkpoint_c_collect
from .checkpoint_d1 import checkpoint_d1_page_object_structure
from .checkpoint_d2 import checkpoint_d2_method_contracts
from .checkpoint_d3 import checkpoint_d3_method_signatures
from .checkpoint_d4 import checkpoint_d4_execution

logger = logging.getLogger(__name__)


def verification_node(state: AgentState) -> AgentState:
    """
    Verification node - runs all verification checkpoints.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with verification results
    """
    logger.info("=" * 60)
    logger.info("VERIFICATION NODE")
    logger.info("=" * 60)
    
    state["current_node"] = "verification"
    state["node_history"] = state.get("node_history", []) + ["verification"]
    
    generated_files = state.get("generated_files", {})
    output_path = state.get("output_path", "")
    
    if not generated_files:
        logger.warning("No generated files to verify")
        state["verification_passed"] = False
        return state
    
    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Run checkpoints
    checkpoint_a = checkpoint_a_syntax(generated_files)
    logger.info(f"Checkpoint A: {checkpoint_a.status.value} ({len(checkpoint_a.files_passed)}/{len(checkpoint_a.files_checked)} passed)")
    
    checkpoint_b = checkpoint_b_imports(generated_files)
    logger.info(f"Checkpoint B: {checkpoint_b.status.value} ({len(checkpoint_b.files_passed)}/{len(checkpoint_b.files_checked)} passed)")
    
    checkpoint_c = checkpoint_c_collect(generated_files, output_path)
    logger.info(f"Checkpoint C: {checkpoint_c.status.value}")
    
    # Run granular D checkpoints (only if A, B, C passed)
    checkpoint_d1 = None
    checkpoint_d2 = None
    checkpoint_d3 = None
    checkpoint_d4 = None
    
    if (checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED):
        
        # Checkpoint D1: Page Object Structure
        checkpoint_d1 = checkpoint_d1_page_object_structure(generated_files)
        logger.info(f"Checkpoint D1: {checkpoint_d1.status.value} ({len(checkpoint_d1.files_passed)}/{len(checkpoint_d1.files_checked)} passed)")
        
        # Checkpoint D2: Method Contracts (only if D1 passed)
        if checkpoint_d1.status == CheckpointStatus.PASSED:
            checkpoint_d2 = checkpoint_d2_method_contracts(generated_files)
            logger.info(f"Checkpoint D2: {checkpoint_d2.status.value} ({len(checkpoint_d2.files_passed)}/{len(checkpoint_d2.files_checked)} passed)")
        else:
            logger.info("Checkpoint D2: SKIPPED (D1 failed)")
            checkpoint_d2 = CheckpointResult(
                checkpoint_name="D2",
                checkpoint_description="Method Contract Validation",
                status=CheckpointStatus.SKIPPED,
                files_checked=[],
                files_passed=[],
                files_failed=[],
                errors={}
            )
        
        # Checkpoint D3: Method Signatures (only if D2 passed)
        if checkpoint_d2.status == CheckpointStatus.PASSED:
            checkpoint_d3 = checkpoint_d3_method_signatures(generated_files)
            logger.info(f"Checkpoint D3: {checkpoint_d3.status.value} ({len(checkpoint_d3.files_passed)}/{len(checkpoint_d3.files_checked)} passed)")
        else:
            logger.info("Checkpoint D3: SKIPPED (D2 failed)")
            checkpoint_d3 = CheckpointResult(
                checkpoint_name="D3",
                checkpoint_description="Method Signature Validation",
                status=CheckpointStatus.SKIPPED,
                files_checked=[],
                files_passed=[],
                files_failed=[],
                errors={}
            )
        
        # Checkpoint D4: Test Execution (only if D1-D3 passed)
        if (checkpoint_d1.status == CheckpointStatus.PASSED and
            checkpoint_d2.status == CheckpointStatus.PASSED and
            checkpoint_d3.status == CheckpointStatus.PASSED):
            
            checkpoint_d4 = checkpoint_d4_execution(generated_files, output_path)
            test_info = checkpoint_d4.metadata.get("tests_passed", 0) if checkpoint_d4.metadata else 0
            test_failed = checkpoint_d4.metadata.get("tests_failed", 0) if checkpoint_d4.metadata else 0
            logger.info(f"Checkpoint D4: {checkpoint_d4.status.value} ({test_info} passed, {test_failed} failed)")
        else:
            logger.info("Checkpoint D4: SKIPPED (previous D checkpoints failed)")
            checkpoint_d4 = CheckpointResult(
                checkpoint_name="D4",
                checkpoint_description="Test Execution",
                status=CheckpointStatus.SKIPPED,
                files_checked=[],
                files_passed=[],
                files_failed=[],
                errors={}
            )
    else:
        logger.info("Checkpoint D1-D4: SKIPPED (A, B, or C failed)")
        # Create skipped checkpoints
        checkpoint_d1 = CheckpointResult(
            checkpoint_name="D1",
            checkpoint_description="Page Object Structure Validation",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        )
        checkpoint_d2 = CheckpointResult(
            checkpoint_name="D2",
            checkpoint_description="Method Contract Validation",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        )
        checkpoint_d3 = CheckpointResult(
            checkpoint_name="D3",
            checkpoint_description="Method Signature Validation",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        )
        checkpoint_d4 = CheckpointResult(
            checkpoint_name="D4",
            checkpoint_description="Test Execution",
            status=CheckpointStatus.SKIPPED,
            files_checked=[],
            files_passed=[],
            files_failed=[],
            errors={}
        )
    
    # Backward compatibility: checkpoint_d = checkpoint_d4
    checkpoint_d = checkpoint_d4
    
    # Build verification results
    results = VerificationResults(
        checkpoint_a=checkpoint_a,
        checkpoint_b=checkpoint_b,
        checkpoint_c=checkpoint_c,
        checkpoint_d1=checkpoint_d1,
        checkpoint_d2=checkpoint_d2,
        checkpoint_d3=checkpoint_d3,
        checkpoint_d4=checkpoint_d4,
        checkpoint_d=checkpoint_d,  # Backward compatibility
        all_passed=False
    )
    
    # Check if all passed (including all D checkpoints)
    all_passed = (
        checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED and
        checkpoint_d1.status == CheckpointStatus.PASSED and
        checkpoint_d2.status == CheckpointStatus.PASSED and
        checkpoint_d3.status == CheckpointStatus.PASSED and
        checkpoint_d4.status == CheckpointStatus.PASSED
    )
    results.all_passed = all_passed
    
    # Update state
    state["verification_results"] = results.model_dump()
    state["verification_passed"] = all_passed
    
    # Log summary
    logger.info("-" * 40)
    logger.info("VERIFICATION SUMMARY")
    logger.info(f"  Checkpoint A (Syntax): {checkpoint_a.status.value}")
    logger.info(f"  Checkpoint B (Imports): {checkpoint_b.status.value}")
    logger.info(f"  Checkpoint C (Collection): {checkpoint_c.status.value}")
    logger.info(f"  Checkpoint D1 (Page Object Structure): {checkpoint_d1.status.value}")
    logger.info(f"  Checkpoint D2 (Method Contracts): {checkpoint_d2.status.value}")
    logger.info(f"  Checkpoint D3 (Method Signatures): {checkpoint_d3.status.value}")
    logger.info(f"  Checkpoint D4 (Test Execution): {checkpoint_d4.status.value}")
    if checkpoint_d4.metadata:
        logger.info(f"    Tests: {checkpoint_d4.metadata.get('tests_passed', 0)} passed, "
                   f"{checkpoint_d4.metadata.get('tests_failed', 0)} failed")
    logger.info(f"  Overall: {'PASSED' if all_passed else 'FAILED'}")
    logger.info("-" * 40)
    
    # Collect all errors for recovery
    if not all_passed:
        all_errors = {}
        for cp in [checkpoint_a, checkpoint_b, checkpoint_c, 
                   checkpoint_d1, checkpoint_d2, checkpoint_d3, checkpoint_d4]:
            if cp and cp.errors:
                all_errors.update(cp.errors)
        
        if all_errors:
            logger.warning("Errors found:")
            for filepath, error in all_errors.items():
                # Handle both string and list errors
                error_str = error if isinstance(error, str) else '\n'.join(error) if isinstance(error, list) else str(error)
                logger.warning(f"  {filepath}: {error_str[:200]}")
    
    return state
