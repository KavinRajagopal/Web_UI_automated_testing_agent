# Android/Appium Support for Web UI Test Generation Agent

> **Primary Reference Document** - Maintained across sessions
> **Last Updated**: 2025-01-16
> **Status**: Planning Complete - Ready for Implementation

---

## Implementation Progress

| Phase | Description | Status | Files Changed |
|-------|-------------|--------|---------------|
| 1 | Schema & State Updates | ⬜ Not Started | `src/models/schemas.py`, `src/models/state.py` |
| 2 | Create Templates Module | ⬜ Not Started | `src/templates/*` (new) |
| 3 | Update Generation Node | ⬜ Not Started | `src/nodes/generation.py` |
| 4 | Update Recovery Node | ⬜ Not Started | `src/nodes/recovery.py` |
| 5 | Update Planning Node | ⬜ Not Started | `src/nodes/planning.py` |
| 6 | Update Onboarding (Prereq Checks) | ⬜ Not Started | `src/nodes/onboarding.py` |
| 7 | Update Verification Node | ⬜ Not Started | `src/nodes/verification/verification_node.py` |
| 8 | Add Dependencies | ⬜ Not Started | `requirements.txt` |
| 9 | Sample Android Input | ⬜ Not Started | `inputs/saucedemo_android/*` (new) |

**Legend**: ⬜ Not Started | 🔄 In Progress | ✅ Complete | ❌ Blocked

---

## Quick Reference

**Run Command (after implementation)**:
```bash
# Start prerequisites first
emulator -avd Pixel_4_API_30 &
appium &

# Run agent
python -m src.agent --inputs inputs/saucedemo_android --output output/saucedemo_android
```

**Key Files**:
- Schema: `src/models/schemas.py` - PlatformType, AndroidConfig
- Templates: `src/templates/android_templates.py` - Appium code templates
- Onboarding: `src/nodes/onboarding.py` - Prerequisite checks

---

# PART 1: ARCHITECTURE DECISIONS

## 1.1 Template Factory Pattern

### Current State
The generation node (`src/nodes/generation.py`) has hardcoded Selenium templates:
```
BASE_PAGE_TEMPLATE     (lines 117-182)  → Selenium WebDriver imports
CONFTEST_TEMPLATE      (lines 184-258)  → Chrome driver setup
PAGE_GENERATION_PROMPT (lines 274-317)  → "USE SELENIUM ONLY" directive
TEST_GENERATION_PROMPT (lines 320-352)  → Selenium references
```

### Proposed Architecture

```
src/templates/
├── __init__.py           # Exports get_templates()
├── base_templates.py     # Abstract base class
├── web_templates.py      # Selenium templates (extract from generation.py)
├── android_templates.py  # Appium templates (new)
└── template_factory.py   # Factory: platform → templates
```

**Template Interface:**
```python
class BaseTemplates(ABC):
    @property
    @abstractmethod
    def BASE_PAGE_TEMPLATE(self) -> str: ...

    @property
    @abstractmethod
    def CONFTEST_TEMPLATE(self) -> str: ...

    @property
    @abstractmethod
    def PAGE_GENERATION_PROMPT(self) -> str: ...

    @property
    @abstractmethod
    def TEST_GENERATION_PROMPT(self) -> str: ...

    @abstractmethod
    def get_by_type(self, selector_type: str) -> str: ...
```

**Factory Usage:**
```python
# In generation_node():
templates = get_templates(platform_type)  # Returns WebTemplates or AndroidTemplates
base_page_code = templates.BASE_PAGE_TEMPLATE
by_type = templates.get_by_type("accessibility_id")  # → "AppiumBy.ACCESSIBILITY_ID"
```

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Template Factory (chosen)** | Clean separation, easy to extend | More files |
| **Inheritance hierarchy** | OOP patterns | Complex, harder to understand |
| **Inline conditionals** | Simple, no new files | Messy, hard to maintain |
| **YAML/JSON templates** | Declarative | Less flexible for complex logic |

