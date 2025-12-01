# Mem0 Long-Term Memory Integration Architecture

**Date:** 2025-11-28
**Status:** Design Document
**Author:** Claude Code

## Overview

This document describes the architecture for integrating Mem0 as a long-term memory and personalization engine into the ShowEasy chatbot. The existing round-to-round conversation history (stored in file-based `MemoryManager`) serves as **short-term memory**, while Mem0 provides **long-term memory** for user preferences, patterns, and personalization across sessions.

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Memory Architecture                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐    ┌─────────────────────────────────────┐ │
│  │   Short-Term Memory │    │        Long-Term Memory (Mem0)      │ │
│  │  (Conversation Hx)  │    │                                     │ │
│  ├─────────────────────┤    ├─────────────────────────────────────┤ │
│  │ • Current session   │    │ • User preferences                  │ │
│  │ • dspy.History      │    │ • Behavioral patterns               │ │
│  │ • File-based JSONL  │    │ • Cross-session insights            │ │
│  │ • Per-session scope │    │ • Semantic search enabled           │ │
│  │ • Context window    │    │ • Vector store backed               │ │
│  └─────────────────────┘    └─────────────────────────────────────┘ │
│           │                              │                          │
│           └──────────────┬───────────────┘                          │
│                          │                                          │
│                          ▼                                          │
│           ┌─────────────────────────────┐                           │
│           │   ConversationOrchestrator  │                           │
│           │                             │                           │
│           │ • Receives both memories    │                           │
│           │ • Short-term: full context  │                           │
│           │ • Long-term: user profile   │                           │
│           └─────────────────────────────┘                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Request Flow (Reading Memories)

```
1. API Endpoint receives request
   ├── Load short-term memory (conversation history)
   │   └── memory_manager.get_memory(session_id)
   │
   └── Load long-term memory context (Mem0)
       └── mem0_service.get_user_context(user_id, query)
           │
           └── Returns formatted string:
               "User Context:
                - Prefers jazz concerts
                - Usually books 2 tickets
                - Likes evening shows"

2. ConversationOrchestrator.forward()
   ├── Receives: user_message, previous_conversation, user_context
   │
   ├── Pre-Guardrails (unchanged)
   │
   ├── ReAct Agent
   │   └── user_context injected into prompt
   │       "Based on what I know about you: [user_context]"
   │
   └── Post-Guardrails (unchanged)

3. Return response to user
```

### Response Flow (Writing Memories)

```
1. After successful response generation

2. Update short-term memory (immediate)
   └── memory_manager.update_memory(session_id, new_conversation)

3. Update long-term memory (async/background)
   └── mem0_service.add_conversation(
           user_message=request.message,
           assistant_message=response_content,
           user_id=user_id,
           session_id=session_id
       )
       │
       └── Mem0 extracts preferences/patterns automatically:
           • "User interested in jazz concerts"
           • "Prefers evening shows"
           • "Books for 2 people"
```

## Integration Points

### 1. ConversationOrchestrator Changes

**File:** `src/app/llm/modules/ConversationOrchestrator.py`

```python
class ConversationOrchestrator(dspy.Module):
    def __init__(
        self,
        ab_config: Optional[ABTestConfig] = None,
        mem0_service: Optional[Mem0Service] = None  # NEW
    ):
        # ... existing init ...
        self.mem0_service = mem0_service

    def forward(
        self,
        user_message: str,
        previous_conversation: list[ConversationMessage],
        page_context: str = "",
        user_id: Optional[str] = None  # NEW - for Mem0 lookup
    ) -> dspy.Prediction:
        # Get user context from long-term memory
        user_context = ""
        if self.mem0_service and user_id:
            user_context = self.mem0_service.get_user_context(
                user_id=user_id,
                query=user_message,  # Semantic search based on current query
                limit=5
            )

        # Pass to agent with enriched context
        agent_prediction = self.agent(
            question=user_message,
            previous_conversation=previous_conversation,
            page_context=page_context,
            user_context=user_context  # NEW
        )
```

### 2. ConversationSignature Changes

**File:** `src/app/llm/signatures/ConversationSignature.py`

```python
class ConversationSignature(dspy.Signature):
    """Signature for conversation with user context."""

    question: str = dspy.InputField(desc="User's question or request")
    previous_conversation: list[ConversationMessage] = dspy.InputField(
        desc="Previous conversation history"
    )
    page_context: str = dspy.InputField(desc="Current page context", default="")
    user_context: str = dspy.InputField(  # NEW
        desc="Long-term user preferences and patterns from memory",
        default=""
    )
    answer: str = dspy.OutputField(desc="Agent's response")
```

### 3. API Layer Changes

**File:** `src/app/api/main.py`

