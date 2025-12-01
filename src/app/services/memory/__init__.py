"""
Memory Service Package

This package provides memory management for conversation history.
It includes:
- MemoryService: Abstract interface for memory operations
- FileMemoryService: File-based implementation (JSONL storage)
- MemoryManager: Facade for simplified memory operations
"""

from .memory_interface import MemoryService
from .file_memory_service import FileMemoryService
from .memory_manager import MemoryManager

__all__ = [
    "MemoryService",
    "FileMemoryService",
    "MemoryManager",
]
