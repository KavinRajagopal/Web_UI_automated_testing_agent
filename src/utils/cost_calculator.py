"""Cost calculator for LLM usage.

Pricing based on AWS Bedrock Claude Opus 4.5 pricing (as of 2024).
Prices are per 1M tokens.

NOTE: These are approximate costs. Actual pricing may vary by:
- AWS region
- Pricing tier/commitment
- Time of usage
- AWS pricing updates

For accurate pricing, check: https://aws.amazon.com/bedrock/pricing/
"""

from typing import Dict, Optional

# Claude Opus 4.5 pricing (USD per 1M tokens)
# Source: AWS Bedrock pricing (approximate, may vary by region)
# NOTE: Claude Opus 4.5 is the most powerful (and expensive) model.
# Output tokens cost 5x more than input tokens, which is why costs can seem high.
# For cost optimization, consider using Claude Sonnet or Claude Haiku for simpler tasks.
CLAUDE_OPUS_4_5_PRICING = {
    "input": 15.00,   # $15 per 1M input tokens
    "output": 75.00,  # $75 per 1M output tokens (5x input cost)
}

# Alternative model pricing (for future use)
MODEL_PRICING = {
    "us.anthropic.claude-opus-4-5-20251101-v1:0": CLAUDE_OPUS_4_5_PRICING,
    "claude-opus-4-5": CLAUDE_OPUS_4_5_PRICING,
    # Add other models as needed
}


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model_id: str = "us.anthropic.claude-opus-4-5-20251101-v1:0"
) -> Dict[str, float]:
    """
    Calculate approximate cost for LLM usage.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model_id: Model identifier (default: Claude Opus 4.5)
        
    Returns:
        Dict with:
            - input_cost: Cost for input tokens (USD)
            - output_cost: Cost for output tokens (USD)
            - total_cost: Total cost (USD)
            - input_tokens: Input token count
            - output_tokens: Output token count
    """
    # Get pricing for model (default to Claude Opus 4.5)
    pricing = MODEL_PRICING.get(model_id, CLAUDE_OPUS_4_5_PRICING)
    
    # Calculate costs (per 1M tokens)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    
    return {
        "input_cost": round(input_cost, 4),
        "output_cost": round(output_cost, 4),
        "total_cost": round(total_cost, 4),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_id": model_id
    }


def format_cost(cost: float) -> str:
    """
    Format cost for display.
    
    Args:
        cost: Cost in USD
        
    Returns:
        Formatted string (e.g., "$0.1234" or "$0.00")
    """
    if cost < 0.01:
        return f"${cost:.6f}"
    elif cost < 1.0:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"
