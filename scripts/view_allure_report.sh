#!/bin/bash
# Script to generate and view Allure report
# Usage: ./scripts/view_allure_report.sh [output_directory]

set -e

# Get output directory from argument or use default
OUTPUT_DIR="${1:-output/saucedemo}"

# Check if allure-results directory exists
if [ ! -d "$OUTPUT_DIR/allure-results" ]; then
    echo "❌ Error: allure-results directory not found in $OUTPUT_DIR"
    echo ""
    echo "To generate Allure results, run tests with Allure enabled:"
    echo "  cd $OUTPUT_DIR"
    echo "  pytest tests/ -v"
    echo ""
    echo "Or regenerate with Allure enabled:"
    echo "  python -m src.agent --inputs inputs/saucedemo --output $OUTPUT_DIR --allure --auto"
    exit 1
fi

# Check if Allure CLI is installed
if ! command -v allure &> /dev/null; then
    echo "❌ Error: Allure CLI is not installed"
    echo ""
    echo "Install Allure CLI:"
    echo "  macOS: brew install allure"
    echo "  Linux: See https://github.com/allure-framework/allure2/releases"
    echo "  Or use: npm install -g allure-commandline"
    exit 1
fi

echo "📊 Generating Allure report from $OUTPUT_DIR/allure-results..."
cd "$OUTPUT_DIR"

# Generate report
allure generate allure-results -o allure-report --clean

if [ $? -eq 0 ]; then
    echo "✅ Allure report generated successfully!"
    echo ""
    echo "📖 Opening Allure report in browser..."
    echo "   (Press Ctrl+C to stop the server)"
    echo ""
    
    # Serve the report (opens browser automatically)
    allure serve allure-results
else
    echo "❌ Failed to generate Allure report"
    exit 1
fi
