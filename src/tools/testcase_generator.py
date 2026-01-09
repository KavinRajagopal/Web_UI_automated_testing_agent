"""Test Case Generator - LLM-powered generation of test cases from UI elements.

This tool uses Claude to generate comprehensive manual test cases
based on discovered UI elements and optional page screenshots.

Supports multi-modal prompts (text + images) for better context.
"""

import base64
import json
import logging
from typing import Dict, List, Optional

from ..llm.bedrock_client import BedrockClient
from ..models.schemas import (
    PageMetadata,
    TestCaseRow,
    UIElement
)

logger = logging.getLogger(__name__)


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

SYSTEM_PROMPT = """You are an expert QA engineer specializing in test automation. 
Your task is to generate comprehensive manual test cases for web application testing.

GUIDELINES:
1. Generate test cases that are clear, actionable, and automatable
2. Include positive, negative, and edge cases
3. Use the exact element names provided in the metadata
4. Steps should be pipe-delimited (|) for parsing
5. Expected results should be pipe-delimited (|) for parsing
6. Test data should be in format: key=value|key2=value2
7. Assign appropriate priority (P0=critical, P1=high, P2=medium)
8. Use consistent naming: TC_{MODULE}_{SEQUENCE}

OUTPUT FORMAT:
Return a JSON array of test case objects with this exact structure:
[
  {
    "test_id": "TC_LOGIN_001",
    "test_name": "Valid login with correct credentials",
    "module": "login",
    "priority": "P0",
    "preconditions": "User has valid account",
    "steps": "Navigate to login page|Enter valid username|Enter valid password|Click login button",
    "expected_result": "User is redirected to products page|Welcome message displayed",
    "test_data": "username=standard_user|password=secret_sauce",
    "tags": "smoke,login,positive",
    "page_name": "LoginPage"
  }
]"""


def _format_elements_for_prompt(page: PageMetadata) -> str:
    """
    Format page elements into a readable string for the LLM prompt.
    
    Args:
        page: PageMetadata object
        
    Returns:
        Formatted string describing the page and its elements
    """
    lines = [
        f"## {page.page_name}",
        f"URL: {page.page_url or 'N/A'}",
        f"Description: {page.description or 'N/A'}",
        "",
        "### Elements:",
    ]
    
    for elem in page.elements:
        # Get best selector info
        best_selector = elem.get_best_selector()
        selector_info = ""
        if best_selector:
            selector_info = f" [{best_selector.selector_type.value}='{best_selector.value}']"
        
        lines.append(
            f"- **{elem.name}** ({elem.element_type}){selector_info}"
            f"\n  Description: {elem.description or 'N/A'}"
        )
    
    return "\n".join(lines)


def _build_generation_prompt(
    pages: List[PageMetadata],
    module_name: str,
    coverage_hints: Optional[List[str]] = None,
    max_tests_per_page: int = 10
) -> str:
    """
    Build the prompt for test case generation.
    
    Args:
        pages: List of PageMetadata objects
        module_name: Name of the module (e.g., "login", "cart")
        coverage_hints: Optional list of specific scenarios to cover
        max_tests_per_page: Maximum tests to generate per page
        
    Returns:
        Formatted prompt string
    """
    # Format all pages
    pages_text = "\n\n".join(_format_elements_for_prompt(p) for p in pages)
    
    # Build coverage section
    coverage_section = ""
    if coverage_hints:
        coverage_section = "\n\nSPECIFIC SCENARIOS TO COVER:\n" + "\n".join(f"- {h}" for h in coverage_hints)
    
    prompt = f"""Generate comprehensive test cases for the "{module_name}" module.

# PAGES AND ELEMENTS

{pages_text}

{coverage_section}

# REQUIREMENTS

1. Generate {max_tests_per_page * len(pages)} test cases total (roughly {max_tests_per_page} per page)
2. Include test types:
   - Positive tests (happy path)
   - Negative tests (invalid inputs, error handling)
   - Boundary tests (min/max values, empty inputs)
   - Edge cases (special characters, long inputs)
3. For each test, specify:
   - Clear, descriptive test name
   - All preconditions needed
   - Step-by-step actions (use element names exactly)
   - Expected results for each step
   - Test data with realistic values
4. Prioritize tests appropriately:
   - P0: Core functionality that must work
   - P1: Important features
   - P2: Nice-to-have coverage

Return ONLY the JSON array, no additional text."""
    
    return prompt


