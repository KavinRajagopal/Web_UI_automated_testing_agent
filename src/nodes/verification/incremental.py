"""Incremental verification checkpoints for multi-stage generation."""

import logging
import os
from typing import Dict

from ...models.schemas import CheckpointResult, CheckpointStatus, VerificationResults
from .checkpoint_a import checkpoint_a_syntax
from .checkpoint_b import checkpoint_b_imports
from .checkpoint_d1 import checkpoint_d1_page_object_structure
from .checkpoint_d2 import checkpoint_d2_method_contracts
from .checkpoint_c import checkpoint_c_collect

logger = logging.getLogger(__name__)


def verify_page_objects(
    generated_files: Dict[str, str],
    output_path: str
) -> VerificationResults:
    """
    Verify page objects after generation (Stage 1).
    
    Checks:
    - Syntax (A)
    - Imports (B)
    - Page Object Structure (D1)
    
    Args:
        generated_files: All generated files
        output_path: Output directory
        
    Returns:
        VerificationResults with Stage 1 checkpoints
    """
    logger.info("=" * 60)
    logger.info("INCREMENTAL VERIFICATION: Page Objects (Stage 1)")
    logger.info("=" * 60)
    
    # Filter to only page object files
    page_files = {
        k: v for k, v in generated_files.items()
        if k.startswith("pages/")
    }
    
    if not page_files:
        logger.warning("No page files found for verification")
        return VerificationResults(all_passed=False)
    
    checkpoint_a = checkpoint_a_syntax(page_files)
    logger.info(f"  Checkpoint A (Syntax): {checkpoint_a.status.value} "
                f"({len(checkpoint_a.files_passed)}/{len(checkpoint_a.files_checked)} passed)")
    
    checkpoint_b = checkpoint_b_imports(page_files)
    logger.info(f"  Checkpoint B (Imports): {checkpoint_b.status.value} "
                f"({len(checkpoint_b.files_passed)}/{len(checkpoint_b.files_checked)} passed)")
    
    checkpoint_d1 = checkpoint_d1_page_object_structure(page_files)
    logger.info(f"  Checkpoint D1 (Structure): {checkpoint_d1.status.value} "
                f"({len(checkpoint_d1.files_passed)}/{len(checkpoint_d1.files_checked)} passed)")
    
    all_passed = (
        checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_d1.status == CheckpointStatus.PASSED
    )
    
    logger.info(f"  Stage 1 Overall: {'✅ PASSED' if all_passed else '❌ FAILED'}")
    logger.info("=" * 60)
    
    return VerificationResults(
        checkpoint_a=checkpoint_a,
        checkpoint_b=checkpoint_b,
        checkpoint_d1=checkpoint_d1,
        all_passed=all_passed
    )


def verify_flows(
    generated_files: Dict[str, str],
    output_path: str,
    page_objects_verified: bool = True
) -> VerificationResults:
    """
    Verify flows after generation (Stage 2).
    
    Checks:
    - Syntax (A) - flows only
    - Imports (B) - can flows import pages?
    - Method calls (D2-partial) - do flow methods call valid page methods?
    
    Args:
        generated_files: All generated files
        output_path: Output directory
        page_objects_verified: Whether page objects passed verification
        
    Returns:
        VerificationResults with Stage 2 checkpoints
    """
    logger.info("=" * 60)
    logger.info("INCREMENTAL VERIFICATION: Flows (Stage 2)")
    logger.info("=" * 60)
    
    if not page_objects_verified:
        logger.warning("  Skipping flow verification - page objects not verified")
        return VerificationResults(all_passed=False)
    
    # Filter to flow files
    flow_files = {
        k: v for k, v in generated_files.items()
        if k.startswith("flows/")
    }
    
    if not flow_files:
        logger.info("  No flow files to verify")
        return VerificationResults(all_passed=True)
    
    # Include page files for import validation
    page_files = {
        k: v for k, v in generated_files.items()
        if k.startswith("pages/")
    }
    
    all_files = {**flow_files, **page_files}
    
    checkpoint_a = checkpoint_a_syntax(flow_files)
    logger.info(f"  Checkpoint A (Syntax): {checkpoint_a.status.value} "
                f"({len(checkpoint_a.files_passed)}/{len(checkpoint_a.files_checked)} passed)")
    
    checkpoint_b = checkpoint_b_imports(all_files)  # Check flows can import pages
    logger.info(f"  Checkpoint B (Imports): {checkpoint_b.status.value} "
                f"({len(checkpoint_b.files_passed)}/{len(checkpoint_b.files_checked)} passed)")
    
    # Partial D2: Check if flow methods call valid page methods
    from ...tools.method_extractor import extract_method_calls, extract_methods_from_files
    
    page_methods = extract_methods_from_files(page_files)
    flow_errors = {}
    
    for flow_file, code in flow_files.items():
        calls = extract_method_calls(code)
        for call in calls:
            class_name = call.get("class_name")
            method_name = call.get("method_name")
            
            if class_name and method_name:
                # Check if this method exists in page objects
                found = False
                for page_file, methods in page_methods.items():
                    for cls_name, method_list in methods.items():
                        if class_name.lower() == cls_name.lower():
                            if method_name in method_list:
                                found = True
                            break
                    if found:
                        break
                
                if not found:
                    if flow_file not in flow_errors:
                        flow_errors[flow_file] = []
                    flow_errors[flow_file].append(
                        f"Line {call.get('line')}: {class_name}.{method_name}() not found in page objects"
                    )
    
    checkpoint_d2_partial = CheckpointResult(
        checkpoint_name="D2-Partial",
        checkpoint_description="Flow Method Calls Validation",
        status=CheckpointStatus.PASSED if not flow_errors else CheckpointStatus.FAILED,
        files_checked=list(flow_files.keys()),
        files_passed=[f for f in flow_files.keys() if f not in flow_errors],
        files_failed=list(flow_errors.keys()),
        errors=flow_errors
    )
    logger.info(f"  Checkpoint D2-Partial (Flow Calls): {checkpoint_d2_partial.status.value} "
                f"({len(checkpoint_d2_partial.files_passed)}/{len(checkpoint_d2_partial.files_checked)} passed)")
    
    all_passed = (
        checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_d2_partial.status == CheckpointStatus.PASSED
    )
    
    logger.info(f"  Stage 2 Overall: {'✅ PASSED' if all_passed else '❌ FAILED'}")
    logger.info("=" * 60)
    
    return VerificationResults(
        checkpoint_a=checkpoint_a,
        checkpoint_b=checkpoint_b,
        checkpoint_d2=checkpoint_d2_partial,
        all_passed=all_passed
    )


