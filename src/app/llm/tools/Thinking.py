"""Thinking tool - provides working memory/scratchpad for agent reasoning.

This tool allows the agent to externalize its thought process, organize complex
reasoning, and maintain working memory across multiple reasoning steps.
"""

import dspy


def Thinking(note: str) -> str:
    """Agent's internal scratchpad for organizing thoughts and reasoning.

    Use this tool to:
    - Break down complex queries into steps
    - Organize information before making decisions
    - Keep track of multiple pieces of information
    - Plan multi-tool sequences
    - Summarize findings before final response

    This tool does nothing except echo back your note - it's purely for your
    working memory and won't be shown to the user.

    Args:
        note: Your internal thoughts, plans, or reasoning notes

    Returns:
        The same note (for agent's working memory)

    Example usage:
        User: "I want rock concerts in LA this weekend, and what's included in membership?"

        Agent thinking process:
        1. Thinking("Complex query with 2 parts: event search + membership info")
        2. Thinking("Step 1: Search for rock concerts in LA this weekend")
        3. SearchEvent(query="rock concerts", location="Los Angeles", ...)
        4. Thinking("Step 2: Get membership benefits info")
        5. MembershipInfo(query_type="benefits")
        6. Thinking("Now combine both results into coherent response")
        7. [Generate final answer]
    """
    return note
