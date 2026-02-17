"""Onboarding Node - Validates and loads input files.

This node:
1. Checks if required input files exist
2. Loads and validates module_spec.json
3. Loads and validates testcases.csv (or generates if missing)
4. Loads and validates element_metadata/*.json (or generates if missing)
5. Sets flags for human review if inputs were auto-generated
6. For Android: Checks prerequisites (Appium, adb, device)

Supports multiple platforms:
- Web (Selenium)
- Android (Appium)
"""

import logging
import os
import subprocess
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Tuple

from ..models.state import AgentState
from ..models.schemas import ModuleSpec, TestCaseRow, PageMetadata
from ..parsers.module_parser import ModuleParser
from ..parsers.csv_parser import CSVParser
from ..parsers.element_parser import ElementParser

logger = logging.getLogger(__name__)


class OnboardingError(Exception):
    """Raised when onboarding fails."""
    pass


def _find_adb_path() -> Optional[str]:
    """
    Find the adb executable path, checking common locations.

    Returns:
        Path to adb if found, None otherwise
    """
    # Check if adb is in PATH
    try:
        result = subprocess.run(
            ["which", "adb"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Check common locations on macOS/Linux
    common_paths = [
        os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),  # macOS default
        os.path.expanduser("~/Android/Sdk/platform-tools/adb"),  # Linux default
        "/usr/local/bin/adb",
        "/opt/android-sdk/platform-tools/adb",
    ]

    # Also check ANDROID_HOME and ANDROID_SDK_ROOT
    for env_var in ["ANDROID_HOME", "ANDROID_SDK_ROOT"]:
        sdk_path = os.environ.get(env_var)
        if sdk_path:
            common_paths.insert(0, os.path.join(sdk_path, "platform-tools", "adb"))

    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return None


def _check_android_prerequisites(android_config: Dict[str, Any], inputs_path: str = "") -> Tuple[bool, List[str]]:
    """
    Check Android prerequisites during onboarding. Fail early if not ready.

    Checks:
    1. Appium server running at http://localhost:4723 (or APPIUM_SERVER env)
    2. Android SDK installed (adb command available)
    3. Device/emulator connected (adb devices shows device)
    4. APK exists (if app_path specified in config)

    Args:
        android_config: Android configuration dict from module_spec
        inputs_path: Path to inputs directory (for resolving relative APK paths)

    Returns:
        Tuple of (all_passed: bool, issues: List[str])
    """
    issues = []

    # Get Appium server URL from environment or default
    appium_url = os.getenv("APPIUM_SERVER", "http://localhost:4723")

    # Check 1: Appium server running
    try:
        req = urllib.request.urlopen(f"{appium_url}/status", timeout=5)
        if req.status != 200:
            issues.append(f"❌ Appium server not responding properly at {appium_url}")
    except urllib.error.URLError:
        issues.append(f"❌ Appium server not running at {appium_url}. Start with: appium")
    except Exception as e:
        issues.append(f"❌ Could not connect to Appium server: {e}")

    # Find adb path (check common locations)
    adb_path = _find_adb_path()

    # Check 2: Android SDK (adb) available
    if adb_path:
        try:
            result = subprocess.run(
                [adb_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                issues.append("❌ adb command failed. Check Android SDK installation.")
            else:
                logger.info(f"  ✓ adb found at: {adb_path}")
        except subprocess.TimeoutExpired:
            issues.append("❌ adb command timed out.")
        except Exception as e:
            issues.append(f"❌ Failed to check adb: {e}")
    else:
        issues.append(
            "❌ Android SDK not found. Install Android Studio and ensure adb is available.\n"
            "     Add to ~/.zshrc: export ANDROID_HOME=$HOME/Library/Android/sdk\n"
            "                      export PATH=$PATH:$ANDROID_HOME/platform-tools"
        )

    # Check 3: Device/emulator connected (only if adb found)
    if adb_path:
        try:
            result = subprocess.run(
                [adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse output to find connected devices
                lines = result.stdout.strip().split('\n')
                # Skip header line "List of devices attached"
                devices = [
                    line for line in lines[1:]
                    if line.strip() and '\tdevice' in line
                ]
                if not devices:
                    issues.append(
                        "❌ No Android device/emulator connected. "
                        "Start emulator with: emulator -avd <your_avd_name>"
                    )
            else:
                issues.append("❌ adb devices command failed.")
        except Exception as e:
            issues.append(f"❌ Failed to check connected devices: {e}")

    # Check 4: APK exists (if app_path specified)
    app_path = android_config.get("app_path")
    if app_path:
        # First try as-is (absolute or relative to cwd)
        apk_found = False
        resolved_path = app_path

        if os.path.exists(app_path):
            apk_found = True
            resolved_path = app_path
        elif not os.path.isabs(app_path) and inputs_path:
            # Try relative to inputs directory
            relative_path = os.path.join(inputs_path, app_path)
            if os.path.exists(relative_path):
                apk_found = True
                resolved_path = relative_path

        if apk_found:
            logger.info(f"  ✓ APK found: {resolved_path}")
            # Update the config with resolved path for later use
            android_config["_resolved_app_path"] = resolved_path
        else:
            issues.append(f"❌ APK not found at: {app_path}")

    all_passed = len(issues) == 0
    return all_passed, issues


def _validate_android_config(module_spec: ModuleSpec) -> List[str]:
    """
    Validate Android configuration in module_spec.

    Args:
        module_spec: Loaded module specification

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not module_spec.android_config:
        errors.append("android_config is required when platform_type='android'")
        return errors

    config = module_spec.android_config

    # Required fields
    if not config.app_package:
        errors.append("android_config.app_package is required")

    if not config.app_activity:
        errors.append("android_config.app_activity is required")

    return errors


def _check_inputs_exist(inputs_path: str) -> Dict[str, bool]:
    """
    Check which input files exist.
    
    Args:
        inputs_path: Path to inputs directory
        
    Returns:
        Dict with existence status for each input type
    """
    status = {
        "module_spec": False,
        "testcases": False,
        "element_metadata": False,
        "element_files": []
    }
    
    # Check module_spec.json
    module_spec_path = os.path.join(inputs_path, "module_spec.json")
    status["module_spec"] = os.path.exists(module_spec_path)
    
    # Check testcases.csv
    testcases_path = os.path.join(inputs_path, "testcases.csv")
    status["testcases"] = os.path.exists(testcases_path)
    
    # Check element_metadata directory
    element_dir = os.path.join(inputs_path, "element_metadata")
    if os.path.isdir(element_dir):
        json_files = [f for f in os.listdir(element_dir) if f.endswith('.json')]
        status["element_metadata"] = len(json_files) > 0
        status["element_files"] = json_files
    
    return status


def _load_module_spec(inputs_path: str) -> Tuple[ModuleSpec, List[str], List[str]]:
    """
    Load and validate module_spec.json.

    Args:
        inputs_path: Path to inputs directory

    Returns:
        Tuple of (ModuleSpec, list of errors, list of warnings)
    """
    errors = []
    warnings = []
    parser = ModuleParser()

    module_spec_path = os.path.join(inputs_path, "module_spec.json")
    module_spec = parser.parse(module_spec_path)

    # Get platform type
    platform_type = getattr(module_spec, 'platform_type', 'web')
    if hasattr(platform_type, 'value'):
        platform_type = platform_type.value

    # Validation warnings (common)
    if not module_spec.pages:
        warnings.append("No pages defined in module_spec.json")

    # Platform-specific validation
    if platform_type == "android":
        # Validate Android config
        android_errors = _validate_android_config(module_spec)
        errors.extend(android_errors)

        # Warn about CSS selectors
        selector_priority = getattr(module_spec, 'selector_priority', [])
        if 'css' in selector_priority:
            warnings.append("CSS selectors are not supported on Android. Use accessibility_id, id, or xpath.")

    else:
        # Web validation
        if not module_spec.app_url:
            warnings.append("No app_url defined in module_spec.json")

    return module_spec, errors, warnings


def _load_test_cases(inputs_path: str) -> Tuple[List[TestCaseRow], List[str]]:
    """
    Load and validate testcases.csv.
    
    Args:
        inputs_path: Path to inputs directory
        
    Returns:
        Tuple of (list of TestCaseRow, list of warnings)
    """
    warnings = []
    parser = CSVParser()
    
    testcases_path = os.path.join(inputs_path, "testcases.csv")
    test_cases = parser.parse(testcases_path)
    
    # Validation warnings
    if not test_cases:
        warnings.append("No test cases found in testcases.csv")
    
    # Check for missing pages
    pages_used = set(tc.page_name for tc in test_cases if tc.page_name)
    logger.info(f"Test cases reference pages: {pages_used}")
    
    return test_cases, warnings


def _load_element_metadata(inputs_path: str) -> Tuple[Dict[str, PageMetadata], List[str]]:
    """
    Load and validate element_metadata/*.json files.
    
    Args:
        inputs_path: Path to inputs directory
        
    Returns:
        Tuple of (dict of page_name -> PageMetadata, list of warnings)
    """
    warnings = []
    parser = ElementParser()
    
    element_dir = os.path.join(inputs_path, "element_metadata")
    
    if not os.path.isdir(element_dir):
        return {}, ["element_metadata directory not found"]
    
    page_metadata = parser.parse_directory(element_dir)
    
    # Validation
    if not page_metadata:
        warnings.append("No element metadata files found")
    
    # Check for unstable selectors
    for page_name, page in page_metadata.items():
        unstable = parser.find_unstable_selectors(page)
        if unstable:
            for selector_info in unstable:
                warnings.append(
                    f"Unstable selector in {page_name}: {selector_info['element']} "
                    f"uses {selector_info['selector_type']}"
                )
    
    return page_metadata, warnings


def onboarding_node(state: AgentState) -> AgentState:
    """
    Onboarding node - loads and validates all inputs.

    This is the first node in the agent pipeline.
    For Android projects, also checks prerequisites (Appium, adb, device).

    Args:
        state: Current agent state

    Returns:
        Updated state with loaded inputs
    """
    logger.info("=" * 60)
    logger.info("ONBOARDING NODE")
    logger.info("=" * 60)

    inputs_path = state.get("inputs_path", "")
    errors = []
    warnings = []

    # Track what was generated
    generated_elements = False
    generated_testcases = False

    # Update current node
    state["current_node"] = "onboarding"
    state["node_history"] = state.get("node_history", []) + ["onboarding"]

    # Step 1: Check what exists
    logger.info(f"Checking inputs at: {inputs_path}")
    input_status = _check_inputs_exist(inputs_path)

    logger.info(f"  module_spec.json: {'✓' if input_status['module_spec'] else '✗'}")
    logger.info(f"  testcases.csv: {'✓' if input_status['testcases'] else '✗'}")
    logger.info(f"  element_metadata/: {'✓' if input_status['element_metadata'] else '✗'}")

    # Step 2: Load module_spec.json (REQUIRED)
    if not input_status["module_spec"]:
        errors.append("module_spec.json is required but not found")
        state["input_validation_errors"] = errors
        state["errors"] = state.get("errors", []) + errors
        logger.error("ONBOARDING FAILED: module_spec.json required")
        return state

    try:
        module_spec, spec_errors, spec_warnings = _load_module_spec(inputs_path)
        errors.extend(spec_errors)
        warnings.extend(spec_warnings)
        state["module_spec"] = module_spec.model_dump()
        logger.info(f"Loaded module_spec: {module_spec.module_name}")
    except Exception as e:
        errors.append(f"Failed to load module_spec.json: {e}")
        state["input_validation_errors"] = errors
        logger.error(f"ONBOARDING FAILED: {e}")
        return state

    # Step 2.5: Get platform type and store in state
    platform_type = getattr(module_spec, 'platform_type', 'web')
    if hasattr(platform_type, 'value'):
        platform_type = platform_type.value
    state["platform_type"] = platform_type

    logger.info(f"  Platform: {platform_type}")

    # Step 2.6: Check Android prerequisites (FAIL EARLY)
    if platform_type == "android":
        logger.info("Platform: Android - Checking prerequisites...")

        # Check for android_config errors first
        if spec_errors:
            logger.error("=" * 60)
            logger.error("ANDROID CONFIGURATION ERRORS")
            logger.error("=" * 60)
            for err in spec_errors:
                logger.error(f"  {err}")
            logger.error("")
            logger.error("Please fix module_spec.json and try again.")
            logger.error("=" * 60)
            state["input_validation_errors"] = errors
            state["errors"] = state.get("errors", []) + errors
            raise OnboardingError("Android configuration invalid. See errors above.")

        # Check infrastructure prerequisites
        android_config = module_spec.android_config
        if android_config:
            config_dict = android_config.model_dump() if hasattr(android_config, 'model_dump') else android_config
            prereq_ok, prereq_issues = _check_android_prerequisites(config_dict, inputs_path)

            if not prereq_ok:
                logger.error("=" * 60)
                logger.error("ANDROID PREREQUISITES NOT MET")
                logger.error("=" * 60)
                for issue in prereq_issues:
                    logger.error(f"  {issue}")
                logger.error("")
                logger.error("Please fix the above issues before running the agent.")
                logger.error("=" * 60)
                errors.extend(prereq_issues)
                state["input_validation_errors"] = errors
                state["errors"] = state.get("errors", []) + errors
                raise OnboardingError("Android prerequisites not met. See errors above.")

            # Log success
            logger.info("  ✓ Appium server running")
            logger.info("  ✓ Android SDK (adb) available")
            logger.info("  ✓ Device/emulator connected")
            if config_dict.get("app_path"):
                logger.info(f"  ✓ APK configured: {config_dict.get('app_path')}")

    # Step 3: Load testcases.csv (or flag for generation)
    if input_status["testcases"]:
        try:
            test_cases, tc_warnings = _load_test_cases(inputs_path)
            warnings.extend(tc_warnings)
            state["test_cases"] = [tc.model_dump() for tc in test_cases]
            logger.info(f"Loaded {len(test_cases)} test cases")
        except Exception as e:
            warnings.append(f"Failed to load testcases.csv: {e}")
            state["test_cases"] = []
            generated_testcases = True
    else:
        logger.info("testcases.csv not found - will need generation")
        state["test_cases"] = []
        generated_testcases = True
    
    # Step 4: Load element_metadata (or flag for generation)
    if input_status["element_metadata"]:
        try:
            page_metadata, elem_warnings = _load_element_metadata(inputs_path)
            warnings.extend(elem_warnings)
            state["page_metadata"] = {
                name: page.model_dump() for name, page in page_metadata.items()
            }
            logger.info(f"Loaded element metadata for {len(page_metadata)} pages")
        except Exception as e:
            warnings.append(f"Failed to load element_metadata: {e}")
            state["page_metadata"] = {}
            generated_elements = True
    else:
        logger.info("element_metadata/ not found - will need generation")
        state["page_metadata"] = {}
        generated_elements = True
    
    # Step 5: Set generation flags
    state["generated_elements"] = generated_elements
    state["generated_testcases"] = generated_testcases
    state["inputs_generated"] = generated_elements or generated_testcases
    state["needs_input_review"] = generated_elements or generated_testcases
    
    # Step 6: Store validation results
    state["input_validation_errors"] = errors
    state["input_validation_warnings"] = warnings
    
    # Log summary (platform-aware)
    logger.info("-" * 40)
    logger.info("ONBOARDING SUMMARY")
    logger.info(f"  Module: {module_spec.module_name}")
    logger.info(f"  Platform: {platform_type}")

    if platform_type == "android":
        android_config = module_spec.android_config
        if android_config:
            logger.info(f"  App Package: {android_config.app_package}")
            logger.info(f"  App Activity: {android_config.app_activity}")
            logger.info(f"  Device: {android_config.device_name}")
    else:
        logger.info(f"  App URL: {module_spec.app_url}")

    logger.info(f"  Test cases: {len(state.get('test_cases', []))}")
    logger.info(f"  Pages: {len(state.get('page_metadata', {}))}")
    logger.info(f"  Errors: {len(errors)}")
    logger.info(f"  Warnings: {len(warnings)}")
    logger.info(f"  Needs input review: {state['needs_input_review']}")
    logger.info("-" * 40)

    if warnings:
        for w in warnings:
            logger.warning(f"  ⚠ {w}")

    return state