class TestCaseGenerator:
    """
    LLM-powered test case generator.
    
    Uses Claude via Bedrock to generate comprehensive test cases
    from UI element metadata and optional page screenshots.
    
    Usage:
        generator = TestCaseGenerator(bedrock_client)
        test_cases = generator.generate(pages, "authentication")
    """
    
    def __init__(
        self,
        llm_client: BedrockClient,
        max_tests_per_page: int = 10
    ):
        """
        Initialize the Test Case Generator.
        
        Args:
            llm_client: BedrockClient instance for LLM calls
            max_tests_per_page: Default max tests to generate per page
        """
        self.llm = llm_client
        self.max_tests_per_page = max_tests_per_page
    
    def generate(
        self,
        pages: List[PageMetadata],
        module_name: str,
        coverage_hints: Optional[List[str]] = None,
        screenshots: Optional[Dict[str, bytes]] = None,
        max_tests_per_page: Optional[int] = None
    ) -> List[TestCaseRow]:
        """
        Generate test cases for the given pages.
        
        Args:
            pages: List of PageMetadata objects with element info
            module_name: Name of the module being tested
            coverage_hints: Optional specific scenarios to cover
            screenshots: Optional dict of page_name -> PNG bytes
            max_tests_per_page: Override default max tests per page
            
        Returns:
            List of TestCaseRow objects
        """
        if not pages:
            logger.warning("No pages provided for test case generation")
            return []
        
        max_tests = max_tests_per_page or self.max_tests_per_page
        
        # Build the prompt
        prompt = _build_generation_prompt(
            pages=pages,
            module_name=module_name,
            coverage_hints=coverage_hints,
            max_tests_per_page=max_tests
        )
        
        # Build messages with optional screenshots
        messages = self._build_messages(prompt, screenshots)
        
        logger.info(f"Generating test cases for module '{module_name}' with {len(pages)} pages")
        
        try:
            # Call LLM
            response = self.llm.converse(
                messages=messages,
                system=SYSTEM_PROMPT,
                max_tokens=8192,  # Need more tokens for test case output
                temperature=0.3   # Lower temperature for more consistent output
            )
            
            # Extract response text
            response_text = self.llm.extract_text(response)
            
            # Parse JSON response
            test_cases = self._parse_response(response_text, module_name)
            
            logger.info(f"Generated {len(test_cases)} test cases")
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Test case generation failed: {e}")
            raise
    
    def _build_messages(
        self,
        prompt: str,
        screenshots: Optional[Dict[str, bytes]] = None
    ) -> List[Dict]:
        """
        Build Converse API messages, optionally with images.
        
        Args:
            prompt: Text prompt
            screenshots: Optional dict of page_name -> PNG bytes
            
        Returns:
            Messages list for Converse API
        """
        content = []
        
        # Add screenshots if provided
        if screenshots:
            for page_name, image_bytes in screenshots.items():
                # Convert to base64
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                
                content.append({
                    "text": f"Screenshot of {page_name}:"
                })
                content.append({
                    "image": {
                        "format": "png",
                        "source": {
                            "bytes": image_b64
                        }
                    }
                })
        
        # Add text prompt
        content.append({"text": prompt})
        
        return [{
            "role": "user",
            "content": content
        }]
    
    def _parse_response(self, response_text: str, module_name: str) -> List[TestCaseRow]:
        """
        Parse LLM response into TestCaseRow objects.
        
        Args:
            response_text: Raw response from LLM
            module_name: Module name for fallback
            
        Returns:
            List of TestCaseRow objects
        """
        # Clean up response - extract JSON
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        text = text.strip()
        
        # Parse JSON
        try:
            test_cases_data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {text[:500]}...")
            raise ValueError(f"LLM response was not valid JSON: {e}")
        
        # Convert to TestCaseRow objects
        test_cases = []
        
        for idx, tc_data in enumerate(test_cases_data):
            try:
                # Ensure required fields
                tc_data.setdefault("test_id", f"TC_{module_name.upper()}_{idx + 1:03d}")
                tc_data.setdefault("test_name", f"Test case {idx + 1}")
                tc_data.setdefault("module", module_name)
                tc_data.setdefault("priority", "P1")
                tc_data.setdefault("steps", "No steps defined")
                tc_data.setdefault("expected_result", "No expected result defined")
                
                # Create TestCaseRow
                test_case = TestCaseRow(**tc_data)
                test_cases.append(test_case)
                
            except Exception as e:
                logger.warning(f"Failed to parse test case {idx}: {e}")
                continue
        
        return test_cases
    
    def generate_for_saucedemo(
        self,
        pages: List[PageMetadata],
        screenshots: Optional[Dict[str, bytes]] = None
    ) -> List[TestCaseRow]:
        """
        Generate test cases specifically for SauceDemo.
        
        Pre-configured with coverage hints for e-commerce testing.
        
        Args:
            pages: List of PageMetadata for SauceDemo pages
            screenshots: Optional screenshots dict
            
        Returns:
            List of TestCaseRow objects
        """
        coverage_hints = [
            # Login
            "Valid login with standard_user credentials",
            "Invalid login with wrong password",
            "Invalid login with wrong username",
            "Login with locked_out_user (should fail)",
            "Login with empty username",
            "Login with empty password",
            
            # Products
            "View products list after login",
            "Sort products by name A-Z",
            "Sort products by name Z-A",
            "Sort products by price low to high",
            "Sort products by price high to low",
            "Add single product to cart",
            "Add multiple products to cart",
            
            # Cart
            "View cart with items",
            "Remove item from cart",
            "Continue shopping from cart",
            "Proceed to checkout from cart",
            
            # Checkout
            "Complete checkout with valid info",
            "Checkout with missing first name",
            "Checkout with missing last name", 
            "Checkout with missing postal code",
        ]
        
        return self.generate(
            pages=pages,
            module_name="saucedemo",
            coverage_hints=coverage_hints,
            screenshots=screenshots,
            max_tests_per_page=8
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_testcases_from_pages(
    pages: List[PageMetadata],
    module_name: str,
    llm_client: BedrockClient,
    screenshots: Optional[Dict[str, bytes]] = None
) -> List[TestCaseRow]:
    """
    Convenience function to generate test cases from pages.
    
    Args:
        pages: List of PageMetadata objects
        module_name: Module name
        llm_client: BedrockClient instance
        screenshots: Optional screenshots
        
    Returns:
        List of TestCaseRow objects
    """
    generator = TestCaseGenerator(llm_client)
    return generator.generate(pages, module_name, screenshots=screenshots)


def export_testcases_to_csv(
    test_cases: List[TestCaseRow],
    output_path: str
) -> str:
    """
    Export test cases to CSV file.
    
    Args:
        test_cases: List of TestCaseRow objects
        output_path: Path to output CSV file
        
    Returns:
        Path to created file
    """
    import csv
    
    fieldnames = [
        "test_id", "test_name", "module", "priority",
        "preconditions", "steps", "expected_result",
        "test_data", "tags", "page_name"
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for tc in test_cases:
            writer.writerow({
                "test_id": tc.test_id,
                "test_name": tc.test_name,
                "module": tc.module,
                "priority": tc.priority,
                "preconditions": tc.preconditions or "",
                "steps": tc.steps,
                "expected_result": tc.expected_result,
                "test_data": tc.test_data or "",
                "tags": tc.tags or "",
                "page_name": tc.page_name or ""
            })
    
    logger.info(f"Exported {len(test_cases)} test cases to {output_path}")
    return output_path


def export_pages_to_json(
    pages: List[PageMetadata],
    output_dir: str
) -> List[str]:
    """
    Export page metadata to JSON files.
    
    Args:
        pages: List of PageMetadata objects
        output_dir: Directory to write files to
        
    Returns:
        List of created file paths
    """
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    created_files = []
    
    for page in pages:
        # Generate filename from page name
        filename = page.page_name.lower().replace(" ", "_") + ".json"
        filepath = os.path.join(output_dir, filename)
        
        # Convert to dict (handle datetime serialization)
        page_dict = page.model_dump(mode='json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(page_dict, f, indent=2, default=str)
        
        created_files.append(filepath)
        logger.info(f"Exported {page.page_name} to {filepath}")
    
    return created_files
