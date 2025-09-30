"""
Example Router Configuration with Parameter Validation

This module demonstrates how to configure an LLM router with proper parameter
validation, fallback strategies, and best practices for production use.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ModelProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    COHERE = "cohere"
    LOCAL = "local"


class TaskType(Enum):
    """Task types for intelligent routing."""
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    SEARCH = "search"
    EMBEDDING = "embedding"


@dataclass
class ModelConfig:
    """Configuration for a single model."""

    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30
    retry_attempts: int = 3
    cost_per_1k_tokens: float = 0.0

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")

        if self.cost_per_1k_tokens < 0:
            raise ValueError("cost_per_1k_tokens must be non-negative")


@dataclass
class RoutingRule:
    """Routing rule for task-based model selection."""

    task_type: TaskType
    primary_model: str
    fallback_models: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate routing rule."""
        if not self.primary_model:
            raise ValueError("primary_model cannot be empty")

        if self.primary_model in self.fallback_models:
            raise ValueError("primary_model cannot be in fallback_models")


@dataclass
class RouterConfig:
    """Complete router configuration."""

    models: Dict[str, ModelConfig]
    routing_rules: List[RoutingRule]
    default_model: str
    enable_caching: bool = True
    enable_fallback: bool = True
    log_requests: bool = True
    budget_limit_usd: Optional[float] = None

    def __post_init__(self):
        """Validate router configuration."""
        # Validate default model exists
        if self.default_model not in self.models:
            raise ValueError(f"default_model '{self.default_model}' not found in models")

        # Validate routing rules reference existing models
        for rule in self.routing_rules:
            if rule.primary_model not in self.models:
                raise ValueError(
                    f"Rule for {rule.task_type}: primary_model '{rule.primary_model}' not found"
                )

            for fallback in rule.fallback_models:
                if fallback not in self.models:
                    raise ValueError(
                        f"Rule for {rule.task_type}: fallback_model '{fallback}' not found"
                    )

        # Validate budget limit
        if self.budget_limit_usd is not None and self.budget_limit_usd <= 0:
            raise ValueError("budget_limit_usd must be positive")

    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get the primary model for a given task type."""
        for rule in self.routing_rules:
            if rule.task_type == task_type:
                return rule.primary_model
        return self.default_model

    def get_fallback_chain(self, task_type: TaskType) -> List[str]:
        """Get the complete fallback chain for a task type."""
        for rule in self.routing_rules:
            if rule.task_type == task_type:
                return [rule.primary_model] + rule.fallback_models
        return [self.default_model]


# Example Configuration 1: Production Setup with Multiple Providers
def create_production_config() -> RouterConfig:
    """
    Production configuration with multiple providers and comprehensive fallback.

    This setup uses:
    - Claude Sonnet 4 for reasoning tasks
    - GPT-4 for code generation
    - Gemini Pro for analysis
    - Local embeddings for cost efficiency
    """

    models = {
        "claude-sonnet-4": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.7,
            cost_per_1k_tokens=0.015,
        ),
        "gpt-4-turbo": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4-turbo-preview",
            max_tokens=4096,
            temperature=0.5,
            cost_per_1k_tokens=0.01,
        ),
        "gemini-pro": ModelConfig(
            provider=ModelProvider.GOOGLE,
            model_name="gemini-pro",
            max_tokens=2048,
            temperature=0.7,
            cost_per_1k_tokens=0.0005,
        ),
        "local-llama": ModelConfig(
            provider=ModelProvider.LOCAL,
            model_name="llama-3-70b",
            endpoint="http://localhost:8000",
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_tokens=0.0,
        ),
    }

    routing_rules = [
        RoutingRule(
            task_type=TaskType.REASONING,
            primary_model="claude-sonnet-4",
            fallback_models=["gpt-4-turbo", "gemini-pro"],
            conditions={"min_context_length": 4000}
        ),
        RoutingRule(
            task_type=TaskType.CODE_GENERATION,
            primary_model="gpt-4-turbo",
            fallback_models=["claude-sonnet-4", "local-llama"],
            conditions={"prefer_deterministic": True}
        ),
        RoutingRule(
            task_type=TaskType.ANALYSIS,
            primary_model="gemini-pro",
            fallback_models=["claude-sonnet-4", "gpt-4-turbo"],
            conditions={"max_cost_per_request": 0.05}
        ),
        RoutingRule(
            task_type=TaskType.SEARCH,
            primary_model="gemini-pro",
            fallback_models=["local-llama"],
            conditions={"prefer_fast": True}
        ),
    ]

    return RouterConfig(
        models=models,
        routing_rules=routing_rules,
        default_model="claude-sonnet-4",
        enable_caching=True,
        enable_fallback=True,
        log_requests=True,
        budget_limit_usd=100.0,
    )


# Example Configuration 2: Cost-Optimized Setup
def create_budget_config() -> RouterConfig:
    """
    Budget-conscious configuration prioritizing cost efficiency.

    Uses cheaper models as primary with premium models as fallback only
    when quality is critical.
    """

    models = {
        "claude-haiku": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_tokens=0.00025,
        ),
        "gpt-3.5-turbo": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_tokens=0.0005,
        ),
        "claude-sonnet": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            temperature=0.7,
            cost_per_1k_tokens=0.003,
        ),
    }

    routing_rules = [
        RoutingRule(
            task_type=TaskType.CODE_GENERATION,
            primary_model="gpt-3.5-turbo",
            fallback_models=["claude-sonnet"],
        ),
        RoutingRule(
            task_type=TaskType.REASONING,
            primary_model="claude-haiku",
            fallback_models=["claude-sonnet"],
        ),
        RoutingRule(
            task_type=TaskType.ANALYSIS,
            primary_model="claude-haiku",
            fallback_models=["gpt-3.5-turbo"],
        ),
    ]

    return RouterConfig(
        models=models,
        routing_rules=routing_rules,
        default_model="claude-haiku",
        enable_caching=True,
        enable_fallback=True,
        log_requests=True,
        budget_limit_usd=10.0,
    )


# Example Configuration 3: Local-First Setup
def create_local_config() -> RouterConfig:
    """
    Local-first configuration for offline/privacy-sensitive environments.

    Uses local models as primary with cloud fallback only when necessary.
    """

    models = {
        "local-llama-70b": ModelConfig(
            provider=ModelProvider.LOCAL,
            model_name="llama-3-70b-instruct",
            endpoint="http://localhost:8000",
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_tokens=0.0,
        ),
        "local-codellama": ModelConfig(
            provider=ModelProvider.LOCAL,
            model_name="codellama-34b",
            endpoint="http://localhost:8001",
            max_tokens=4096,
            temperature=0.5,
            cost_per_1k_tokens=0.0,
        ),
        "claude-sonnet": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            temperature=0.7,
            cost_per_1k_tokens=0.003,
        ),
    }

    routing_rules = [
        RoutingRule(
            task_type=TaskType.CODE_GENERATION,
            primary_model="local-codellama",
            fallback_models=["claude-sonnet"],
        ),
        RoutingRule(
            task_type=TaskType.REASONING,
            primary_model="local-llama-70b",
            fallback_models=["claude-sonnet"],
        ),
        RoutingRule(
            task_type=TaskType.ANALYSIS,
            primary_model="local-llama-70b",
            fallback_models=["claude-sonnet"],
        ),
    ]

    return RouterConfig(
        models=models,
        routing_rules=routing_rules,
        default_model="local-llama-70b",
        enable_caching=True,
        enable_fallback=True,
        log_requests=True,
        budget_limit_usd=None,  # No budget limit for local models
    )


# Usage Examples
if __name__ == "__main__":
    # Example 1: Create production config
    print("=== Production Configuration ===")
    prod_config = create_production_config()
    print(f"Default model: {prod_config.default_model}")
    print(f"Models configured: {len(prod_config.models)}")
    print(f"Routing rules: {len(prod_config.routing_rules)}")
    print(f"Budget limit: ${prod_config.budget_limit_usd}")

    # Example 2: Get model for specific task
    print("\n=== Task Routing ===")
    reasoning_model = prod_config.get_model_for_task(TaskType.REASONING)
    print(f"Reasoning task → {reasoning_model}")

    code_model = prod_config.get_model_for_task(TaskType.CODE_GENERATION)
    print(f"Code generation task → {code_model}")

    # Example 3: Get fallback chain
    print("\n=== Fallback Chain ===")
    fallback_chain = prod_config.get_fallback_chain(TaskType.REASONING)
    print(f"Reasoning fallback chain: {' → '.join(fallback_chain)}")

    # Example 4: Create budget config
    print("\n=== Budget Configuration ===")
    budget_config = create_budget_config()
    print(f"Default model: {budget_config.default_model}")
    print(f"Budget limit: ${budget_config.budget_limit_usd}")

    # Example 5: Create local config
    print("\n=== Local Configuration ===")
    local_config = create_local_config()
    print(f"Default model: {local_config.default_model}")
    print(f"Budget limit: {local_config.budget_limit_usd or 'None (local)'}")

    # Example 6: Validation error handling
    print("\n=== Validation Examples ===")
    try:
        # This will raise an error: invalid temperature
        invalid_model = ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="test-model",
            temperature=3.0  # Invalid!
        )
    except ValueError as e:
        print(f"✓ Caught validation error: {e}")

    try:
        # This will raise an error: default_model not in models
        invalid_config = RouterConfig(
            models={"model1": ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_name="test"
            )},
            routing_rules=[],
            default_model="nonexistent_model"  # Invalid!
        )
    except ValueError as e:
        print(f"✓ Caught validation error: {e}")