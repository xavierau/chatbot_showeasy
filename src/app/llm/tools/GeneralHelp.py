"""
GeneralHelp Tool - Provides general platform help and information.

This tool handles:
- Platform navigation and features
- Account management
- General FAQs
- Platform policies
- Contact information
- Customer service

Source: docs/context/zh-TW/
- 01_platform_overview.md
- 04_customer_service.md
- 05_contact_information.md
"""
import dspy
from pathlib import Path
from typing import Dict
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_general_help_context() -> str:
    """
    Load general help content from the context files.
    Combines platform overview, customer service, and contact information.
    Uses lru_cache to avoid repeated file reads.

    Returns:
        The combined content of the general help context files.
    """
    context_dir = Path(__file__).parent.parent.parent.parent.parent / "docs" / "context" / "zh-TW"

    context_files = [
        "01_platform_overview.md",
        "04_customer_service.md",
        "05_contact_information.md",
    ]

    combined_content = []
    for filename in context_files:
        file_path = context_dir / filename
        if file_path.exists():
            combined_content.append(file_path.read_text(encoding="utf-8"))
        else:
            combined_content.append(f"[Warning: {filename} not found]")

    return "\n\n---\n\n".join(combined_content)


def _get_general_help(category: str = "general") -> Dict[str, str]:
    """
    Retrieves general help information from the official context files.

    Args:
        category: Category of help - 'navigation', 'account', 'policies', 'features', 'contact'
                 (Note: category is kept for backward compatibility but the full
                 context is always returned for the LLM to process)

    Returns:
        Dictionary with help information from docs/context/zh-TW/
    """
    try:
        help_content = _load_general_help_context()
        return {"info": help_content}
    except Exception as e:
        return {"info": f"Error loading help information: {e}"}


# Create DSPy Tool for general help
GeneralHelp = dspy.Tool(
    func=_get_general_help,
    name="general_help",
    desc="""Get general help and information about the ShowEasy platform.

Parameters:
- category: Type of help needed - 'navigation', 'account', 'policies', 'features', or 'contact'

Use this tool when users ask about:
- How to use the platform
- Account management
- Platform features
- Policies and terms
- How to contact support
- General platform questions"""
)
