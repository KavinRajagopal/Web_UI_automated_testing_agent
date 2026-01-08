#!/usr/bin/env python3
"""
Test suite for Bedrock Client (LLM integration).

Verifies:
1. AWS credentials are configured correctly
2. Bedrock client can connect
3. Claude Opus 4.5 responds via Converse API
4. JSON parsing works
5. Usage tracking works

Usage:
    python -m tests.test_bedrock_client
    # or
    pytest tests/test_bedrock_client.py -v
"""
import os
import sys
import logging

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.llm.bedrock_client import BedrockClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner(text: str):
    """Print a formatted banner."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_bedrock_connection():
    """Test: Verify Bedrock client initializes."""
    print_banner("Test: Initialize Bedrock Client")
    
    try:
        client = BedrockClient(
            model_id="us.anthropic.claude-opus-4-5-20251101-v1:0",
            region_name="us-east-2",
            profile_name="tring-kavin"
        )
        print("✓ Bedrock client initialized successfully")
        print(f"  Model: {client.model_id}")
        print(f"  Region: {client.region_name}")
        print(f"  Profile: {client.profile_name}")
        return client
    except Exception as e:
        print(f"✗ Failed to initialize Bedrock client: {e}")
        return None


def test_simple_chat(client: BedrockClient):
    """Test: Send a simple message and get response."""
    print_banner("Test: Simple Chat")
    
    try:
        prompt = "Say 'Hello from Claude Opus 4.5!' and tell me what 2+2 equals. Keep it brief."
        
        print(f"Sending: {prompt}")
        print("Waiting for response...")
        
        response = client.chat(prompt)
        
        print(f"\n✓ Response received:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"✗ Chat failed: {e}")
        return False


def test_system_prompt(client: BedrockClient):
    """Test: Test with system prompt (for agent persona)."""
    print_banner("Test: System Prompt (Agent Persona)")
    
    try:
        system_prompt = """You are a QA automation architect specializing in Selenium + pytest.
Your job is to analyze test cases and generate clean, modular automation code.
Always respond concisely and professionally."""
        
        user_prompt = "What are the 3 most important principles for writing maintainable Page Objects?"
        
        print(f"System: {system_prompt[:80]}...")
        print(f"User: {user_prompt}")
        print("Waiting for response...")
        
        response = client.chat(user_prompt, system=system_prompt)
        
        print(f"\n✓ Response received:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"✗ System prompt test failed: {e}")
        return False


def test_json_response(client: BedrockClient):
    """Test: Request JSON response (for structured outputs)."""
    print_banner("Test: JSON Response")
    
    try:
        system_prompt = "You are a JSON generator. Always respond with valid JSON only, no markdown."
        
        user_prompt = """Generate a JSON object representing a simple Page Object plan:
{
  "page_name": "LoginPage",
  "elements": [list of 3 element names],
  "methods": [list of 3 method names]
}"""
        
        print("Requesting JSON response...")
        
        response = client.chat_json(user_prompt, system=system_prompt)
        
        print(f"\n✓ JSON parsed successfully:")
        print(f"  Page name: {response.get('page_name')}")
        print(f"  Elements: {response.get('elements')}")
        print(f"  Methods: {response.get('methods')}")
        
        return True
    except Exception as e:
        print(f"✗ JSON test failed: {e}")
        return False


def test_usage_stats(client: BedrockClient):
    """Test: Verify usage tracking."""
    print_banner("Test: Usage Statistics")
    
    stats = client.get_usage_stats()
    
    print(f"✓ Usage stats retrieved:")
    print(f"  API calls made: {stats['call_count']}")
    print(f"  Input tokens: {stats['total_input_tokens']}")
    print(f"  Output tokens: {stats['total_output_tokens']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    
    return True


def main():
    """Run all Bedrock client tests."""
    print("\n" + "=" * 60)
    print("  BEDROCK CLIENT TESTS")
    print("  TringPlay Web UI Test Generation Agent")
    print("=" * 60)
    
    results = []
    
    # Test 1: Initialize client
    client = test_bedrock_connection()
    if client is None:
        print("\n✗ TESTS FAILED: Could not initialize Bedrock client")
        print("\nTroubleshooting:")
        print("1. Check AWS profile 'tring-kavin' exists: aws configure list --profile tring-kavin")
        print("2. Check region 'us-east-2' has Bedrock access")
        print("3. Check model access: Claude Opus 4.5 enabled in Bedrock console")
        sys.exit(1)
    results.append(("Initialize Client", True))
    
    # Test 2: Simple chat
    success = test_simple_chat(client)
    results.append(("Simple Chat", success))
    
    # Test 3: System prompt
    success = test_system_prompt(client)
    results.append(("System Prompt", success))
    
    # Test 4: JSON response
    success = test_json_response(client)
    results.append(("JSON Response", success))
    
    # Test 5: Usage stats
    success = test_usage_stats(client)
    results.append(("Usage Stats", success))
    
    # Summary
    print_banner("TEST RESULTS")
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n" + "=" * 60)
        print("  ✓ ALL BEDROCK CLIENT TESTS PASSED")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  ✗ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