### Decision Rationale
Template Factory is chosen because:
1. LLM prompts are strings with formatting - factory fits naturally
2. Easy to add iOS later without touching existing code
3. Clear separation: web_templates.py vs android_templates.py
4. Testable: can unit test each template class independently

---

## 1.2 Verification Strategy for Android

### The Problem
Web verification only needs Chrome browser (ubiquitous). Android needs:
1. **Appium server** running at http://localhost:4723
2. **Android SDK** with adb in PATH
3. **Emulator/device** connected and booted
4. **APK** installed on device

### Proposed Solution: Fail Early in Onboarding

**Key Decision**: Check prerequisites in **Onboarding**, not Verification. Agent stops immediately if infrastructure is missing.

```
┌──────────────────────────────────────────────────────────────┐
│                    ONBOARDING (Fail Early)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Load module_spec.json                                       │
│       │                                                      │
│       ▼                                                      │
│  if platform_type == "android":                              │
│       │                                                      │
│       ▼                                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PREREQUISITE CHECKS (all must pass to continue)        │ │
│  │                                                         │ │
│  │  1. ✓ Appium server running (HTTP GET /status)          │ │
│  │  2. ✓ Android SDK installed (adb version)               │ │
│  │  3. ✓ Device/emulator connected (adb devices)           │ │
│  │  4. ✓ APK exists (if app_path specified)                │ │
│  │                                                         │ │
│  │  ANY FAIL → Stop immediately with clear error message   │ │
│  └────────────────────────────────────────────────────────┘ │
│       │                                                      │
│       ▼ (all passed)                                         │
│  Continue to Planning → Generation → Verification            │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    VERIFICATION (Later)                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Checkpoint A (Syntax)     ──────► PASS/FAIL                │
│  Checkpoint B (Imports)    ──────► PASS/FAIL                │
│  Checkpoint C (Collection) ──────► PASS/FAIL                │
│  Checkpoint D (Execution)  ──────► PASS/FAIL                │
│                                                              │
│  (Infrastructure already verified - just run tests)          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Checkpoint D Status Values for Android

| Status | Meaning | When |
|--------|---------|------|
| `PASSED` | Tests executed successfully | All tests pass on device |
| `FAILED` | Verification failed | Infrastructure missing OR tests failed |

**Note**: No SKIPPED status - Android tests require full infrastructure.

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `APPIUM_SERVER` | `http://localhost:4723` | Appium server URL |
| `ANDROID_TIMEOUT` | `600` | Test execution timeout (seconds) |

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Preflight + Fail (chosen)** | Ensures full verification | Requires infrastructure setup |
| **Graceful skip** | Works without setup | Doesn't verify execution |
| **Docker container** | Reproducible | Heavy, slow, complex |
| **Cloud device farm** | No local setup | Costs money, API keys |

### Decision Rationale
Preflight + Fail is chosen because:
1. Android tests must be verified end-to-end to ensure correctness
2. Clear error messages guide user to set up infrastructure
3. Ensures generated code actually works on real device
4. Aligns with existing web verification behavior (requires Chrome)

---

## 1.3 Input Schema Design

### Current Schema (Web)
```json
{
  "module_name": "saucedemo",
  "app_name": "SauceDemo",
  "app_url": "https://www.saucedemo.com",
  "browser": "chrome",
  "selector_priority": ["id", "data-testid", "name", "css"],
  "pages": [...]
}
```

### Proposed Schema (Multi-Platform)

```json
{
  "module_name": "saucedemo_android",
  "app_name": "SauceLabs My Demo App",

  // NEW: Platform discriminator
  "platform_type": "android",  // "web" (default) | "android"

  // NEW: Android-specific config (required when platform_type="android")
  "android_config": {
    "app_package": "com.saucelabs.mydemoapp.rn",
    "app_activity": ".MainActivity",
    "device_name": "Android Emulator",
    "platform_version": "11.0",
    "automation_name": "UiAutomator2",
    "app_path": "apps/mda-2.0.0-21.apk",  // Optional: path to APK
    "no_reset": false                      // Reset app state between tests
  },

  // Existing fields (web-only, ignored for Android)
  "app_url": null,
  "browser": null,

  // Updated selector priorities for Android
  "selector_priority": ["accessibility_id", "id", "xpath"],
  "avoid_selectors": ["css"],  // CSS not supported in Appium

  "pages": [...]
}
```

