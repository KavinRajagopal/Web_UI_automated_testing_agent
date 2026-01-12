# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Web UI Test Generation Agent** built with LangGraph that automatically generates Selenium+Pytest automation code from manual test cases and UI element metadata. It uses Claude Opus 4.5 via AWS Bedrock to generate Page Objects, Flow classes, and test files.

## Commands

### Run the Agent
```bash
# Interactive mode (with human approval gate)
python -m src.agent --inputs inputs/saucedemo --output output/saucedemo

# Auto-approve mode (skip human gate, for CI/batch)
python -m src.agent --inputs inputs/saucedemo --output output/saucedemo --auto

# Quick test run
python test_agent.py

# Show browser during tests (non-headless)
python test_agent.py --headless false
```

### Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_tools.py -v

# Run with coverage
pytest tests/ -v --cov=src
```

### LangGraph Development
```bash
# Start LangGraph Studio (local development UI)
langgraph dev

# LangSmith tracing (requires LANGCHAIN_API_KEY)
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT=web-ui-agent
python -m src.agent --inputs inputs/saucedemo --output output/saucedemo
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### LangGraph Pipeline (7 Nodes)

```
analyze_inputs -> human_gate -> planning -> generation -> verification -> recovery -> reporting
                     |                                      |              |
                     +----> END (rejected)                  |              |
                                                      (pass)|        (fail)|
                                                            v              v
                                                       reporting <--- recovery (max 5 retries)
```

### Key Files

| File | Purpose |
|------|---------|
| `src/agent.py` | Main entry point, graph builder, `TestGenerationAgent` class |
| `src/models/state.py` | `AgentState` TypedDict - all state flows through this |
| `src/llm/bedrock_client.py` | AWS Bedrock Converse API client for Claude Opus 4.5 |
| `langgraph.json` | LangGraph Studio configuration |

### Nodes (src/nodes/)

| Node | Purpose |
|------|---------|
| `onboarding.py` | Loads/validates inputs: module_spec.json, testcases.csv, element_metadata/*.json. Detects duplicate test cases, prioritizes by P0>P1>P2, caps at 10 tests. |
| `human_gates.py` | Human-in-the-loop approval checkpoint |
| `planning.py` | LLM generates code generation plan (pages, flows, tests structure) |
| `generation.py` | LLM generates Page Objects, Flow classes, test files, conftest.py |
| `verification/verification_node.py` | 4-checkpoint validation: A=Syntax, B=Imports, C=pytest collection, D=pytest execution |
| `recovery.py` | LLM fixes errors from verification, with loop detection (max 5 retries) |
| `reporting.py` | Saves files, generates AI report with cost analysis |

### Input Files Structure

```
inputs/<project>/
├── module_spec.json      # App metadata: name, URL, pages
├── testcases.csv         # Manual test cases with steps
└── element_metadata/     # One JSON per page
    ├── loginpage.json
    ├── productspage.json
    └── cartpage.json
```

### Output Structure

```
output/<project>/
├── pages/                # Page Object classes
│   ├── base_page.py
│   ├── login_page.py
│   └── ...
├── flows/                # Flow helper classes
├── tests/                # Pytest test files
│   ├── conftest.py
│   └── test_<module>.py
├── pytest.ini
├── report.json           # AI-generated report with cost analysis
└── event_log.json        # Trace of all agent events
```

## Key Patterns

### State Management
All data flows through `AgentState` TypedDict. Each node reads from and writes to this state. Important fields:
- `generated_files`: Dict[str, str] - filepath -> code content
- `verification_passed`: bool
- `llm_input_tokens/llm_output_tokens`: Token tracking for cost calculation

### LLM Usage
The agent uses `BedrockClient` for all LLM calls. Locators are generated **deterministically** from element metadata (not by LLM) to ensure correct selectors. The LLM generates method logic and test structure.

### Verification Checkpoints
- **A**: Python syntax (AST parse)
- **B**: Import resolution
- **C**: pytest --collect-only
- **D**: pytest execution with error extraction

### Recovery Loop
If verification fails, recovery node uses LLM to fix errors. Includes loop detection to prevent infinite retries of the same error. Max 5 attempts before marking `needs_human_intervention`.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `LANGCHAIN_TRACING_V2=true` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_PROJECT` | LangSmith project name |
| `HEADLESS=true/false` | Control browser visibility in tests |
| `ENABLE_ALLURE=true` | Enable Allure reporting |

## AWS Configuration

Uses AWS Bedrock with Claude Opus 4.5. Configure via:
- AWS profile: `--profile <name>` flag or `llm_profile` parameter
- Region: `--region` flag (default: us-east-2)
- Model: `us.anthropic.claude-opus-4-5-20251101-v1:0` (cross-region inference profile)
