"""
Mem0 Memory Service Package

This package provides a memory layer for AI interactions using Mem0.
It includes:
- Client factory for configuring and initializing Mem0
- Service abstraction for memory operations (add, search, get_all, update, delete)
- Custom categories and instructions for the ShowEasy chatbot domain
"""

from .client import get_mem0_client, Mem0Config
from .service import Mem0Service
from .categories import SHOWEASY_CATEGORIES, SHOWEASY_INSTRUCTIONS

__all__ = [
    "get_mem0_client",
    "Mem0Config",
    "Mem0Service",
    "SHOWEASY_CATEGORIES",
    "SHOWEASY_INSTRUCTIONS",
]
