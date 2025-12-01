"""
Memory Service Interface

This module defines the abstract interface for memory services.
Following the Dependency Inversion Principle (DIP), high-level modules
depend on this abstraction rather than concrete implementations.
"""

from abc import ABC, abstractmethod
import dspy


class MemoryService(ABC):
    """Abstract interface for conversation memory storage.

    This interface defines the contract for storing and retrieving
    conversation history. Implementations can use different backends
    (file, database, Redis, etc.) while maintaining the same API.

    Design Patterns:
    - Strategy Pattern: Different storage strategies can be swapped
    - Repository Pattern: Abstracts data access operations
    """

    @abstractmethod
    def get_memory(self, session_id: str, rounds: int = 10) -> dspy.History:
        """Retrieve conversation history with sliding window.

        Args:
            session_id: Unique session identifier
            rounds: Number of conversation rounds to retrieve (default: 10).
                    Each round = 1 user message + 1 assistant message.
                    Returns the most recent rounds.

        Returns:
            dspy.History with the most recent messages up to limit.
        """
        pass

    @abstractmethod
    def update_memory(self, session_id: str, messages: dspy.History) -> None:
        """Update conversation history for a session.

        DEPRECATED: Use append_messages() instead for incremental updates.
        This method overwrites the entire conversation history.

        Args:
            session_id: Unique session identifier
            messages: dspy.History containing conversation messages
        """
        pass

    @abstractmethod
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
        pass