```python
from ..services.mem0 import Mem0Service

# Initialize Mem0 service (singleton)
mem0_service: Optional[Mem0Service] = None

def get_mem0_service() -> Optional[Mem0Service]:
    """Lazy initialization of Mem0 service."""
    global mem0_service
    if mem0_service is None:
        try:
            mem0_service = Mem0Service()
            logger.info("Mem0 service initialized successfully")
        except Exception as e:
            logger.warning(f"Mem0 service unavailable: {e}")
            mem0_service = None
    return mem0_service

@app.post("/api/message")
def receive_message(request: MessageRequest):
    # ... existing code ...

    # Initialize orchestrator with Mem0
    orchestrator = ConversationOrchestrator(
        ab_config=ab_config,
        mem0_service=get_mem0_service()
    )

    # Process message
    prediction = orchestrator(
        user_message=request.message,
        previous_conversation=previous_conversation,
        page_context=None,
        user_id=user_id  # Pass for Mem0 lookup
    )

    response_content = prediction.answer

    # Update short-term memory (existing)
    # ...

    # Update long-term memory (NEW)
    mem0 = get_mem0_service()
    if mem0:
        mem0.add_conversation(
            user_message=request.message,
            assistant_message=response_content,
            user_id=user_id,
            session_id=session_id
        )
```

## Categories for ShowEasy Domain

The Mem0 integration uses custom categories defined in `src/app/services/mem0/categories.py`:

| Category | Description | Example |
|----------|-------------|---------|
| `event_preferences` | Favorite genres, venues, formats | "Loves jazz concerts at Cultural Centre" |
| `booking_patterns` | Booking behavior (NOT records) | "Usually books 2 tickets, prefers front rows" |
| `membership_preferences` | Membership interests (NOT data) | "Interested in premium membership benefits" |
| `personal_preferences` | Accessibility, language, dietary | "Needs wheelchair access" |
| `location_preferences` | Preferred areas, travel willingness | "Prefers events in Central/TST" |
| `budget_preferences` | Spending range, discount interests | "Usually spends $500-1000 per event" |
| `companion_info` | Who they attend with | "Often attends with spouse" |
| `feedback_history` | Satisfaction, suggestions | "Had great experience at last concert" |

**Important:** Transactional data (actual bookings, membership tiers, points) is fetched from the database via tools (TicketInfo, MembershipInfo), NOT stored in Mem0.

## Configuration

### Environment Variables

```bash
# Mem0 LLM Configuration
MEM0_LLM_PROVIDER=gemini           # Match main chatbot LLM
MEM0_LLM_MODEL=gemini-2.5-flash    # Or gpt-4o-mini for OpenAI
MEM0_LLM_TEMPERATURE=0.1
MEM0_LLM_MAX_TOKENS=2000

# Mem0 Embedder Configuration
MEM0_EMBEDDER_PROVIDER=openai      # For high-quality embeddings
MEM0_EMBEDDER_MODEL=text-embedding-3-small
MEM0_EMBEDDER_API_KEY=your-key

# Mem0 Vector Store Configuration
MEM0_VECTOR_STORE_PROVIDER=chroma  # Local, no setup required
MEM0_VECTOR_STORE_PATH=./mem0_data # Persistent storage path
MEM0_VECTOR_STORE_COLLECTION=showeasy_memories

# Optional: Use Qdrant for production
# MEM0_VECTOR_STORE_PROVIDER=qdrant
# MEM0_VECTOR_STORE_HOST=localhost
# MEM0_VECTOR_STORE_PORT=6333
```

## Error Handling

Mem0 integration is designed to be **fail-safe**:

1. **Service unavailable**: If Mem0 fails to initialize, the chatbot continues without long-term memory
2. **Search failures**: Empty context is used if memory search fails
3. **Add failures**: Logged but don't block response delivery
4. **Graceful degradation**: System works with just short-term memory if needed

```python
# Example error handling
try:
    user_context = mem0_service.get_user_context(user_id)
except Exception as e:
    logger.warning(f"Mem0 context retrieval failed: {e}")
    user_context = ""  # Continue without personalization
```

## Performance Considerations

1. **Async Memory Updates**: Consider using background tasks for `mem0.add()` to avoid blocking response
2. **Context Limit**: Limit retrieved memories to 5-10 most relevant
3. **Cache User Context**: Consider caching user context for repeated queries in same session
4. **Vector Store**: Use Qdrant or Milvus for production (faster than Chroma for large datasets)

## Testing Strategy

1. **Unit Tests**: Test Mem0Service methods independently
2. **Integration Tests**: Test orchestrator with mocked Mem0Service
3. **E2E Tests**: Test full flow with actual Mem0 instance
4. **Fallback Tests**: Verify graceful degradation when Mem0 unavailable

## Rollout Plan

1. **Phase 1**: Add Mem0 service initialization and logging (no changes to flow)
2. **Phase 2**: Enable memory writes (add_conversation) after responses
3. **Phase 3**: Enable memory reads (user_context) in orchestrator
4. **Phase 4**: Monitor and tune extraction quality

## Related Documents

- [Booking Enquiry System](./2025-11-14-booking-enquiry-system.md)
- [Notification Strategy Pattern](./2025-11-14-notification-strategy-pattern.md)
- Mem0 Service: `src/app/services/mem0/service.py`
- Mem0 Categories: `src/app/services/mem0/categories.py`
