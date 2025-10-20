#!/usr/bin/env python3
"""
AB Testing Example for ConversationOrchestrator

This script demonstrates how to use AB testing configuration
to compare different module variants.

Usage:
    python examples/ab_testing_example.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from app.models import ABTestConfig, ModuleABConfig, ABVariant
from app.llm.modules import ConversationOrchestrator


def example_1_default_control():
    """Example 1: Default behavior (no AB testing)"""
    print("\n" + "="*80)
    print("Example 1: Default Control (No AB Testing)")
    print("="*80)

    orchestrator = ConversationOrchestrator()
    print("✓ Orchestrator initialized with default config")
    print("  - All modules use control variants")
    print("  - Optimized models loaded where available")


def example_2_pre_guardrails_baseline():
    """Example 2: Test baseline pre-guardrails (no optimization)"""
    print("\n" + "="*80)
    print("Example 2: Pre-Guardrails Baseline Test")
    print("="*80)

    ab_config = ABTestConfig(
        pre_guardrails=ModuleABConfig(
            enabled=True,
            variant=ABVariant.VARIANT_A,
            description="Baseline pre-guardrails without GEPA optimization"
        )
    )

    orchestrator = ConversationOrchestrator(ab_config=ab_config)
    print("✓ Orchestrator initialized with VARIANT_A pre-guardrails")
    print("  - Using baseline (unoptimized) model")
    print("  - Compare against control to measure GEPA improvement")


def example_3_agent_reduced_iterations():
    """Example 3: Test agent with reduced max_iters"""
    print("\n" + "="*80)
    print("Example 3: Agent with Reduced Iterations")
    print("="*80)

    ab_config = ABTestConfig(
        agent=ModuleABConfig(
            enabled=True,
            variant=ABVariant.VARIANT_A,
            description="Agent with max_iters=5 for faster responses"
        )
    )

    orchestrator = ConversationOrchestrator(ab_config=ab_config)
    print("✓ Orchestrator initialized with VARIANT_A agent")
    print("  - Using max_iters=5 (vs control max_iters=10)")
    print("  - Test hypothesis: Faster responses without quality loss")


def example_4_multi_module_testing():
    """Example 4: Test multiple modules simultaneously"""
    print("\n" + "="*80)
    print("Example 4: Multi-Module AB Testing")
    print("="*80)

    ab_config = ABTestConfig(
        pre_guardrails=ModuleABConfig(
            enabled=True,
            variant=ABVariant.VARIANT_B,
            description="Pre-guardrails experimental variant"
        ),
        agent=ModuleABConfig(
            enabled=True,
            variant=ABVariant.VARIANT_A,
            description="Agent with reduced iterations"
        )
    )

    orchestrator = ConversationOrchestrator(ab_config=ab_config)
    print("✓ Orchestrator initialized with multi-module AB config")
    print("  - Pre-guardrails: VARIANT_B")
    print("  - Agent: VARIANT_A")
    print("  - Post-guardrails: CONTROL (default)")


def example_5_hash_based_bucketing():
    """Example 5: Demonstrate hash-based user bucketing"""
    print("\n" + "="*80)
    print("Example 5: Hash-Based User Bucketing")
    print("="*80)

    import hashlib
    import os

    # Simulate environment variables
    os.environ['AB_TEST_ENABLED'] = 'true'
    os.environ['AB_TEST_MODULE'] = 'pre_guardrails'
    os.environ['AB_TEST_VARIANT_A_RATIO'] = '50'
    os.environ['AB_TEST_VARIANT_B_RATIO'] = '0'

    from app.api.main import get_ab_test_config

    # Test with sample users
    test_users = ['alice@example.com', 'bob@example.com', 'charlie@example.com']

    print("\nUser assignments (50% VARIANT_A, 50% CONTROL):")
    print("-" * 60)

    for user_id in test_users:
        config = get_ab_test_config(user_id, 'session123')

        if config and config.pre_guardrails.enabled:
            variant = config.pre_guardrails.variant.value
        else:
            variant = 'control'

        # Calculate hash for visibility
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100

        print(f"User: {user_id:25} → {variant:12} (hash={hash_val})")

    print("\n✓ Same user always gets same variant (consistent experience)")


def example_6_production_usage():
    """Example 6: Production-ready example with error handling"""
    print("\n" + "="*80)
    print("Example 6: Production-Ready Usage")
    print("="*80)

    try:
        # In production, config comes from environment or request
        import os
        ab_config = None

        if os.getenv('AB_TEST_ENABLED', 'false').lower() == 'true':
            # Would typically use get_ab_test_config(user_id, session_id)
            ab_config = ABTestConfig(
                pre_guardrails=ModuleABConfig(
                    enabled=True,
                    variant=ABVariant.VARIANT_A,
                    description="Production AB test"
                )
            )

        orchestrator = ConversationOrchestrator(ab_config=ab_config)

        # Use orchestrator as normal
        result = orchestrator(
            user_message="What concerts are happening this weekend?",
            previous_conversation=[],
            page_context=""
        )

        print("✓ Production request processed successfully")
        print(f"  - Response: {result.answer[:100]}...")

    except Exception as e:
        print(f"✗ Error: {e}")
        print("  - In production, log error and use default config")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ConversationOrchestrator AB Testing Examples")
    print("="*80)

    example_1_default_control()
    example_2_pre_guardrails_baseline()
    example_3_agent_reduced_iterations()
    example_4_multi_module_testing()
    example_5_hash_based_bucketing()
    example_6_production_usage()

    print("\n" + "="*80)
    print("Examples Complete!")
    print("="*80)
    print("\nFor more information, see:")
    print("  - docs/guides/2025-10-20-ab-testing-guide.md")
    print("  - src/app/models/ABTestConfig.py")
    print("  - src/app/api/main.py (get_ab_test_config)")
    print()
