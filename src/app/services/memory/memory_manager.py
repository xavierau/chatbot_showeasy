"""
Memory Manager

This module provides a facade for memory operations, delegating to
the injected MemoryService implementation.
"""

import dspy

from .memory_interface import MemoryService


class MemoryManager:
    """Facade for memory operations.

    This class provides a simplified interface for memory operations,
    delegating to the injected MemoryService implementation.

    Design Patterns:
    - Facade Pattern: Simplifies memory service usage
    - Dependency Injection: Accepts MemoryService implementation

    Args:
        memory_service: MemoryService implementation to use
    """

    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    def get_memory(self, session_id: str, rounds: int = 10) -> dspy.History:
        """Retrieve conversation history with sliding window.

        Args:
            session_id: Unique session identifier
            rounds: Number of conversation rounds to retrieve (default: 10).
                    Each round = 1 user message + 1 assistant message.

        Returns:
            dspy.History with the most recent messages.
        """
        return self.memory_service.get_memory(session_id, rounds)

    def update_memory(self, session_id: str, messages: dspy.History) -> None:
        """Update conversation history for a session.

        DEPRECATED: Use append_messages() instead for incremental updates.
        This method overwrites the entire conversation history.

        Args:
            session_id: Unique session identifier
            messages: dspy.History containing conversation messages
        """
        self.memory_service.update_memory(session_id, messages)

    def append_messages(self, session_id: str, messages: list[dict]) -> None:
        """Append new messages to existing conversation history.

        This method appends new messages without reading the entire history first,
        making it efficient for incremental updates in a turn-by-turn conversation.

        Args:
            session_id: Unique session identifier
            messages: List of message dicts with 'role' and 'content' keys.
                     Example: [{"role": "user", "content": "Hello"},
                              {"role": "assistant", "content": "Hi!"}]
        """
        self.memory_service.append_messages(session_id, messages)
