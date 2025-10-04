import os
import json
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List

class Message(BaseModel):
    role: str
    content: str

class MemoryService(ABC):
    @abstractmethod
    def get_memory(self, session_id: str) -> List[Message]:
        pass

    @abstractmethod
    def update_memory(self, session_id: str, messages: List[Message]):
        pass

class FileMemoryService(MemoryService):
    def __init__(self, storage_path: str = "memory_storage"):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def get_memory(self, session_id: str) -> List[Message]:
        file_path = os.path.join(self.storage_path, f"{session_id}.jsonl")
        messages: List[Message] = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        messages.append(Message(**data))
        return messages

    def update_memory(self, session_id: str, messages: List[Message]):
        file_path = os.path.join(self.storage_path, f"{session_id}.jsonl")
        with open(file_path, "w") as f:
            for message in messages:
                f.write(message.model_dump_json() + "\n")

class MemoryManager:
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    def get_memory(self, session_id: str) -> List[Message]:
        return self.memory_service.get_memory(session_id)

    def update_memory(self, session_id: str, messages: List[Message]):
        self.memory_service.update_memory(session_id, messages)
