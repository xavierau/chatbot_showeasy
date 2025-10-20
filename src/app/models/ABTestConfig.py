from dataclasses import dataclass
from typing import Literal, Optional
from enum import Enum


class ABVariant(str, Enum):
    """AB test variant selection."""
    CONTROL = "control"
    VARIANT_A = "variant_a"
    VARIANT_B = "variant_b"


@dataclass
class ModuleABConfig:
    """AB testing configuration for a specific module.

    Attributes:
        enabled: Whether AB testing is enabled for this module
        variant: Which variant to use (control, variant_a, variant_b)
        description: Optional description of what this variant tests
    """
    enabled: bool = False
    variant: ABVariant = ABVariant.CONTROL
    description: Optional[str] = None


@dataclass
class ABTestConfig:
    """Comprehensive AB testing configuration for ConversationOrchestrator.

    Allows independent AB testing for each nested module:
    - pre_guardrails: Test different pre-guardrail models/strategies
    - post_guardrails: Test different post-guardrail models/strategies
    - agent: Test different ReAct agent configurations

    Example:
        config = ABTestConfig(
            pre_guardrails=ModuleABConfig(
                enabled=True,
                variant=ABVariant.VARIANT_A,
                description="Testing GEPA-optimized model vs baseline"
            ),
            post_guardrails=ModuleABConfig(enabled=False),
            agent=ModuleABConfig(enabled=False)
        )
    """
    pre_guardrails: ModuleABConfig = None
    post_guardrails: ModuleABConfig = None
    agent: ModuleABConfig = None

    def __post_init__(self):
        """Initialize default ModuleABConfig for None values."""
        if self.pre_guardrails is None:
            self.pre_guardrails = ModuleABConfig()
        if self.post_guardrails is None:
            self.post_guardrails = ModuleABConfig()
        if self.agent is None:
            self.agent = ModuleABConfig()

    @classmethod
    def default(cls) -> "ABTestConfig":
        """Create default config with all AB testing disabled (control group)."""
        return cls(
            pre_guardrails=ModuleABConfig(enabled=False, variant=ABVariant.CONTROL),
            post_guardrails=ModuleABConfig(enabled=False, variant=ABVariant.CONTROL),
            agent=ModuleABConfig(enabled=False, variant=ABVariant.CONTROL)
        )

    def is_any_variant_active(self) -> bool:
        """Check if any module is using a non-control variant."""
        return (
            (self.pre_guardrails.enabled and self.pre_guardrails.variant != ABVariant.CONTROL) or
            (self.post_guardrails.enabled and self.post_guardrails.variant != ABVariant.CONTROL) or
            (self.agent.enabled and self.agent.variant != ABVariant.CONTROL)
        )
