#!/usr/bin/env python3
"""Tests for Element Discovery and Test Case Generator tools.

Run with: venv/bin/python -m pytest tests/test_tools.py -v
"""

import json
import os
import sys
import tempfile
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.schemas import (
    PageMetadata,
    UIElement,
    ElementSelector,
    SelectorType,
    TestCaseRow
)
from src.tools.element_discovery import ElementDiscoveryTool
from src.tools.testcase_generator import (
    TestCaseGenerator,
    _format_elements_for_prompt,
    _build_generation_prompt,
    export_testcases_to_csv,
    export_pages_to_json
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_page_metadata():
    """Create sample PageMetadata for testing."""
    return PageMetadata(
        page_name="LoginPage",
        page_url="https://www.saucedemo.com",
        description="SauceDemo login page",
        elements=[
            UIElement(
                name="username",
                description="Username input field",
                element_type="input",
                selectors=[
                    ElementSelector(
                        selector_type=SelectorType.DATA_TESTID,
                        value="username",
                        confidence=0.98,
                        is_stable=True
                    )
                ],
                is_required=True,
                wait_strategy="visible"
            ),
            UIElement(
                name="password",
                description="Password input field",
                element_type="input",
                selectors=[
                    ElementSelector(
                        selector_type=SelectorType.DATA_TESTID,
                        value="password",
                        confidence=0.98,
                        is_stable=True
                    )
                ],
                is_required=True,
                wait_strategy="visible"
            ),
            UIElement(
                name="login-button",
                description="Login button",
                element_type="button",
                selectors=[
                    ElementSelector(
                        selector_type=SelectorType.DATA_TESTID,
                        value="login-button",
                        confidence=0.98,
                        is_stable=True
                    )
                ],
                is_required=True,
                wait_strategy="clickable"
            ),
            UIElement(
                name="error",
                description="Error message container",
                element_type="element",
                selectors=[
                    ElementSelector(
                        selector_type=SelectorType.DATA_TESTID,
                        value="error",
                        confidence=0.98,
                        is_stable=True
                    )
                ],
                is_required=False,
                wait_strategy="visible"
            ),
        ]
    )


@pytest.fixture
def sample_test_cases():
    """Create sample test cases for testing."""
    return [
        TestCaseRow(
            test_id="TC_LOGIN_001",
            test_name="Valid login with correct credentials",
            module="login",
            priority="P0",
            preconditions="User has valid account",
            steps="Navigate to login page|Enter valid username|Enter valid password|Click login button",
            expected_result="User redirected to products page",
            test_data="username=standard_user|password=secret_sauce",
            tags="smoke,login",
            page_name="LoginPage"
        ),
        TestCaseRow(
            test_id="TC_LOGIN_002",
            test_name="Invalid login with wrong password",
            module="login",
            priority="P1",
            preconditions="User is on login page",
            steps="Enter valid username|Enter wrong password|Click login button",
            expected_result="Error message displayed",
            test_data="username=standard_user|password=wrong_pass",
            tags="negative,login",
            page_name="LoginPage"
        ),
    ]


@pytest.fixture
def mock_bedrock_client():
    """Create a mock BedrockClient."""
    client = Mock()
    client.converse = Mock()
    client.extract_text = Mock()
    client.get_usage_stats = Mock(return_value={
        "call_count": 1,
        "total_input_tokens": 1000,
        "total_output_tokens": 500,
        "total_tokens": 1500
    })
    return client


# =============================================================================
# ELEMENT DISCOVERY TOOL TESTS
# =============================================================================

class TestElementDiscoveryTool:
    """Tests for ElementDiscoveryTool."""
    
    def test_initialization_defaults(self):
        """Test default initialization."""
        tool = ElementDiscoveryTool()
        
        assert tool.headless is True
        assert tool.implicit_wait == 10
        assert tool.page_load_timeout == 30
        assert tool.driver is None
    
    def test_initialization_custom(self):
        """Test custom initialization."""
        tool = ElementDiscoveryTool(
            headless=False,
            implicit_wait=5,
            page_load_timeout=60
        )
        
        assert tool.headless is False
        assert tool.implicit_wait == 5
        assert tool.page_load_timeout == 60
    
    def test_element_type_detection(self):
        """Test _determine_element_type method."""
        tool = ElementDiscoveryTool()
        
        # Input types
        assert tool._determine_element_type({"tag": "input", "type": "text"}) == "input"
        assert tool._determine_element_type({"tag": "input", "type": "email"}) == "input"
        assert tool._determine_element_type({"tag": "input", "type": "password"}) == "input"
        assert tool._determine_element_type({"tag": "input", "type": "submit"}) == "button"
        assert tool._determine_element_type({"tag": "input", "type": "checkbox"}) == "checkbox"
        
        # Other elements
        assert tool._determine_element_type({"tag": "button"}) == "button"
        assert tool._determine_element_type({"tag": "a"}) == "link"
        assert tool._determine_element_type({"tag": "select"}) == "select"
        assert tool._determine_element_type({"tag": "textarea"}) == "textarea"
        
        # Role-based
        assert tool._determine_element_type({"tag": "div", "role": "button"}) == "button"
    
    def test_element_name_generation(self):
        """Test _generate_element_name method."""
        tool = ElementDiscoveryTool()
        
        # From data-test
        assert tool._generate_element_name({"data-test": "login-button"}, 0) == "login-button"
        
        # From id
        assert tool._generate_element_name({"id": "username"}, 0) == "username"
        
        # From name
        assert tool._generate_element_name({"name": "password"}, 0) == "password"
        
        # Fallback
        name = tool._generate_element_name({"tag": "button", "type": "submit"}, 5)
        assert "button" in name
    
    def test_selector_building(self):
        """Test _build_selectors method."""
        tool = ElementDiscoveryTool()
        
        attrs = {
            "id": "username",
            "data-test": "username-input",
            "name": "user",
            "aria-label": "Enter username"
        }
        
        selectors = tool._build_selectors(attrs)
        
        assert len(selectors) == 4
        # Should be sorted by confidence
        assert selectors[0].selector_type == SelectorType.DATA_TESTID
        assert selectors[0].confidence == 0.98
    
    def test_selector_stability_detection(self):
        """Test that dynamic IDs are marked as unstable."""
        tool = ElementDiscoveryTool()
        
        # Dynamic ID should be marked unstable
        attrs_dynamic = {"id": "input_12345678"}
        selectors = tool._build_selectors(attrs_dynamic)
        assert len(selectors) == 1
        assert selectors[0].is_stable is False
        
        # Normal ID should be stable
        attrs_normal = {"id": "username"}
        selectors = tool._build_selectors(attrs_normal)
        assert len(selectors) == 1
        assert selectors[0].is_stable is True
    
    def test_is_element_useful(self):
        """Test _is_element_useful method."""
        tool = ElementDiscoveryTool()
        
        # Useful - has stable selectors
        assert tool._is_element_useful({"id": "username"}) is True
        assert tool._is_element_useful({"data-test": "login"}) is True
        assert tool._is_element_useful({"name": "password"}) is True
        
        # Not useful - no stable selectors
        assert tool._is_element_useful({"tag": "div", "class": "some-class"}) is False
        assert tool._is_element_useful({}) is False


# =============================================================================
# TEST CASE GENERATOR TESTS
# =============================================================================

class TestTestCaseGenerator:
    """Tests for TestCaseGenerator."""
    
    def test_format_elements_for_prompt(self, sample_page_metadata):
        """Test element formatting for prompts."""
        formatted = _format_elements_for_prompt(sample_page_metadata)
        
        assert "LoginPage" in formatted
        assert "username" in formatted
        assert "password" in formatted
        assert "login-button" in formatted
        assert "data-testid" in formatted
    
    def test_build_generation_prompt(self, sample_page_metadata):
        """Test prompt building."""
        prompt = _build_generation_prompt(
            pages=[sample_page_metadata],
            module_name="login",
            coverage_hints=["Valid login", "Invalid login"],
            max_tests_per_page=5
        )
        
        assert "login" in prompt.lower()
        assert "LoginPage" in prompt
        assert "Valid login" in prompt
        assert "Invalid login" in prompt
        assert "5" in prompt  # max tests
    
    def test_generator_initialization(self, mock_bedrock_client):
        """Test generator initialization."""
        generator = TestCaseGenerator(mock_bedrock_client)
        
        assert generator.llm == mock_bedrock_client
        assert generator.max_tests_per_page == 10
    
    def test_generator_empty_pages(self, mock_bedrock_client):
        """Test generator with empty pages list."""
        generator = TestCaseGenerator(mock_bedrock_client)
        
        result = generator.generate([], "test_module")
        
        assert result == []
        mock_bedrock_client.converse.assert_not_called()
    
    def test_generator_parses_response(self, mock_bedrock_client, sample_page_metadata):
        """Test that generator correctly parses LLM response."""
        # Setup mock response
        mock_response = {
            "output": {
                "message": {
                    "content": [{"text": json.dumps([
                        {
                            "test_id": "TC_LOGIN_001",
                            "test_name": "Valid login",
                            "module": "login",
                            "priority": "P0",
                            "steps": "Navigate|Enter username|Enter password|Click login",
                            "expected_result": "User logged in",
                            "test_data": "username=test|password=test",
                            "tags": "smoke",
                            "page_name": "LoginPage"
                        }
                    ])}]
                }
            },
            "usage": {"inputTokens": 100, "outputTokens": 50}
        }
        mock_bedrock_client.converse.return_value = mock_response
        mock_bedrock_client.extract_text.return_value = json.dumps([
            {
                "test_id": "TC_LOGIN_001",
                "test_name": "Valid login",
                "module": "login",
                "priority": "P0",
                "steps": "Navigate|Enter username|Enter password|Click login",
                "expected_result": "User logged in",
                "test_data": "username=test|password=test",
                "tags": "smoke",
                "page_name": "LoginPage"
            }
        ])
        
        generator = TestCaseGenerator(mock_bedrock_client)
        result = generator.generate([sample_page_metadata], "login")
        
        assert len(result) == 1
        assert result[0].test_id == "TC_LOGIN_001"
        assert result[0].module == "login"
    
    def test_build_messages_with_screenshots(self, mock_bedrock_client):
        """Test message building with screenshots."""
        generator = TestCaseGenerator(mock_bedrock_client)
        
        screenshots = {"LoginPage": b"fake_png_data"}
        messages = generator._build_messages("Test prompt", screenshots)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        # Should have screenshot + text
        assert len(messages[0]["content"]) == 3  # text intro + image + prompt
    
    def test_build_messages_without_screenshots(self, mock_bedrock_client):
        """Test message building without screenshots."""
        generator = TestCaseGenerator(mock_bedrock_client)
        
        messages = generator._build_messages("Test prompt", None)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert len(messages[0]["content"]) == 1  # just the prompt


# =============================================================================
# EXPORT FUNCTION TESTS
# =============================================================================

class TestExportFunctions:
    """Tests for export utility functions."""
    
    def test_export_testcases_to_csv(self, sample_test_cases):
        """Test CSV export."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            result_path = export_testcases_to_csv(sample_test_cases, output_path)
            
            assert result_path == output_path
            assert os.path.exists(output_path)
            
            # Read and verify
            with open(output_path, 'r') as f:
                content = f.read()
            
            assert "TC_LOGIN_001" in content
            assert "TC_LOGIN_002" in content
            assert "smoke,login" in content
        finally:
            os.unlink(output_path)
    
    def test_export_pages_to_json(self, sample_page_metadata):
        """Test JSON export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result_paths = export_pages_to_json([sample_page_metadata], tmpdir)
            
            assert len(result_paths) == 1
            assert os.path.exists(result_paths[0])
            
            # Read and verify
            with open(result_paths[0], 'r') as f:
                data = json.load(f)
            
            assert data["page_name"] == "LoginPage"
            assert len(data["elements"]) == 4


# =============================================================================
# INTEGRATION TEST (MOCK)
# =============================================================================

class TestToolsIntegration:
    """Integration tests using mocks."""
    
    def test_full_flow_mocked(self, mock_bedrock_client, sample_page_metadata):
        """Test full discovery -> generation flow with mocks."""
        # Setup mock LLM response
        mock_response_text = json.dumps([
            {
                "test_id": "TC_LOGIN_001",
                "test_name": "Valid login with correct credentials",
                "module": "login",
                "priority": "P0",
                "preconditions": "User has valid account",
                "steps": "Navigate to login page|Enter username|Enter password|Click login",
                "expected_result": "User redirected to products page",
                "test_data": "username=standard_user|password=secret_sauce",
                "tags": "smoke,login",
                "page_name": "LoginPage"
            },
            {
                "test_id": "TC_LOGIN_002",
                "test_name": "Invalid login with wrong password",
                "module": "login",
                "priority": "P1",
                "steps": "Enter username|Enter wrong password|Click login",
                "expected_result": "Error message displayed",
                "test_data": "username=standard_user|password=wrong",
                "tags": "negative",
                "page_name": "LoginPage"
            }
        ])
        
        mock_bedrock_client.extract_text.return_value = mock_response_text
        
        # Create generator
        generator = TestCaseGenerator(mock_bedrock_client)
        
        # Generate test cases
        test_cases = generator.generate([sample_page_metadata], "login")
        
        # Verify
        assert len(test_cases) == 2
        assert test_cases[0].test_id == "TC_LOGIN_001"
        assert test_cases[1].test_id == "TC_LOGIN_002"
        
        # Export to temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Export test cases
            csv_path = os.path.join(tmpdir, "testcases.csv")
            export_testcases_to_csv(test_cases, csv_path)
            assert os.path.exists(csv_path)
            
            # Export page metadata
            json_paths = export_pages_to_json([sample_page_metadata], tmpdir)
            assert len(json_paths) == 1
            assert os.path.exists(json_paths[0])


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
