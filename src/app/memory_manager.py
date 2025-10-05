import os
import json
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List
import dspy

class Message(BaseModel):
    role: str
    content: str

class MemoryService(ABC):
    @abstractmethod
    def get_memory(self, session_id: str) -> dspy.History:
        pass

    @abstractmethod
    def update_memory(self, session_id: str, messages: dspy.History):
        pass

class FileMemoryService(MemoryService):
    def __init__(self, storage_path: str = "memory_storage"):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def get_memory(self, session_id: str) -> dspy.History:
        file_path = os.path.join(self.storage_path, f"{session_id}.jsonl")
        messages: List[Message] = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        messages.append(Message(**data))

        # Convert List[Message] to dspy.History
        history_messages = []
        for msg in messages:
            history_messages.append({"role": msg.role, "content": msg.content})

        # Return proper dspy.History object
        return dspy.History(messages=history_messages)

    def update_memory(self, session_id: str, messages: dspy.History):
        file_path = os.path.join(self.storage_path, f"{session_id}.jsonl")
        with open(file_path, "w") as f:
            # dspy.History has a messages attribute
            for message in messages.messages:
                # Convert dict from dspy.History to Message for serialization
                msg = Message(role=message["role"], content=message["content"])
                f.write(msg.model_dump_json() + "\n")

class MemoryManager:
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    def get_memory(self, session_id: str) -> dspy.History:
        return self.memory_service.get_memory(session_id)

    def update_memory(self, session_id: str, messages: dspy.History):
        self.memory_service.update_memory(session_id, messages)