def verify_tests(
    generated_files: Dict[str, str],
    output_path: str,
    previous_stages_passed: bool = True
) -> VerificationResults:
    """
    Verify tests after generation (Stage 3).
    
    Checks:
    - Syntax (A) - tests only
    - Imports (B) - can tests import flows/pages?
    - Collection (C) - can pytest discover tests?
    - Method Contracts (D2) - do tests call valid methods?
    - Method Signatures (D3) - do method calls match signatures?
    
    Args:
        generated_files: All generated files
        output_path: Output directory
        previous_stages_passed: Whether previous stages passed
        
    Returns:
        VerificationResults with Stage 3 checkpoints
    """
    logger.info("=" * 60)
    logger.info("INCREMENTAL VERIFICATION: Tests (Stage 3)")
    logger.info("=" * 60)
    
    if not previous_stages_passed:
        logger.warning("  Skipping test verification - previous stages failed")
        return VerificationResults(all_passed=False)
    
    # Filter to test files
    test_files = {
        k: v for k, v in generated_files.items()
        if k.startswith("tests/")
    }
    
    if not test_files:
        logger.warning("No test files found for verification")
        return VerificationResults(all_passed=False)
    
    # Include all files for import validation
    all_files = generated_files
    
    # Write files to disk for collection check
    os.makedirs(output_path, exist_ok=True)
    for filepath, code in all_files.items():
        full_path = os.path.join(output_path, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(code)
    
    checkpoint_a = checkpoint_a_syntax(test_files)
    logger.info(f"  Checkpoint A (Syntax): {checkpoint_a.status.value} "
                f"({len(checkpoint_a.files_passed)}/{len(checkpoint_a.files_checked)} passed)")
    
    checkpoint_b = checkpoint_b_imports(all_files)
    logger.info(f"  Checkpoint B (Imports): {checkpoint_b.status.value} "
                f"({len(checkpoint_b.files_passed)}/{len(checkpoint_b.files_checked)} passed)")
    
    checkpoint_c = checkpoint_c_collect(all_files, output_path)
    logger.info(f"  Checkpoint C (Collection): {checkpoint_c.status.value}")
    
    # Only run D2/D3 if A, B, C passed
    checkpoint_d2 = None
    checkpoint_d3 = None
    
    if (checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED):
        
        checkpoint_d2 = checkpoint_d2_method_contracts(all_files)
        logger.info(f"  Checkpoint D2 (Contracts): {checkpoint_d2.status.value} "
                    f"({len(checkpoint_d2.files_passed)}/{len(checkpoint_d2.files_checked)} passed)")
        
        from .checkpoint_d3 import checkpoint_d3_method_signatures
        checkpoint_d3 = checkpoint_d3_method_signatures(all_files)
        logger.info(f"  Checkpoint D3 (Signatures): {checkpoint_d3.status.value} "
                    f"({len(checkpoint_d3.files_passed)}/{len(checkpoint_d3.files_checked)} passed)")
    else:
        logger.info("  Checkpoint D2/D3: SKIPPED (A, B, or C failed)")
        checkpoint_d2 = CheckpointResult(
            checkpoint_name="D2",
            checkpoint_description="Method Contract Validation",
            status=CheckpointStatus.SKIPPED,
            files_checked=[], files_passed=[], files_failed=[], errors={}
        )
        checkpoint_d3 = CheckpointResult(
            checkpoint_name="D3",
            checkpoint_description="Method Signature Validation",
            status=CheckpointStatus.SKIPPED,
            files_checked=[], files_passed=[], files_failed=[], errors={}
        )
    
    all_passed = (
        checkpoint_a.status == CheckpointStatus.PASSED and
        checkpoint_b.status == CheckpointStatus.PASSED and
        checkpoint_c.status == CheckpointStatus.PASSED and
        (checkpoint_d2 is None or checkpoint_d2.status == CheckpointStatus.PASSED) and
        (checkpoint_d3 is None or checkpoint_d3.status == CheckpointStatus.PASSED)
    )
    
    logger.info(f"  Stage 3 Overall: {'✅ PASSED' if all_passed else '❌ FAILED'}")
    logger.info("=" * 60)
    
    return VerificationResults(
        checkpoint_a=checkpoint_a,
        checkpoint_b=checkpoint_b,
        checkpoint_c=checkpoint_c,
        checkpoint_d2=checkpoint_d2,
        checkpoint_d3=checkpoint_d3,
        all_passed=all_passed
    )
