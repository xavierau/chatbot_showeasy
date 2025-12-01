"""
File-based Memory Service Implementation

This module provides a file-based implementation of the MemoryService interface.
Conversation history is stored as JSONL files (one per session).
"""

import os
import json
from typing import List
from pydantic import BaseModel
import dspy

from .memory_interface import MemoryService


class Message(BaseModel):
    """Message model for serialization."""
    role: str
    content: str


class FileMemoryService(MemoryService):
    """File-based implementation of conversation memory storage.

    Stores conversation history as JSONL files in a specified directory.
    Each session gets its own file named {session_id}.jsonl.

    Args:
        storage_path: Directory path for storing conversation files.
                     Defaults to "memory_storage".
    """

    def __init__(self, storage_path: str = "memory_storage"):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

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
        file_path = os.path.join(self.storage_path, f"{session_id}.jsonl")
        messages: List[Message] = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        messages.append(Message(**data))

        # Apply sliding window - each round = 2 messages (user + assistant)
        limit = rounds * 2
        if limit > 0 and len(messages) > limit:
            messages = messages[-limit:]

        # Convert List[Message] to dspy.History
        history_messages = []
        for msg in messages:
            history_messages.append({"role": msg.role, "content": msg.content})

        # Return proper dspy.History object
        return dspy.History(messages=history_messages)

    def update_memory(self, session_id: str, messages: dspy.History) -> None:
        """Update conversation history for a session.

        DEPRECATED: Use append_messages() instead for incremental updates.
        This method overwrites the entire conversation history.

        Args:
            session_id: Unique session identifier
            messages: dspy.History containing conversation messages
        """
        file_path = os.path.join(self.storage_path, f"{session_id}.jsonl")
        with open(file_path, "w") as f:
            # dspy.History has a messages attribute
            for message in messages.messages:
                # Convert dict from dspy.History to Message for serialization
                msg = Message(role=message["role"], content=message["content"])
                f.write(msg.model_dump_json() + "\n")

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
        file_path = os.path.join(self.storage_path, f"{session_id}.jsonl")
        with open(file_path, "a") as f:  # "a" = append mode
            for message_dict in messages:
                msg = Message(role=message_dict["role"], content=message_dict["content"])
                f.write(msg.model_dump_json() + "\n")
