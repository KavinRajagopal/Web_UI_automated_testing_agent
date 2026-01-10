#!/usr/bin/env python3
"""Script to generate and view Allure report.

Usage:
    python scripts/view_allure_report.py [output_directory]
    
Example:
    python scripts/view_allure_report.py output/saucedemo
"""

import os
import sys
import subprocess
from pathlib import Path


def check_allure_installed():
    """Check if Allure CLI is installed."""
    try:
        subprocess.run(["allure", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    # Get output directory from argument or use default
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output/saucedemo"
    output_path = Path(output_dir)
    
    # Check if allure-results directory exists
    allure_results = output_path / "allure-results"
    if not allure_results.exists():
        print(f"❌ Error: allure-results directory not found in {output_dir}")
        print()
        print("To generate Allure results, run tests with Allure enabled:")
        print(f"  cd {output_dir}")
        print("  pytest tests/ -v")
        print()
        print("Or regenerate with Allure enabled:")
        print(f"  python -m src.agent --inputs inputs/saucedemo --output {output_dir} --allure --auto")
        sys.exit(1)
    
    # Check if Allure CLI is installed
    if not check_allure_installed():
        print("❌ Error: Allure CLI is not installed")
        print()
        print("Install Allure CLI:")
        print("  macOS: brew install allure")
        print("  Linux: See https://github.com/allure-framework/allure2/releases")
        print("  Or use: npm install -g allure-commandline")
        sys.exit(1)
    
    print(f"📊 Generating Allure report from {allure_results}...")
    
    # Change to output directory
    os.chdir(output_path)
    
    # Generate report
    try:
        subprocess.run(
            ["allure", "generate", "allure-results", "-o", "allure-report", "--clean"],
            check=True
        )
        print("✅ Allure report generated successfully!")
        print()
        print("📖 Opening Allure report in browser...")
        print("   (Press Ctrl+C to stop the server)")
        print()
        
        # Serve the report (opens browser automatically)
        subprocess.run(["allure", "serve", "allure-results"])
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate Allure report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