### Element Metadata Schema

**Web (existing):**
```json
{
  "name": "login_button",
  "selectors": [
    {"selector_type": "data-testid", "value": "login-button"},
    {"selector_type": "css", "value": "#login-button"}
  ]
}
```

**Android (new selector types):**
```json
{
  "name": "login_button",
  "selectors": [
    {"selector_type": "accessibility_id", "value": "Login button"},
    {"selector_type": "id", "value": "com.saucelabs.mydemoapp.rn:id/loginBtn"},
    {"selector_type": "xpath", "value": "//android.widget.Button[@content-desc='Login button']"}
  ]
}
```

### New Selector Types for Android

| Type | Maps To | Example |
|------|---------|---------|
| `accessibility_id` | `AppiumBy.ACCESSIBILITY_ID` | `"Login button"` |
| `id` | `AppiumBy.ID` | `"com.app:id/btn"` |
| `resource_id` | `AppiumBy.ID` | Same as id |
| `xpath` | `AppiumBy.XPATH` | `"//android.widget.Button"` |
| `android_uiautomator` | `AppiumBy.ANDROID_UIAUTOMATOR` | `"new UiSelector().text(\"Login\")"` |

### Validation Rules

```python
def validate_module_spec(spec):
    if spec.platform_type == "android":
        # Required fields
        assert spec.android_config is not None
        assert spec.android_config.app_package
        assert spec.android_config.app_activity

        # Warnings
        if "css" in spec.selector_priority:
            warn("CSS selectors not supported on Android")

    if spec.platform_type == "web":
        # Required fields
        assert spec.app_url is not None
```

---

---

## 1.4 User Workflow & Infrastructure Setup

