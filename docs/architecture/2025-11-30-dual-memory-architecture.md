# Dual Memory Architecture: Short-Term + Long-Term Memory

**Date:** 2025-11-30
**Status:** Implemented
**Author:** Claude Code

## Overview

The ConversationOrchestrator uses a dual-memory architecture combining:
1. **Short-Term Memory**: File-based conversation history (per session)
2. **Long-Term Memory**: Mem0 semantic memory (per user, cross-session)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Layer (main.py)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐    │
│  │   Short-Term Memory         │    │   Long-Term Memory          │    │
│  │   (FileMemoryService)       │    │   (Mem0Service)             │    │
│  ├─────────────────────────────┤    ├─────────────────────────────┤    │
│  │ • Session-based             │    │ • User-based                │    │
│  │ • JSONL file per session    │    │ • Vector store (semantic)   │    │
│  │ • Sliding window (10 rounds)│    │ • Cross-session persistence │    │
│  │ • Full conversation context │    │ • Preferences & patterns    │    │
│  └──────────────┬──────────────┘    └──────────────┬──────────────┘    │
│                 │                                   │                   │
│                 │ previous_conversation             │ user_id           │
│                 │ (dspy.History)                    │                   │
│                 ▼                                   ▼                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  ConversationOrchestrator                        │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │ _get_user_context(user_id, user_message)                  │  │   │
│  │  │   → Semantic search in Mem0 using current message         │  │   │
│  │  │   → Returns formatted user preferences                    │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                              │                                   │   │
│  │                              ▼                                   │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │                    ReAct Agent                             │  │   │
│  │  │  Inputs:                                                   │  │   │
│  │  │   • question (current user message)                        │  │   │
│  │  │   • previous_conversation (SHORT-TERM: last 10 rounds)     │  │   │
│  │  │   • page_context (current page)                            │  │   │
│  │  │   • user_context (LONG-TERM: preferences from Mem0)        │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Post-Response Updates                         │   │
│  │  1. Append to short-term: memory_manager.update_memory()        │   │
│  │  2. Add to long-term: mem0_service.add_conversation()           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Memory Types Comparison

| Aspect | Short-Term Memory | Long-Term Memory |
|--------|-------------------|------------------|
| **Service** | `FileMemoryService` | `Mem0Service` |
| **Storage** | JSONL file per session | Vector store (Qdrant/etc.) |
| **Scope** | Single session | Cross-session (per user) |
| **Retention** | Session lifetime | Persistent |
| **Retrieval** | Sequential (last N rounds) | Semantic search |
| **Content** | Full messages | Extracted facts/preferences |
| **Parameter** | `previous_conversation` | `user_context` |
| **Default Limit** | 10 rounds (20 messages) | 5 memories |

## Data Flow

### Request Flow (Reading Memory)

```python
# 1. Short-term: Get conversation history from file
previous_conversation = memory_manager.get_memory(session_id)  # Last 10 rounds

# 2. Long-term: Retrieved inside orchestrator
user_context = self._get_user_context(user_id, user_message)
# Returns: "User Context:\n- Prefers jazz concerts\n- Usually books 2 tickets"

# 3. Both passed to ReAct agent
agent_prediction = self.agent(
    question=user_message,
    previous_conversation=previous_conversation,  # SHORT-TERM
    user_context=user_context                      # LONG-TERM
)
```

### Response Flow (Writing Memory)

```python
# 1. Update short-term (append to file)
new_messages = previous_conversation.messages + [user_msg, assistant_msg]
memory_manager.update_memory(session_id, dspy.History(messages=new_messages))

# 2. Update long-term (Mem0 extracts and stores preferences)
mem0_service.add_conversation(
    user_message=request.user_input,
    assistant_message=response_content,
    user_id=user_id,
    session_id=session_id
)
```

## Sliding Window Implementation

The short-term memory uses a sliding window to limit context size:

```python
# FileMemoryService.get_memory()
def get_memory(self, session_id: str, rounds: int = 10) -> dspy.History:
    # ... load all messages from file ...

    # Apply sliding window - each round = 2 messages (user + assistant)
    limit = rounds * 2
    if limit > 0 and len(messages) > limit:
        messages = messages[-limit:]  # Keep most recent

    return dspy.History(messages=history_messages)
```

**Example:**
- Conversation with 50 rounds (100 messages)
- `get_memory(session_id)` → returns rounds 41-50 (20 messages)
- `get_memory(session_id, rounds=5)` → returns rounds 46-50 (10 messages)

## Package Structure

```
src/app/services/memory/
├── __init__.py              # Package exports
├── memory_interface.py      # Abstract interface (MemoryService)
├── file_memory_service.py   # Concrete implementation (FileMemoryService)
└── memory_manager.py        # Facade (MemoryManager)

src/app/services/mem0/
├── __init__.py              # Package exports
├── client.py                # Mem0 client factory
├── service.py               # Mem0Service implementation
└── categories.py            # ShowEasy-specific memory categories
```

## Design Patterns Applied

1. **Strategy Pattern**: `MemoryService` interface allows swapping implementations
2. **Facade Pattern**: `MemoryManager` simplifies memory operations
3. **Dependency Injection**: Services injected into orchestrator
4. **Repository Pattern**: Abstracts data access operations
5. **Graceful Degradation**: System works without Mem0 (returns empty context)

## Configuration

### Environment Variables

```bash
# Mem0 Long-Term Memory
MEM0_ENABLED=true                    # Enable/disable Mem0
MEM0_PROVIDER=qdrant                 # Vector store provider

# Short-term memory uses default file storage
# Location: memory_storage/{session_id}.jsonl
```

## Graceful Degradation

The system continues to function if Mem0 is unavailable:

```python
def _get_user_context(self, user_id: Optional[str], user_message: str) -> str:
    if not self.mem0_service or not user_id:
        return ""  # Empty context - agent works without personalization

    try:
        return self.mem0_service.get_user_context(user_id, query=user_message)
    except Exception as e:
        logger.warning(f"[Mem0] Failed to retrieve user context: {e}")
        return ""  # Graceful degradation
```

## Future Enhancements

1. **Redis-based short-term memory**: For horizontal scaling
2. **Memory summarization**: Compress old conversations before archiving
3. **Memory decay**: Reduce weight of old long-term memories
4. **Explicit memory commands**: Let users say "remember that I prefer..."

## Related Files

- `src/app/llm/modules/ConversationOrchestrator.py` - Main orchestrator
- `src/app/llm/signatures/ConversationSignature.py` - Agent signature with `user_context`
- `src/app/services/memory/` - Short-term memory package
- `src/app/services/mem0/` - Long-term memory package
- `src/app/api/main.py` - API layer wiring
