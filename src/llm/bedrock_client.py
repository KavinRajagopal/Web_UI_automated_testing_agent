"""AWS Bedrock client for Claude Opus 4.5 using Converse API."""
import json
import logging
from typing import List, Dict, Any, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class BedrockClient:
    """
    Bedrock client using Converse API for Claude Opus 4.5.
    
    This client is used by all agent nodes that need LLM capabilities:
    - Planning: Analyze test cases, create generation plan
    - Generation: Generate Page Objects, Flows, Tests
    - Recovery: Fix errors in generated code
    - Reporting: Generate AI analysis report
    """
    
    def __init__(
        self,
        model_id: str = "us.anthropic.claude-opus-4-5-20251101-v1:0",
        region_name: str = "us-east-2",
        profile_name: Optional[str] = None,
        max_tokens: int = 16384,
        temperature: float = 0.7
    ):
        """
        Initialize Bedrock client.
        
        Args:
            model_id: Bedrock model ID (inference profile for Claude Opus 4.5)
            region_name: AWS region
            profile_name: AWS profile name (from ~/.aws/credentials)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 1.0)
        """
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.region_name = region_name
        self.profile_name = profile_name
        
        # Track usage for reporting
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        
        # Create session with profile if specified
        if profile_name:
            session = boto3.Session(profile_name=profile_name)
        else:
            session = boto3.Session()
        
        # Initialize Bedrock Runtime client with extended timeout
        # Claude Opus with high token counts can take several minutes
        config = Config(
            read_timeout=600,  # 10 minutes
            connect_timeout=10,
            retries={'max_attempts': 3}
        )
        self.client = session.client(
            service_name='bedrock-runtime',
            region_name=region_name,
            config=config
        )
        
        logger.info(
            f"Bedrock client initialized: {model_id} in {region_name}"
            f"{f' (profile: {profile_name})' if profile_name else ''}"
        )
    
    def converse(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call Bedrock Converse API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
                     Format: [{"role": "user", "content": [{"text": "..."}]}]
            system: Optional system prompt
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            
        Returns:
            Full response dict from Bedrock Converse API
            
        Raises:
            ClientError: If AWS API call fails
        """
        try:
            # Prepare request
            request = {
                "modelId": self.model_id,
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens or self.max_tokens,
                    "temperature": temperature if temperature is not None else self.temperature,
                }
            }
            
            # Add system prompt if provided
            if system:
                request["system"] = [{"text": system}]
            
            logger.debug(f"Converse request to {self.model_id}")
            
            # Call Converse API
            response = self.client.converse(**request)
            
            # Track usage
            self.call_count += 1
            if 'usage' in response:
                self.total_input_tokens += response['usage'].get('inputTokens', 0)
                self.total_output_tokens += response['usage'].get('outputTokens', 0)
            
            logger.info(
                f"Converse response: stop_reason={response.get('stopReason')}, "
                f"tokens={response.get('usage', {})}"
            )
            
            return response
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Bedrock ClientError ({error_code}): {error_message}")
            raise
        except BotoCoreError as e:
            logger.error(f"Bedrock BotoCoreError: {str(e)}")
            raise
    
    def extract_text(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from Converse response.
        
        Args:
            response: Response dict from converse()
            
        Returns:
            Extracted text content
        """
        try:
            output = response.get('output', {})
            message = output.get('message', {})
            content = message.get('content', [])
            
            if content and len(content) > 0:
                return content[0].get('text', '')
            return ''
        except (KeyError, IndexError, AttributeError) as e:
            logger.warning(f"Failed to extract text from response: {e}")
            return ''
    
    def chat(
        self,
        user_message: str,
        system: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Simple chat interface - send message, get text response.
        
        Args:
            user_message: The user's message
            system: Optional system prompt
            conversation_history: Previous messages for multi-turn
            
        Returns:
            Assistant's response as text
        """
        # Build messages list
        messages = conversation_history.copy() if conversation_history else []
        
        # Add user message
        messages.append({
            "role": "user",
            "content": [{"text": user_message}]
        })
        
        # Call Converse API
        response = self.converse(messages=messages, system=system)
        
        # Extract and return text
        return self.extract_text(response)
    
    def chat_json(
        self,
        user_message: str,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chat expecting JSON response - parses response as JSON.
        
        Args:
            user_message: The user's message (should request JSON output)
            system: Optional system prompt (should specify JSON format)
            
        Returns:
            Parsed JSON dict
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        response_text = self.chat(user_message, system)
        
        # Try to extract JSON from response
        # Claude often wraps JSON in ```json ... ``` blocks
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text.strip())
    
    def get_usage_stats(self) -> Dict[str, int]:
        """
        Get usage statistics for this client.
        
        Returns:
            Dict with call_count, total_input_tokens, total_output_tokens
        """
        return {
            "call_count": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