### What the Agent Does vs What the Human Does

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HUMAN RESPONSIBILITIES (Before Agent)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. ONE-TIME SETUP (do once per machine):                              │
│     • Install Node.js + Appium: npm install -g appium                  │
│     • Install UiAutomator2 driver: appium driver install uiautomator2  │
│     • Install Android SDK (Android Studio)                             │
│     • Create AVD (emulator): Android Studio → AVD Manager              │
│                                                                         │
│  2. BEFORE EACH AGENT RUN:                                             │
│     • Start Android emulator: emulator -avd <your_avd_name>            │
│     • Start Appium server: appium                                      │
│     • (Optional) Install APK: adb install <app.apk>                    │
│                                                                         │
│  3. PROVIDE INPUTS:                                                     │
│     • inputs/<project>/module_spec.json (with platform_type="android") │
│     • inputs/<project>/testcases.csv                                   │
│     • inputs/<project>/element_metadata/*.json                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AGENT RESPONSIBILITIES                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ONBOARDING NODE:                                                       │
│     • Validates module_spec.json (checks android_config is present)    │
│     • Loads testcases.csv and element_metadata                         │
│     • ⚠️ CHECKS PREREQUISITES (Appium, adb, device, APK)               │
│     • STOPS HERE if any prerequisite is missing                        │
│                                                                         │
│  PLANNING NODE:                                                         │
│     • Creates code generation plan                                      │
│     • Knows platform=android, adjusts prompts accordingly               │
│                                                                         │
│  GENERATION NODE:                                                       │
│     • Uses AndroidTemplates (Appium imports, mobile methods)           │
│     • Generates base_page.py with tap(), swipe(), hide_keyboard()      │
│     • Generates conftest.py with Appium Remote driver                  │
│     • Generates page objects with AppiumBy locators                    │
│                                                                         │
│  VERIFICATION NODE:                                                     │
│     • Checkpoint A: Syntax check                                       │
│     • Checkpoint B: Import check                                       │
│     • Checkpoint C: pytest --collect-only                              │
│     • Checkpoint D: Run tests on device                                │
│       (Infrastructure already verified in onboarding)                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detailed Human Workflow

**Step 1: One-Time Setup (10-15 minutes)**
```bash
# Install Appium
npm install -g appium
appium driver install uiautomator2

# Install Android SDK (if not already)
# Download Android Studio from https://developer.android.com/studio
# OR use command line tools: sdkmanager "platform-tools" "emulator"

# Create emulator (via Android Studio AVD Manager)
# OR: sdkmanager "system-images;android-30;google_apis;x86_64"
#     avdmanager create avd -n test_avd -k "system-images;android-30;google_apis;x86_64"
```

**Step 2: Before Running Agent (1-2 minutes)**
```bash
# Terminal 1: Start emulator
emulator -avd Pixel_4_API_30  # Use your AVD name

# Terminal 2: Start Appium (wait for emulator to boot first)
appium

# Terminal 3: Run the agent
python -m src.agent --inputs inputs/saucedemo_android --output output/saucedemo_android
```

**Step 3: Provide Inputs**

The human must create these files in `inputs/<project>/`:

| File | Purpose | Android-Specific |
|------|---------|------------------|
| `module_spec.json` | App config | `platform_type: "android"`, `android_config: {...}` |
| `testcases.csv` | Test steps | Same format as web |
| `element_metadata/*.json` | Element locators | Use `accessibility_id`, `id` (not CSS) |

### What Happens If Infrastructure Is Missing?

Agent fails **immediately during onboarding** (before any code generation):

```
$ python -m src.agent --inputs inputs/saucedemo_android --output output/saucedemo_android

[INFO] Onboarding: Loading module_spec.json...
[INFO] Onboarding: Platform: Android - Checking prerequisites...

============================================================
ANDROID PREREQUISITES NOT MET
============================================================
  ❌ Appium server not running. Start with: appium
  ❌ No Android device/emulator connected. Start emulator first.

Please fix the above issues before running the agent.
============================================================

[FAILED] Onboarding failed. Agent stopped.
```

**No code is generated** - agent stops immediately to save time.

### Inputs Required from Human

**1. module_spec.json** (platform_type="android"):
```json
{
  "module_name": "my_android_app",
  "app_name": "My App",
  "platform_type": "android",
  "android_config": {
    "app_package": "com.example.myapp",
    "app_activity": ".MainActivity",
    "device_name": "Android Emulator",
    "automation_name": "UiAutomator2"
  },
  "selector_priority": ["accessibility_id", "id", "xpath"],
  "pages": [...]
}
```

**2. element_metadata/login_screen.json** (Android selectors):
```json
{
  "page_name": "LoginScreen",
  "elements": [
    {
      "name": "username_input",
      "selectors": [
        {"selector_type": "accessibility_id", "value": "Username field"}
      ]
    }
  ]
}
```

**3. testcases.csv** (same format as web):
```csv
test_id,test_name,priority,steps,expected_result,test_data,page_name
TC_001,Valid Login,P0,Enter username|Enter password|Tap login,Home screen shown,username=test,LoginScreen
```

### Future Enhancement: Infrastructure Auto-Setup (Not in Current Scope)

In the future, we could add:
- `--setup-infra` flag to auto-start Appium/emulator
- Docker-based setup for CI environments
- Cloud device farm integration (BrowserStack, SauceLabs)

For now, the human is responsible for infrastructure setup.

---

## Summary: Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent Pipeline                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌────────────┐     │
│  │Onboarding│───►│Planning │───►│Generation│───►│Verification│     │
│  └──────────┘    └─────────┘    └──────────┘    └────────────┘     │
│       │              │               │                │             │
│       ▼              ▼               ▼                ▼             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Platform Detection                        │   │
│  │  module_spec.platform_type → "web" | "android"              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │              │               │                │             │
│       ▼              ▼               ▼                ▼             │
│  Validate        Platform-      Template           Preflight       │
│  android_config  aware prompts  Factory            Checks          │
│                                                                     │
│                          ┌─────────────────┐                       │
│                          │ Template Factory │                       │
│                          ├─────────────────┤                       │
│                          │ get_templates() │                       │
│                          │       │         │                       │
│                          │   ┌───┴───┐     │                       │
│                          │   ▼       ▼     │                       │
│                          │  Web   Android  │                       │
│                          │Templates Templates│                     │
│                          └─────────────────┘                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

# PART 2: IMPLEMENTATION PLAN

## Overview
Add Android/Appium test generation support to the existing Selenium-focused agent. Uses a **template factory pattern** for platform-specific code generation while maintaining full backward compatibility.

## Design Approach
- **Platform-aware configuration**: Add `platform_type` field to module_spec.json (`web`/`android`)
- **Template factory pattern**: Platform-specific code templates in `src/templates/`
- **Conditional logic**: Generation/recovery nodes select templates based on platform
- **Backward compatible**: Existing web projects work unchanged (default: `platform_type: "web"`)

---

## Implementation Plan

### Phase 1: Schema & State Updates

**File: `src/models/schemas.py`**
- Add `PlatformType` enum: `WEB`, `ANDROID`
- Add `AutomationName` enum: `UIAUTOMATOR2`, `ESPRESSO`
- Add `AndroidConfig` model with fields:
  - `app_package` (required)
  - `app_activity` (required)
  - `device_name` (default: "Android Emulator")
  - `platform_version` (optional)
  - `automation_name` (default: UiAutomator2)
  - `app_path` (optional - path to APK)
  - `no_reset` (default: True)
- Add mobile selector types to `SelectorType` enum:
  - `ACCESSIBILITY_ID`
  - `ANDROID_UIAUTOMATOR`
  - `RESOURCE_ID`
- Update `ModuleSpec` to include:
  - `platform_type: PlatformType = WEB`
  - `android_config: Optional[AndroidConfig]`

**File: `src/models/state.py`**
- Add `platform_type: str` field to `AgentState`
- Update `create_initial_state()` to set default `platform_type="web"`

---

### Phase 2: Create Templates Module

**New directory: `src/templates/`**

| File | Purpose |
|------|---------|
| `__init__.py` | Exports WebTemplates, AndroidTemplates, get_templates |
| `base_templates.py` | Abstract base class defining template interface |
| `web_templates.py` | Current Selenium templates (extracted from generation.py) |
| `android_templates.py` | New Appium templates |
| `template_factory.py` | Factory function to get platform-specific templates |

**AndroidTemplates includes:**
- `BASE_PAGE_TEMPLATE` with Appium imports and mobile methods:
  - `tap()`, `long_press()`, `swipe()`, `swipe_up()`, `swipe_down()`
  - `hide_keyboard()`, `get_current_activity()`, `get_current_package()`
- `CONFTEST_TEMPLATE` with Appium Remote driver setup and capabilities
- `PAGE_GENERATION_PROMPT` for Appium-based page objects
- `TEST_GENERATION_PROMPT` for mobile test generation
- `get_by_type()` mapping: id→AppiumBy.ID, accessibility_id→AppiumBy.ACCESSIBILITY_ID, etc.

---

### Phase 3: Update Generation Node

**File: `src/nodes/generation.py`**

1. **Remove hardcoded templates** (lines 117-352):
   - `BASE_PAGE_TEMPLATE`
   - `CONFTEST_TEMPLATE`
   - `PAGE_GENERATION_PROMPT`
   - `TEST_GENERATION_PROMPT`

2. **Add template factory usage**:
   ```python
   from ..templates.template_factory import get_templates

   def generation_node(state):
       platform_type = state.get("module_spec", {}).get("platform_type", "web")
       templates = get_templates(platform_type)
       # Use templates.BASE_PAGE_TEMPLATE, templates.CONFTEST_TEMPLATE, etc.
   ```

3. **Update functions to accept `templates` parameter**:
   - `_get_by_type(selector_type, templates)`
   - `_generate_locators_code(page_metadata, templates)`
   - `generate_page_class(..., templates)`
   - `generate_test_file(..., templates)`

4. **Platform-aware conftest generation**:
   - Web: Chrome driver with headless options
   - Android: Appium Remote driver with capabilities dict

---

### Phase 4: Update Recovery Node

**File: `src/nodes/recovery.py`**

1. **Make RECOVERY_PROMPT platform-aware**:
   - Load base page methods from templates
   - Use "APPIUM for Android" vs "SELENIUM for web" directive

2. **Update `_fix_with_llm()`** to:
   - Get platform_type from state
   - Use platform-specific recovery prompt

---

### Phase 5: Update Planning Node

**File: `src/nodes/planning.py`**

1. **Update `_build_planning_prompt()`**:
   - Include platform type in module info
   - For Android: show app_package, app_activity, device_name
   - For Web: show URL, browser

2. **Add Android-specific guidelines to system prompt**:
   - Appium locator strategies
   - CSS not supported on Android
   - Mobile-specific methods (tap, swipe, etc.)

---

### Phase 6: Update Onboarding/Validation (Critical - Fail Early)

**File: `src/nodes/onboarding.py`**

**Key Change**: Move ALL infrastructure checks to onboarding. Agent should not proceed past onboarding if prerequisites are missing.

1. **Add `_validate_android_config()` function**:
   - Require `android_config` when `platform_type="android"`
   - Require `app_package` and `app_activity`

2. **Add `_check_android_prerequisites()` function** (NEW - moved from verification):
   ```python
   def _check_android_prerequisites(android_config: dict) -> Tuple[bool, List[str]]:
       """Check Android prerequisites during onboarding. Fail early if not ready."""
       issues = []

       # Check 1: Appium server running
       appium_url = os.getenv("APPIUM_SERVER", "http://localhost:4723")
       try:
           import urllib.request
           req = urllib.request.urlopen(f"{appium_url}/status", timeout=5)
           if req.status != 200:
               issues.append(f"Appium server not responding at {appium_url}")
       except Exception:
           issues.append(f"❌ Appium server not running. Start with: appium")

       # Check 2: Android SDK (adb) available
       try:
           result = subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=5)
           if result.returncode != 0:
               issues.append("❌ adb not working properly")
       except FileNotFoundError:
           issues.append("❌ Android SDK not found. Install Android Studio and add adb to PATH")

       # Check 3: Device/emulator connected
       try:
           result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
           devices = [l for l in result.stdout.split('\n')[1:] if l.strip() and 'device' in l]
           if not devices:
               issues.append("❌ No Android device/emulator connected. Start emulator first.")
       except Exception as e:
           issues.append(f"❌ Failed to check devices: {e}")

       # Check 4: APK exists (if app_path specified)
       app_path = android_config.get("app_path")
       if app_path and not os.path.exists(app_path):
           issues.append(f"❌ APK not found at: {app_path}")

       return len(issues) == 0, issues
   ```

3. **Update `analyze_inputs_node()` to check prerequisites**:
   ```python
   def analyze_inputs_node(state: AgentState) -> AgentState:
       # ... load module_spec ...

       if module_spec.platform_type == "android":
           logger.info("Platform: Android - Checking prerequisites...")

           # Validate android_config
           if not module_spec.android_config:
               raise OnboardingError("android_config required for platform_type='android'")

           # Check infrastructure prerequisites
           ready, issues = _check_android_prerequisites(module_spec.android_config)
           if not ready:
               logger.error("=" * 60)
               logger.error("ANDROID PREREQUISITES NOT MET")
               logger.error("=" * 60)
               for issue in issues:
                   logger.error(f"  {issue}")
               logger.error("")
               logger.error("Please fix the above issues before running the agent.")
               logger.error("=" * 60)
               raise OnboardingError("Android prerequisites not met. See errors above.")

           logger.info("✓ Appium server running")
           logger.info("✓ Android SDK (adb) available")
           logger.info("✓ Device/emulator connected")
           if module_spec.android_config.app_path:
               logger.info("✓ APK found")
   ```

4. **Store platform_type in state**

**File: `src/parsers/module_parser.py`**
- Add selector_priority warnings for Android (recommend id, accessibility_id)

---

### Phase 7: Update Verification Node (Simplified for Android)

**Note**: Infrastructure checks (Appium, adb, device) are now done in **Onboarding (Phase 6)**. By the time we reach verification, we know infrastructure is ready.

**File: `src/nodes/verification/verification_node.py`**

1. **Update `_check_execution()` for Android**:
   ```python
   def _check_execution(generated_files, output_dir, headless=True, platform_type="web"):
       if platform_type == "android":
           # Infrastructure already verified in onboarding - just run tests
           env = os.environ.copy()
           env["APPIUM_SERVER"] = os.getenv("APPIUM_SERVER", "http://localhost:4723")
           timeout = 600  # 10 minutes for Android (slower than web)

           logger.info("  Running Android tests on device...")
       else:
           # Existing web logic
           env = os.environ.copy()
           env["HEADLESS"] = "true" if headless else "false"
           timeout = 300  # 5 minutes for web
   ```

2. **Update `_check_imports()` for Appium**:
   - Recognize `appium`, `AppiumBy` as valid modules
   - Add to allowed imports list

3. **Checkpoint D for Android**:
   - `PASSED`: Tests ran successfully on device
   - `FAILED`: Test assertions failed (not infrastructure - that's checked in onboarding)

---

### Phase 8: Add Dependencies

**File: `requirements.txt`**
```
Appium-Python-Client>=3.0.0
```

---

### Phase 9: Sample Android Input (SauceLabs My Demo App)

**Demo App**: [SauceLabs My Demo App (React Native)](https://github.com/saucelabs/my-demo-app-rn)
- Open source Android app (similar to saucedemo.com for web)
- APK available from GitHub releases
- Has login, products catalog, cart, checkout flows

**Create: `inputs/saucedemo_android/`**

`module_spec.json`:
```json
{
  "module_name": "saucedemo_android",
  "app_name": "SauceLabs My Demo App",
  "platform_type": "android",
  "android_config": {
    "app_package": "com.saucelabs.mydemoapp.rn",
    "app_activity": ".MainActivity",
    "device_name": "Android Emulator",
    "platform_version": "11.0",
    "automation_name": "UiAutomator2",
    "app_path": "apps/mda-2.0.0-21.apk",
    "no_reset": false
  },
  "environment": "local",
  "selector_priority": ["accessibility_id", "id", "xpath"],
  "avoid_selectors": ["css"],
  "description": "SauceLabs My Demo App - Android equivalent of saucedemo.com",
  "pages": [
    {
      "name": "LoginScreen",
      "element_metadata_file": "element_metadata/login_screen.json"
    },
    {
      "name": "ProductsScreen",
      "element_metadata_file": "element_metadata/products_screen.json"
    },
    {
      "name": "CartScreen",
      "element_metadata_file": "element_metadata/cart_screen.json"
    }
  ],
  "test_credentials": {
    "standard_user": "bob@example.com",
    "password": "10203040"
  }
}
```

`element_metadata/login_screen.json`:
```json
{
  "page_name": "LoginScreen",
  "description": "Login screen for SauceLabs My Demo App",
  "elements": [
    {
      "name": "username_input",
      "element_type": "input",
      "selectors": [
        {"selector_type": "accessibility_id", "value": "Username input field", "confidence": 0.95},
        {"selector_type": "xpath", "value": "//android.widget.EditText[@content-desc='Username input field']", "confidence": 0.7}
      ],
      "is_required": true,
      "wait_strategy": "visible"
    },
    {
      "name": "password_input",
      "element_type": "input",
      "selectors": [
        {"selector_type": "accessibility_id", "value": "Password input field", "confidence": 0.95}
      ],
      "is_required": true
    },
    {
      "name": "login_button",
      "element_type": "button",
      "selectors": [
        {"selector_type": "accessibility_id", "value": "Login button", "confidence": 0.95}
      ],
      "is_required": true
    }
  ]
}
```

`testcases.csv`:
```csv
test_id,test_name,module,priority,preconditions,steps,expected_result,test_data,tags,page_name
TC_LOGIN_001,Valid Login,saucedemo_android,P0,App on login screen,Tap username field|Enter username|Tap password field|Enter password|Tap login button,User logged in|Products screen displayed,username=bob@example.com|password=10203040,"login,smoke,positive",LoginScreen
TC_LOGIN_002,Invalid Password,saucedemo_android,P1,App on login screen,Enter valid username|Enter invalid password|Tap login,Error message displayed,username=bob@example.com|password=wrongpass,"login,negative",LoginScreen
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/models/schemas.py` | Add PlatformType, AndroidConfig, mobile selectors |
| `src/models/state.py` | Add platform_type field |
| `src/nodes/generation.py` | Refactor to use template factory |
| `src/nodes/planning.py` | Platform-aware prompts |
| `src/nodes/recovery.py` | Platform-aware recovery |
| `src/nodes/onboarding.py` | Android config validation |
| `src/nodes/verification/verification_node.py` | Platform-aware execution |
| `src/parsers/module_parser.py` | Android validation |
| `requirements.txt` | Add Appium dependency |

## New Files to Create

| File | Purpose |
|------|---------|
| `src/templates/__init__.py` | Module exports |
| `src/templates/base_templates.py` | Abstract template interface |
| `src/templates/web_templates.py` | Selenium templates (extracted) |
| `src/templates/android_templates.py` | Appium templates |
| `src/templates/template_factory.py` | Factory function |
| `inputs/android_example/` | Sample Android inputs |

---

## Implementation Order

1. Schema updates (Phase 1) - foundation
2. Templates module (Phase 2) - core abstraction
3. Onboarding validation (Phase 6) - validate early
4. Planning node (Phase 5) - planning awareness
5. Generation node (Phase 3) - main generation
6. Recovery node (Phase 4) - error handling
7. Verification node (Phase 7) - test execution
8. Dependencies & samples (Phase 8-9) - finalization

---

## Verification Plan

### 1. Backward Compatibility (Web)
```bash
# Existing web tests must still work
python -m src.agent --inputs inputs/saucedemo --output output/saucedemo --auto
cd output/saucedemo && pytest tests/ -v
```

### 2. Android Full Execution (Requires Infrastructure)
```bash
# Prerequisites (must be running BEFORE agent):
# 1. Install Appium: npm install -g appium
# 2. Install driver: appium driver install uiautomator2
# 3. Download APK: https://github.com/saucelabs/my-demo-app-rn/releases
# 4. Start emulator: emulator -avd Pixel_4_API_30
# 5. Start Appium: appium &

# Run agent with Android inputs
python -m src.agent \
  --inputs inputs/saucedemo_android \
  --output output/saucedemo_android \
  --auto
```

**Verify generated files:**
- `pages/base_page.py` has Appium imports (`from appium.webdriver.common.appiumby import AppiumBy`)
- `pages/base_page.py` has mobile methods (`tap`, `swipe_up`, `hide_keyboard`)
- `tests/conftest.py` has `UiAutomator2Options` and `webdriver.Remote()`
- Page objects use `AppiumBy.ACCESSIBILITY_ID`, `AppiumBy.ID`
- Tests call `hide_keyboard()` after text entry

### 3. Fail-Fast Behavior (Missing Infrastructure)
Test that verification fails with clear error when infrastructure unavailable:
```bash
# Without Appium running, should see:
#   ERROR: Android infrastructure check FAILED:
#     ✗ Appium server not running at http://localhost:4723. Start with: appium
#     ✗ No Android device/emulator connected. Start emulator or connect device.
python -m src.agent --inputs inputs/saucedemo_android --output output/saucedemo_android --auto
```
Agent should exit with failure status and clear setup instructions.

### 4. Manual Test Execution
```bash
# After agent completes successfully, run tests directly:
cd output/saucedemo_android
pytest tests/ -v

# Or with custom server URL
APPIUM_SERVER=http://localhost:4723 pytest tests/ -v
```

### 5. Unit Tests
Add tests to `tests/` directory:
- `test_templates.py`: Template factory returns correct class for platform
- `test_schemas.py`: AndroidConfig validation works
- `test_verification.py`: Preflight checks return expected error messages
