#!/usr/bin/env python3
"""Test script to run the agent with the enhanced test cases."""

import sys
import os
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent import TestGenerationAgent

def main():
    """Run the agent with saucedemo inputs."""
    parser = argparse.ArgumentParser(description="Run the Web UI Test Generation Agent")
    parser.add_argument(
        "--headless",
        type=str,
        default="true",
        help="Run tests in headless mode (default: true). Use --headless false to disable."
    )
    args = parser.parse_args()
    
    # Parse headless flag
    headless_mode = args.headless.lower() == "true"
    
    print("=" * 60)
    print("TESTING ENHANCED AGENT WITH DUPLICATE TEST CASES")
    print("=" * 60)
    print(f"Headless mode: {headless_mode}")
    print()
    
    # Initialize agent
    agent = TestGenerationAgent(
        inputs_path="inputs/saucedemo",
        output_path="output/saucedemo",
        llm_model_id="us.anthropic.claude-opus-4-5-20251101-v1:0",
        llm_region="us-east-2",
        llm_profile="tring-kavin",  # Update with your profile
        auto_approve=True,  # Skip human gates for testing
        enable_allure=False,  # Disable Allure for faster testing
        headless_mode=headless_mode
    )
    
    print("Starting agent run...")
    print()
    
    try:
        # Run agent
        result = agent.run(stream=False)
        
        print()
        print("=" * 60)
        print("AGENT RUN COMPLETE")
        print("=" * 60)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Session ID: {result.get('session_id', 'unknown')}")
        
        # Check for test case analysis
        if result.get('test_case_analysis'):
            analysis = result['test_case_analysis']
            print()
            print("TEST CASE ANALYSIS RESULTS:")
            print(f"  Total input tests: {analysis.get('total_input_tests', 0)}")
            print(f"  Duplicates found: {analysis.get('duplicate_count', 0)}")
            print(f"  Efficient test count: {analysis.get('efficient_test_count', 0)}")
            print(f"  Suggested tests: {len(analysis.get('suggested_tests', []))}")
            print(f"  Overall coverage: {analysis.get('overall_coverage', 0):.1f}%")
        
        # Check for scratchpad
        scratchpad_path = "output/saucedemo/generation_plan.md"
        if os.path.exists(scratchpad_path):
            print()
            print(f"✓ Scratchpad created: {scratchpad_path}")
        
        # Check for generated files
        output_dir = Path("output/saucedemo")
        if output_dir.exists():
            test_files = list(output_dir.rglob("test_*.py"))
            page_files = list((output_dir / "pages").glob("*.py")) if (output_dir / "pages").exists() else []
            print()
            print(f"Generated files:")
            print(f"  Test files: {len(test_files)}")
            print(f"  Page objects: {len(page_files)}")
        
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
