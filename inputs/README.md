# Input Files Guide

This directory contains all input files for the Web UI Test Generation Agent.

## Directory Structure

```
inputs/
├── module_spec.json           # Module configuration (REQUIRED)
├── testcases.csv              # Test cases from spreadsheet (REQUIRED)
├── element_metadata/          # UI element selectors (REQUIRED)
│   ├── login_elements.json
│   ├── home_page_elements.json
│   └── ...
└── README.md                  # This file
```

---

## 1. module_spec.json (REQUIRED)

Defines the test module configuration.

**Location:** `inputs/module_spec.json`

See `templates/module_spec_template.json` for the full template.

---

## 2. testcases.csv (REQUIRED)

Test cases exported from your spreadsheet.

**Location:** `inputs/testcases.csv`

**Required columns:**
- `test_id` - Unique test ID (e.g., TC_LOGIN_001)
- `test_name` - Human-readable test name
- `module` - Module name (must match module_spec.json)
- `steps` - Pipe-delimited steps (e.g., "Step 1|Step 2|Step 3")
- `expected_result` - Expected outcome

**Optional columns:**
- `priority` - P0, P1, P2 (default: P1)
- `preconditions` - Setup requirements
- `test_data` - Pipe-delimited key=value pairs
- `tags` - Comma-separated tags
- `page_name` - Primary page for this test

---

## 3. element_metadata/ (REQUIRED)

JSON files containing UI element selectors for each page.

**Location:** `inputs/element_metadata/<page_name>_elements.json`

See `templates/element_template.json` for the full template.

---

## How to Add Your Data

1. **Copy templates:**
   ```bash
   cp templates/module_spec_template.json inputs/module_spec.json
   cp templates/element_template.json inputs/element_metadata/login_elements.json
   ```

2. **Edit module_spec.json** with your app details

3. **Export your CSV** from the test case spreadsheet

4. **Extract elements** from DevTools and create element JSON files

5. **Run the agent:**
   ```bash
   python -m src.main --input inputs/ --output automation_repo/
   ```
