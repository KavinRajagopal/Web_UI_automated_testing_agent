"""Test case analysis tool using LLM for intelligent analysis."""

import json
import logging
import re
from typing import List, Dict, Any
from ..models.schemas import (
    TestCaseRow, TestCaseAnalysis, DuplicateTestCase, 
    SuggestedTestCase, TestCasePriority, CoverageMetrics
)
from ..llm.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


class TestCaseAnalyzer:
    """Analyze test cases for duplicates, gaps, priorities, and coverage."""
    
    def __init__(self, llm: BedrockClient):
        self.llm = llm
    
    def analyze_test_cases(
        self,
        test_cases: List[TestCaseRow],
        module_spec: Dict[str, Any],
        page_metadata: Dict[str, Any]
    ) -> TestCaseAnalysis:
        """
        Comprehensive analysis of test cases.
        
        Args:
            test_cases: List of test cases to analyze
            module_spec: Module specification
            page_metadata: Page metadata dictionary
            
        Returns:
            TestCaseAnalysis with all analysis results
        """
        logger.info(f"Analyzing {len(test_cases)} test cases...")
        
        # Scenario 1: Duplicate detection
        duplicates = self._detect_duplicates(test_cases)
        
        # Scenario 2: Suggest missing test cases
        suggested_tests = self._suggest_missing_tests(
            test_cases, module_spec, page_metadata
        )
        
        # Scenario 3: Priority analysis
        priority_analysis = self._analyze_priorities(test_cases, module_spec)
        
        # Scenario 4: Coverage analysis
        coverage_by_module, coverage_by_page, overall_coverage = self._analyze_coverage(
            test_cases, module_spec, page_metadata
        )
        
        # Calculate efficient test count
        duplicate_ids = {d.duplicate_of for d in duplicates}
        efficient_count = len(test_cases) - len(duplicates) + len(duplicate_ids)
        recommended_count = efficient_count + len(suggested_tests)
        
        return TestCaseAnalysis(
            duplicates=duplicates,
            duplicate_count=len(duplicates),
            efficient_test_count=efficient_count,
            suggested_tests=suggested_tests,
            priority_analysis=priority_analysis,
            critical_tests=[tc.test_id for tc in priority_analysis if tc.is_critical],
            coverage_by_module=coverage_by_module,
            coverage_by_page=coverage_by_page,
            overall_coverage=overall_coverage,
            total_input_tests=len(test_cases),
            recommended_test_count=recommended_count
        )(
            duplicates=duplicates,
            duplicate_count=len(duplicates),
            efficient_test_count=efficient_count,
            suggested_tests=suggested_tests,
            priority_analysis=priority_analysis,
            critical_tests=[tc.test_id for tc in priority_analysis if tc.is_critical],
            coverage_by_module=coverage_by_module,
            coverage_by_page=coverage_by_page,
            overall_coverage=overall_coverage,
            total_input_tests=len(test_cases),
            recommended_test_count=recommended_count
        )
    
    def _detect_duplicates(self, test_cases: List[TestCaseRow]) -> List[DuplicateTestCase]:
        """Detect duplicate or inefficient test cases."""
        logger.info("Detecting duplicate test cases...")
        
        # First, do a simple similarity check based on steps and expected results
        # This catches obvious duplicates before LLM call
        duplicates_found = []
        seen_combinations = {}  # (steps_hash, expected_hash) -> test_id
        
        for tc in test_cases:
            # Create a normalized hash of steps and expected results
            steps_normalized = "|".join(sorted(tc.steps.split("|") if tc.steps else []))
            expected_normalized = "|".join(sorted(tc.expected_result.split("|") if tc.expected_result else []))
            combo_key = (steps_normalized, expected_normalized)
            
            if combo_key in seen_combinations:
                # Found a duplicate!
                original_id = seen_combinations[combo_key]
                duplicates_found.append({
                    "test_id": tc.test_id,
                    "test_name": tc.test_name,
                    "duplicate_of": original_id,
                    "similarity_score": 1.0,  # Exact match
                    "reason": "Exact same steps and expected results",
                    "recommendation": "remove"
                })
                logger.debug(f"Found exact duplicate: {tc.test_id} duplicates {original_id}")
            else:
                seen_combinations[combo_key] = tc.test_id
        
        # Also check for high similarity (same steps, similar expected results)
        # Compare each test with others
        for i, tc1 in enumerate(test_cases):
            for tc2 in test_cases[i+1:]:
                # Skip if already marked as duplicate
                if any(d["test_id"] == tc1.test_id or d["test_id"] == tc2.test_id for d in duplicates_found):
                    continue
                
                # Check if steps are very similar (90%+ match)
                steps1 = set(tc1.steps.split("|") if tc1.steps else [])
                steps2 = set(tc2.steps.split("|") if tc2.steps else [])
                
                if len(steps1) > 0 and len(steps2) > 0:
                    similarity = len(steps1 & steps2) / max(len(steps1), len(steps2))
                    if similarity >= 0.9:  # 90%+ similarity
                        # Check if expected results are also similar
                        exp1 = set(tc1.expected_result.split("|") if tc1.expected_result else [])
                        exp2 = set(tc2.expected_result.split("|") if tc2.expected_result else [])
                        exp_similarity = len(exp1 & exp2) / max(len(exp1), len(exp2)) if max(len(exp1), len(exp2)) > 0 else 0
                        
                        if exp_similarity >= 0.8:  # 80%+ expected result similarity
                            # Use the earlier test_id as the original
                            original_id = tc1.test_id if tc1.test_id < tc2.test_id else tc2.test_id
                            duplicate_id = tc2.test_id if original_id == tc1.test_id else tc1.test_id
                            
                            duplicates_found.append({
                                "test_id": duplicate_id,
                                "test_name": tc2.test_name if duplicate_id == tc2.test_id else tc1.test_name,
                                "duplicate_of": original_id,
                                "similarity_score": (similarity + exp_similarity) / 2,
                                "reason": f"Very similar steps ({similarity:.0%}) and expected results ({exp_similarity:.0%})",
                                "recommendation": "merge"
                            })
                            logger.debug(f"Found similar duplicate: {duplicate_id} similar to {original_id} ({similarity:.0%})")
        
        # If we found duplicates via simple check, return them (but still call LLM for additional insights)
        if duplicates_found:
            logger.info(f"Found {len(duplicates_found)} duplicates via similarity check")
            test_lookup = {tc.test_id: tc.test_name for tc in test_cases}
            for dup in duplicates_found:
                if "test_name" not in dup or not dup["test_name"]:
                    dup["test_name"] = test_lookup.get(dup.get("test_id"), "Unknown")
            
            try:
                simple_duplicates = [DuplicateTestCase(**d) for d in duplicates_found]
                # Still call LLM to find additional nuanced duplicates
                logger.info("Calling LLM for additional duplicate detection...")
            except Exception as e:
                logger.warning(f"Failed to create DuplicateTestCase objects: {e}")
                simple_duplicates = []
        else:
            simple_duplicates = []
        
        # If no obvious duplicates, use LLM for more nuanced detection
        # Prepare test case summaries for LLM
        test_summaries = []
        for tc in test_cases:
            test_summaries.append({
                "test_id": tc.test_id,
                "test_name": tc.test_name,
                "module": tc.module,
                "steps": tc.steps,
                "expected_result": tc.expected_result,
                "priority": tc.priority,
                "page_name": tc.page_name
            })
        
        prompt = f"""Analyze the following test cases and identify duplicates or inefficient tests.

IMPORTANT: Only identify tests that are TRUE duplicates - same functionality, same steps, same expected results.
Do NOT mark tests as duplicates if they test different scenarios, even if they use similar steps.

A test case is considered a duplicate if:
1. It tests the EXACT same functionality with the EXACT same steps
2. It has only minor variations in test data but tests the same scenario
3. Multiple tests can be combined into one parameterized test

Test Cases:
{self._format_test_cases_for_llm(test_summaries)}

For each duplicate found, provide:
- test_id: The duplicate test ID
- test_name: The test name (REQUIRED)
- duplicate_of: The original test ID it duplicates
- similarity_score: 0.0-1.0 (1.0 = exact duplicate)
- reason: Why it's a duplicate
- recommendation: "merge", "remove", or "keep_separate"

Return JSON array of duplicates:
[
  {{
    "test_id": "TC_LOGIN_002",
    "test_name": "Invalid login with wrong password",
    "duplicate_of": "TC_LOGIN_001",
    "similarity_score": 0.95,
    "reason": "Same login flow, only password differs",
    "recommendation": "merge"
  }}
]

If no duplicates found, return empty array [].
Return ONLY valid JSON, no markdown or explanation."""

        try:
            response = self.llm.chat(user_message=prompt, system="You are a test automation expert analyzing test cases for duplicates.")
            duplicates_data = self._parse_json_response(response)
            
            # Enrich duplicates with test_name if missing
            test_lookup = {tc.test_id: tc.test_name for tc in test_cases}
            for dup in duplicates_data:
                if "test_name" not in dup:
                    dup["test_name"] = test_lookup.get(dup.get("test_id"), "Unknown")
            
            llm_duplicates = [DuplicateTestCase(**d) for d in duplicates_data]
            
            # Merge simple duplicates with LLM duplicates (avoid duplicates)
            all_duplicate_ids = {d.test_id for d in simple_duplicates}
            for dup in llm_duplicates:
                if dup.test_id not in all_duplicate_ids:
                    simple_duplicates.append(dup)
                    all_duplicate_ids.add(dup.test_id)
            
            total_duplicates = len(simple_duplicates)
            logger.info(f"Found {total_duplicates} duplicate test cases ({len(simple_duplicates) - len(llm_duplicates)} from similarity, {len(llm_duplicates)} from LLM)")
            return simple_duplicates
        except Exception as e:
            logger.warning(f"Failed to detect duplicates with LLM: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Return simple duplicates if we found any
            if duplicates_found:
                return simple_duplicates
            return []
    
    def _suggest_missing_tests(
        self,
        test_cases: List[TestCaseRow],
        module_spec: Dict[str, Any],
        page_metadata: Dict[str, Any]
    ) -> List[SuggestedTestCase]:
        """Suggest missing test cases based on coverage gaps."""
        logger.info("Suggesting missing test cases...")
        
        # Prepare context
        pages = [p.get("name", "") for p in module_spec.get("pages", [])]
        existing_tests_by_page = {}
        for tc in test_cases:
            page = tc.page_name or "unknown"
            existing_tests_by_page.setdefault(page, []).append({
                "test_id": tc.test_id,
                "test_name": tc.test_name,
                "steps": tc.steps,
                "expected_result": tc.expected_result
            })
        
        prompt = f"""Analyze test coverage and suggest missing test cases.

Module: {module_spec.get('module_name')}
Pages: {', '.join(pages)}

Existing Test Cases by Page:
{self._format_tests_by_page(existing_tests_by_page)}

For each page, identify:
1. Critical user flows not covered
2. Edge cases missing
3. Error scenarios not tested
4. Integration points not covered

Suggest test cases that would improve coverage. For each suggestion:
- test_id: Suggested ID (e.g., TC_PAGE_XXX)
- test_name: Descriptive name
- module: Module name
- priority: P0 (critical), P1 (important), P2 (nice to have)
- steps: Pipe-delimited steps
- expected_result: Expected outcome
- reason: Why this test is needed
- coverage_gap: What gap it addresses

Return JSON array (limit to top 5 suggestions):
[
  {{
    "test_id": "TC_LOGIN_009",
    "test_name": "Login with expired session",
    "module": "{module_spec.get('module_name')}",
    "priority": "P1",
    "steps": "Navigate to app|Wait 30 minutes|Attempt action",
    "expected_result": "Session expired|Redirected to login",
    "reason": "Security and session management not covered",
    "coverage_gap": "Session expiration handling"
  }}
]

Return ONLY valid JSON array, no markdown."""

        try:
            response = self.llm.chat(user_message=prompt, system="You are a test automation expert suggesting missing test cases.")
            suggestions_data = self._parse_json_response(response)
            suggestions = [SuggestedTestCase(**s) for s in suggestions_data]
            logger.info(f"Suggested {len(suggestions)} additional test cases")
            return suggestions
        except Exception as e:
            logger.warning(f"Failed to suggest missing tests: {e}")
            return []
    
    def _analyze_priorities(
        self,
        test_cases: List[TestCaseRow],
        module_spec: Dict[str, Any]
    ) -> List[TestCasePriority]:
        """Analyze and recommend priorities for test cases."""
        logger.info("Analyzing test case priorities...")
        
        test_summaries = []
        for tc in test_cases:
            test_summaries.append({
                "test_id": tc.test_id,
                "test_name": tc.test_name,
                "current_priority": tc.priority,
                "module": tc.module,
                "steps": tc.steps,
                "expected_result": tc.expected_result,
                "tags": tc.tags or ""
            })
        
        prompt = f"""Analyze test case priorities and recommend optimal prioritization.

Consider:
- P0: Critical path, smoke tests, security, data integrity
- P1: Important functionality, common user flows
- P2: Edge cases, nice-to-have, low-risk scenarios

Test Cases:
{self._format_test_cases_for_llm(test_summaries)}

For each test case, provide:
- test_id: Test ID
- test_name: Test name
- current_priority: Current priority
- recommended_priority: Recommended priority (P0, P1, or P2)
- priority_reason: Why this priority is recommended
- is_critical: true if this is a critical test (P0, smoke, security)

Return JSON array:
[
  {{
    "test_id": "TC_LOGIN_001",
    "test_name": "Valid login",
    "current_priority": "P0",
    "recommended_priority": "P0",
    "priority_reason": "Critical smoke test for authentication",
    "is_critical": true
  }}
]

Return ONLY valid JSON array."""

        try:
            response = self.llm.chat(user_message=prompt, system="You are a test automation expert analyzing test case priorities.")
            priorities_data = self._parse_json_response(response)
            priorities = [TestCasePriority(**p) for p in priorities_data]
            logger.info(f"Analyzed priorities for {len(priorities)} test cases")
            return priorities
        except Exception as e:
            logger.warning(f"Failed to analyze priorities: {e}")
            return []
    
    def _analyze_coverage(
        self,
        test_cases: List[TestCaseRow],
        module_spec: Dict[str, Any],
        page_metadata: Dict[str, Any]
    ) -> tuple[Dict[str, CoverageMetrics], Dict[str, CoverageMetrics], float]:
        """Analyze test coverage by module and page."""
        logger.info("Analyzing test coverage...")
        
        # Group tests by module and page
        tests_by_module = {}
        tests_by_page = {}
        
        for tc in test_cases:
            module = tc.module
            page = tc.page_name or "unknown"
            
            tests_by_module.setdefault(module, []).append(tc)
            tests_by_page.setdefault(page, []).append(tc)
        
        # Get all pages from module spec
        all_pages = [p.get("name", "") for p in module_spec.get("pages", [])]
        all_modules = set(tc.module for tc in test_cases)
        
        prompt = f"""Analyze test coverage for modules and pages.

Module: {module_spec.get('module_name')}
Pages: {', '.join(all_pages)}
Modules: {', '.join(all_modules)}

Test Cases by Module:
{self._format_coverage_context(tests_by_module)}

Test Cases by Page:
{self._format_coverage_context(tests_by_page)}

For each module and page, calculate:
1. coverage_percentage: 0-100 based on critical scenarios covered
2. covered_scenarios: List of scenarios that are tested
3. missing_scenarios: List of important scenarios not covered
4. recommendations: Suggestions to improve coverage

Return JSON:
{{
  "by_module": {{
    "module_name": {{
      "module_or_page": "module_name",
      "total_test_cases": 10,
      "coverage_percentage": 75.0,
      "covered_scenarios": ["login", "logout"],
      "missing_scenarios": ["password reset", "session timeout"],
      "recommendations": ["Add password reset test", "Add session timeout test"]
    }}
  }},
  "by_page": {{
    "LoginPage": {{
      "module_or_page": "LoginPage",
      "total_test_cases": 5,
      "coverage_percentage": 80.0,
      "covered_scenarios": ["valid login", "invalid login"],
      "missing_scenarios": ["password visibility toggle"],
      "recommendations": ["Add password visibility test"]
    }}
  }},
  "overall_coverage": 77.5
}}

Return ONLY valid JSON."""

        try:
            response = self.llm.chat(user_message=prompt, system="You are a test automation expert analyzing test coverage.")
            coverage_data = self._parse_json_response(response)
            
            coverage_by_module = {
                k: CoverageMetrics(**v) 
                for k, v in coverage_data.get("by_module", {}).items()
            }
            coverage_by_page = {
                k: CoverageMetrics(**v) 
                for k, v in coverage_data.get("by_page", {}).items()
            }
            overall_coverage = coverage_data.get("overall_coverage", 0.0)
            
            logger.info(f"Coverage analysis complete: {overall_coverage:.1f}% overall")
            return coverage_by_module, coverage_by_page, overall_coverage
        except Exception as e:
            logger.warning(f"Failed to analyze coverage: {e}")
            return {}, {}, 0.0
    
    def _format_test_cases_for_llm(self, test_cases: List[Dict]) -> str:
        """Format test cases for LLM prompt."""
        lines = []
        for tc in test_cases:
            lines.append(f"- {tc['test_id']}: {tc['test_name']}")
            lines.append(f"  Steps: {tc.get('steps', 'N/A')}")
            lines.append(f"  Expected: {tc.get('expected_result', 'N/A')}")
            lines.append(f"  Priority: {tc.get('priority', 'N/A')}")
        return "\n".join(lines)
    
    def _format_tests_by_page(self, tests_by_page: Dict[str, List]) -> str:
        """Format tests grouped by page."""
        lines = []
        for page, tests in tests_by_page.items():
            lines.append(f"\n{page}:")
            for test in tests:
                lines.append(f"  - {test['test_id']}: {test['test_name']}")
        return "\n".join(lines)
    
    def _format_coverage_context(self, tests_by_group: Dict[str, List[TestCaseRow]]) -> str:
        """Format test cases grouped by module/page for coverage analysis."""
        lines = []
        for group, tests in tests_by_group.items():
            lines.append(f"\n{group} ({len(tests)} tests):")
            for tc in tests:
                lines.append(f"  - {tc.test_id}: {tc.test_name}")
        return "\n".join(lines)
    
    def _parse_json_response(self, response: str) -> Any:
        """Parse JSON response from LLM."""
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON directly
            json_str = response.strip()
            if not (response.startswith('[') or response.startswith('{')):
                # Try to extract first JSON structure
                json_match = re.search(r'(\[.*?\]|\{.*?\})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
        
        return json.loads(json_str)
