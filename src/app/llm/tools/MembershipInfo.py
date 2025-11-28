"""
MembershipInfo Tool - Provides information about membership benefits and features.

This tool handles all membership-related queries including:
- Membership benefits and features
- Pricing and plans
- Upgrade options
- Discounts and savings

Source: docs/context/zh-TW/02_membership_program.md
"""
import dspy
from pathlib import Path
from typing import Dict
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_membership_context() -> str:
    """
    Load membership program content from the context file.
    Uses lru_cache to avoid repeated file reads.

    Returns:
        The full content of the membership program context file.
    """
    context_file = Path(__file__).parent.parent.parent.parent.parent / "docs" / "context" / "zh-TW" / "02_membership_program.md"

    if not context_file.exists():
        raise FileNotFoundError(f"Membership context file not found: {context_file}")

    return context_file.read_text(encoding="utf-8")


def _get_membership_info(query_type: str = "general") -> Dict[str, str]:
    """
    Retrieves membership information from the official context file.

    Args:
        query_type: Type of membership query - 'general', 'benefits', 'pricing', 'upgrade'
                   (Note: query_type is kept for backward compatibility but the full
                   context is always returned for the LLM to process)

    Returns:
        Dictionary with membership information from docs/context/zh-TW/02_membership_program.md
    """
    try:
        membership_content = _load_membership_context()
        return {"info": membership_content}
    except FileNotFoundError as e:
        return {"info": f"Error loading membership information: {e}"}


# Create DSPy Tool for membership information
MembershipInfo = dspy.Tool(
    func=_get_membership_info,
    name="membership_info",
    desc="""Get information about ShowEasy Premium Membership benefits, pricing, and upgrade options.

Parameters:
- query_type: Type of information needed - 'general', 'benefits', 'pricing', or 'upgrade'

Use this tool when users ask about:
- Membership benefits or features
- How much membership costs
- How to upgrade to premium
- Discounts available to members
- What they get with membership"""
)
