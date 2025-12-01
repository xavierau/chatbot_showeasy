"""
Mem0 Memory Service

This module provides a high-level abstraction layer for Mem0 memory operations.
It wraps the Mem0 Memory client with domain-specific logic and provides a clean
interface for the ShowEasy chatbot.

Design Patterns:
- Facade Pattern: Simplifies Mem0 client usage
- Repository Pattern: Abstracts data access operations
- Dependency Injection: Accepts Memory client instance

Following SOLID Principles:
- Single Responsibility: Only handles memory operations
- Open/Closed: Open for extension via custom categories
- Dependency Inversion: Depends on Memory abstraction
"""

import logging
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass

from mem0 import Memory

from .client import get_mem0_client, Mem0Config
from .categories import SHOWEASY_CATEGORIES, SHOWEASY_INSTRUCTIONS

logger = logging.getLogger(__name__)


@dataclass
class MemoryResult:
    """
    Data class representing a memory operation result.

    Attributes:
        success: Whether the operation succeeded
        data: The result data (memories, IDs, etc.)
        message: Human-readable status message
        error: Error message if operation failed
    """

    success: bool
    data: Optional[Any] = None
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error,
        }


class Mem0Service:
    """
    High-level service for Mem0 memory operations.

    This service provides a clean interface for adding, searching, retrieving,
    updating, and deleting memories. It handles configuration, error handling,
    and domain-specific logic for the ShowEasy chatbot.

    Example:
        # Initialize service
        service = Mem0Service()

        # Add a memory
        result = service.add(
            messages=[
                {"role": "user", "content": "I love jazz concerts"},
                {"role": "assistant", "content": "Great! I'll remember that."}
            ],
            user_id="user123"
        )

        # Search memories
        memories = service.search("music preferences", user_id="user123")

        # Get all memories for a user
        all_memories = service.get_all(user_id="user123")
    """

    def __init__(
        self,
        memory: Optional[Memory] = None,
        config: Optional[Mem0Config] = None,
        custom_categories: Optional[List[Dict[str, str]]] = None,
        custom_instructions: Optional[str] = None,
    ):
        """
        Initialize the Mem0 service.

        Args:
            memory: Optional pre-configured Memory instance.
                   If not provided, creates one using config or defaults.
            config: Optional Mem0Config for client initialization.
            custom_categories: Custom memory categories. Defaults to SHOWEASY_CATEGORIES.
            custom_instructions: Custom extraction instructions. Defaults to SHOWEASY_INSTRUCTIONS.
        """
        if memory:
            self._memory = memory
        else:
            self._memory = get_mem0_client(config)

        self._categories = custom_categories or SHOWEASY_CATEGORIES
        self._instructions = custom_instructions or SHOWEASY_INSTRUCTIONS

        logger.info(
            f"Mem0Service initialized with {len(self._categories)} custom categories"
        )

    @property
    def memory(self) -> Memory:
        """Get the underlying Memory client."""
        return self._memory

    @property
    def categories(self) -> List[Dict[str, str]]:
        """Get the configured custom categories."""
        return self._categories

    @property
    def instructions(self) -> str:
        """Get the configured custom instructions."""
        return self._instructions

    def add(
        self,
        messages: Union[str, List[Dict[str, str]]],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True,
    ) -> MemoryResult:
        """
        Add memories from messages or text.

        This method extracts and stores memories from the provided messages.
        By default, it uses LLM inference to extract relevant facts.

        Args:
            messages: Either a string or list of message dicts with 'role' and 'content'.
            user_id: User identifier for memory association.
            agent_id: Agent identifier for memory association.
            run_id: Run/session identifier for memory association.
            metadata: Additional metadata to attach to memories.
            infer: If True, use LLM to extract memories. If False, store raw messages.

        Returns:
            MemoryResult with added memory IDs and details.

        Example:
            # From conversation messages
            result = service.add(
                messages=[
                    {"role": "user", "content": "I prefer evening shows"},
                    {"role": "assistant", "content": "Noted! I'll prioritize evening events."}
                ],
                user_id="user123",
                metadata={"category": "preferences"}
            )

            # From plain text
            result = service.add(
                messages="User prefers classical music concerts",
                user_id="user123"
            )
        """
        try:
            logger.debug(
                f"Adding memory for user_id={user_id}, agent_id={agent_id}, "
                f"run_id={run_id}, infer={infer}"
            )

            result = self._memory.add(
                messages=messages,
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                metadata=metadata,
                infer=infer,
            )

            memory_count = len(result.get("results", [])) if isinstance(result, dict) else 0
            logger.info(f"Added {memory_count} memories for user_id={user_id}")

            return MemoryResult(
                success=True,
                data=result,
                message=f"Successfully added {memory_count} memories",
            )

        except Exception as e:
            logger.error(f"Failed to add memory: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message="Failed to add memory",
            )

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
    ) -> MemoryResult:
        """
        Search memories using semantic similarity.

        Args:
            query: Natural language search query.
            user_id: Filter by user identifier.
            agent_id: Filter by agent identifier.
            run_id: Filter by run/session identifier.
            limit: Maximum number of results to return.
            filters: Additional filters (e.g., {"category": "preferences"}).
            threshold: Minimum similarity threshold (0-1).

        Returns:
            MemoryResult with matching memories.

        Example:
            # Search user's event preferences
            result = service.search(
                query="What kind of events does the user like?",
                user_id="user123",
                limit=5
            )

            # Search with category filter
            result = service.search(
                query="booking history",
                user_id="user123",
                filters={"category": "booking_history"}
            )
        """
        try:
            logger.debug(
                f"Searching memories: query='{query[:50]}...', "
                f"user_id={user_id}, limit={limit}"
            )

            result = self._memory.search(
                query=query,
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                limit=limit,
                filters=filters,
                threshold=threshold,
            )

            memory_count = len(result.get("results", [])) if isinstance(result, dict) else len(result)
            logger.info(f"Found {memory_count} memories matching query")

            return MemoryResult(
                success=True,
                data=result,
                message=f"Found {memory_count} matching memories",
            )

        except Exception as e:
            logger.error(f"Failed to search memories: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message="Failed to search memories",
            )

    def get_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> MemoryResult:
        """
        Retrieve all memories for a given scope.

        Args:
            user_id: Filter by user identifier.
            agent_id: Filter by agent identifier.
            run_id: Filter by run/session identifier.
            filters: Additional filters.

        Returns:
            MemoryResult with all matching memories.

        Example:
            # Get all memories for a user
            result = service.get_all(user_id="user123")

            # Get memories for a specific session
            result = service.get_all(user_id="user123", run_id="session456")
        """
        try:
            logger.debug(
                f"Getting all memories: user_id={user_id}, "
                f"agent_id={agent_id}, run_id={run_id}"
            )

            result = self._memory.get_all(
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                filters=filters,
            )

            memory_count = len(result.get("results", [])) if isinstance(result, dict) else len(result)
            logger.info(f"Retrieved {memory_count} memories")

            return MemoryResult(
                success=True,
                data=result,
                message=f"Retrieved {memory_count} memories",
            )

        except Exception as e:
            logger.error(f"Failed to get memories: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message="Failed to retrieve memories",
            )

    def get(self, memory_id: str) -> MemoryResult:
        """
        Get a specific memory by ID.

        Args:
            memory_id: Unique identifier of the memory.

        Returns:
            MemoryResult with the memory data.

        Example:
            result = service.get(memory_id="mem_abc123")
        """
        try:
            logger.debug(f"Getting memory: memory_id={memory_id}")

            result = self._memory.get(memory_id=memory_id)

            logger.info(f"Retrieved memory {memory_id}")

            return MemoryResult(
                success=True,
                data=result,
                message=f"Retrieved memory {memory_id}",
            )

        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message=f"Failed to retrieve memory {memory_id}",
            )

    def update(
        self,
        memory_id: str,
        data: str,
    ) -> MemoryResult:
        """
        Update an existing memory.

        Args:
            memory_id: Unique identifier of the memory to update.
            data: New content for the memory.

        Returns:
            MemoryResult with update confirmation.

        Example:
            result = service.update(
                memory_id="mem_abc123",
                data="User prefers jazz and classical concerts"
            )
        """
        try:
            logger.debug(f"Updating memory: memory_id={memory_id}")

            result = self._memory.update(memory_id=memory_id, data=data)

            logger.info(f"Updated memory {memory_id}")

            return MemoryResult(
                success=True,
                data=result,
                message=f"Successfully updated memory {memory_id}",
            )

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message=f"Failed to update memory {memory_id}",
            )

    def delete(self, memory_id: str) -> MemoryResult:
        """
        Delete a specific memory.

        Args:
            memory_id: Unique identifier of the memory to delete.

        Returns:
            MemoryResult with deletion confirmation.

        Example:
            result = service.delete(memory_id="mem_abc123")
        """
        try:
            logger.debug(f"Deleting memory: memory_id={memory_id}")

            result = self._memory.delete(memory_id=memory_id)

            logger.info(f"Deleted memory {memory_id}")

            return MemoryResult(
                success=True,
                data=result,
                message=f"Successfully deleted memory {memory_id}",
            )

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message=f"Failed to delete memory {memory_id}",
            )

    def delete_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> MemoryResult:
        """
        Delete all memories for a given scope.

        WARNING: This operation is irreversible.

        Args:
            user_id: Delete all memories for this user.
            agent_id: Delete all memories for this agent.
            run_id: Delete all memories for this run/session.

        Returns:
            MemoryResult with deletion confirmation.

        Example:
            # Delete all memories for a user
            result = service.delete_all(user_id="user123")

            # Delete memories for a specific session
            result = service.delete_all(user_id="user123", run_id="session456")
        """
        try:
            logger.warning(
                f"Deleting all memories: user_id={user_id}, "
                f"agent_id={agent_id}, run_id={run_id}"
            )

            result = self._memory.delete_all(
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
            )

            logger.info("Deleted all memories for the specified scope")

            return MemoryResult(
                success=True,
                data=result,
                message="Successfully deleted all memories",
            )

        except Exception as e:
            logger.error(f"Failed to delete all memories: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message="Failed to delete all memories",
            )

    def history(self, memory_id: str) -> MemoryResult:
        """
        Get the change history for a specific memory.

        Args:
            memory_id: Unique identifier of the memory.

        Returns:
            MemoryResult with the memory's change history.

        Example:
            result = service.history(memory_id="mem_abc123")
        """
        try:
            logger.debug(f"Getting history for memory: memory_id={memory_id}")

            result = self._memory.history(memory_id=memory_id)

            history_count = len(result) if isinstance(result, list) else 0
            logger.info(f"Retrieved {history_count} history entries for memory {memory_id}")

            return MemoryResult(
                success=True,
                data=result,
                message=f"Retrieved {history_count} history entries",
            )

        except Exception as e:
            logger.error(f"Failed to get history for {memory_id}: {e}", exc_info=True)
            return MemoryResult(
                success=False,
                error=str(e),
                message=f"Failed to retrieve history for memory {memory_id}",
            )

    def add_conversation(
        self,
        user_message: str,
        assistant_message: str,
        user_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryResult:
        """
        Convenience method to add a conversation turn as memory.

        This is a helper method that formats user and assistant messages
        into the expected format and adds them as memory.

        Args:
            user_message: The user's message.
            assistant_message: The assistant's response.
            user_id: User identifier.
            session_id: Optional session identifier (maps to run_id).
            metadata: Additional metadata.

        Returns:
            MemoryResult with added memory details.

        Example:
            result = service.add_conversation(
                user_message="I want to book tickets for a jazz concert",
                assistant_message="I found several jazz concerts. Do you have a preferred date?",
                user_id="user123",
                session_id="session456"
            )
        """
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ]

        return self.add(
            messages=messages,
            user_id=user_id,
            run_id=session_id,
            metadata=metadata,
        )

    def get_user_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """
        Get formatted user context for use in prompts.

        This method retrieves relevant memories and formats them into
        a string suitable for including in LLM prompts.

        Args:
            user_id: User identifier.
            query: Optional query to search for specific context.
            limit: Maximum number of memories to include.

        Returns:
            Formatted string of user context.

        Example:
            context = service.get_user_context(
                user_id="user123",
                query="event preferences"
            )
            # Returns something like:
            # "User Context:
            # - Prefers jazz and classical concerts
            # - Usually books for 2 people
            # - Likes evening shows"
        """
        if query:
            result = self.search(query=query, user_id=user_id, limit=limit)
        else:
            result = self.get_all(user_id=user_id)

        if not result.success or not result.data:
            return ""

        memories = result.data.get("results", []) if isinstance(result.data, dict) else result.data

        if not memories:
            return ""

        context_lines = ["User Context:"]
        for memory in memories[:limit]:
            if isinstance(memory, dict):
                memory_text = memory.get("memory", memory.get("text", ""))
            else:
                memory_text = str(memory)

            if memory_text:
                context_lines.append(f"- {memory_text}")

        return "\n".join(context_lines)
