"""
Cost Calculator for LLM Usage
Converts token usage to USD based on model pricing
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ModelPricing:
    """Pricing information for a model"""
    input_cost_per_1k: float  # USD per 1K input tokens
    output_cost_per_1k: float  # USD per 1K output tokens
    model_name: str


class CostCalculator:
    """
    Calculate costs for LLM API calls
    
    Pricing as of December 2024 (update as needed)
    """
    
    # Model pricing database
    PRICING: Dict[str, ModelPricing] = {
        # Anthropic Claude models
        "claude-sonnet-4": ModelPricing(
            input_cost_per_1k=3.00,
            output_cost_per_1k=15.00,
            model_name="Claude Sonnet 4"
        ),
        "claude-sonnet-4-5": ModelPricing(
            input_cost_per_1k=3.00,
            output_cost_per_1k=15.00,
            model_name="Claude Sonnet 4.5"
        ),
        "claude-opus-4": ModelPricing(
            input_cost_per_1k=15.00,
            output_cost_per_1k=75.00,
            model_name="Claude Opus 4"
        ),
        "claude-haiku-4": ModelPricing(
            input_cost_per_1k=0.25,
            output_cost_per_1k=1.25,
            model_name="Claude Haiku 4"
        ),
        
        # OpenAI models
        "gpt-4o": ModelPricing(
            input_cost_per_1k=2.50,
            output_cost_per_1k=10.00,
            model_name="GPT-4o"
        ),
        "gpt-4-turbo": ModelPricing(
            input_cost_per_1k=10.00,
            output_cost_per_1k=30.00,
            model_name="GPT-4 Turbo"
        ),
        "gpt-3.5-turbo": ModelPricing(
            input_cost_per_1k=0.50,
            output_cost_per_1k=1.50,
            model_name="GPT-3.5 Turbo"
        ),
        
        # Default for unknown models
        "default": ModelPricing(
            input_cost_per_1k=1.00,
            output_cost_per_1k=3.00,
            model_name="Unknown Model"
        ),
    }
    
    @classmethod
    def calculate_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for an API call
        
        Args:
            model: Model identifier (e.g., "claude-sonnet-4")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            float: Cost in USD
        
        Example:
            >>> CostCalculator.calculate_cost("claude-sonnet-4", 1000, 500)
            10.5  # $3 input + $7.5 output = $10.50
        """
        # Normalize model name (remove provider prefix)
        normalized_model = cls._normalize_model_name(model)
        
        # Get pricing (fallback to default if not found)
        pricing = cls.PRICING.get(normalized_model, cls.PRICING["default"])
        
        # Calculate costs
        input_cost = (input_tokens / 1000.0) * pricing.input_cost_per_1k
        output_cost = (output_tokens / 1000.0) * pricing.output_cost_per_1k
        
        total_cost = input_cost + output_cost
        
        return round(total_cost, 6)  # Round to 6 decimal places
    
    @classmethod
    def _normalize_model_name(cls, model: str) -> str:
        """
        Normalize model name by removing provider prefixes
        
        Examples:
            "anthropic/claude-sonnet-4" -> "claude-sonnet-4"
            "openai/gpt-4o" -> "gpt-4o"
        """
        # Remove provider prefix if present
        if "/" in model:
            model = model.split("/")[-1]
        
        # Remove version suffixes
        model = model.split("@")[0]
        
        # Handle common variations
        if "claude-sonnet-4.5" in model or "claude-sonnet-4-5" in model:
            return "claude-sonnet-4-5"
        elif "claude-sonnet-4" in model:
            return "claude-sonnet-4"
        elif "claude-opus-4" in model:
            return "claude-opus-4"
        elif "claude-haiku-4" in model:
            return "claude-haiku-4"
        elif "gpt-4o" in model:
            return "gpt-4o"
        elif "gpt-4-turbo" in model:
            return "gpt-4-turbo"
        elif "gpt-3.5-turbo" in model:
            return "gpt-3.5-turbo"
        
        return model
    
    @classmethod
    def get_model_pricing(cls, model: str) -> ModelPricing:
        """Get pricing information for a model"""
        normalized = cls._normalize_model_name(model)
        return cls.PRICING.get(normalized, cls.PRICING["default"])
    
    @classmethod
    def estimate_cost(
        cls,
        model: str,
        estimated_tokens: int,
        input_output_ratio: float = 0.3
    ) -> float:
        """
        Estimate cost before making API call
        
        Args:
            model: Model identifier
            estimated_tokens: Total estimated tokens
            input_output_ratio: Ratio of output to input (default 0.3)
        
        Returns:
            float: Estimated cost in USD
        """
        # Split tokens between input and output
        input_tokens = int(estimated_tokens / (1 + input_output_ratio))
        output_tokens = int(estimated_tokens * input_output_ratio)
        
        return cls.calculate_cost(model, input_tokens, output_tokens)


# Convenience function
def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for an API call"""
    return CostCalculator.calculate_cost(model, input_tokens, output_tokens)