# ConversationOrchestrator Usage Examples

This document provides practical examples of using the refactored ConversationOrchestrator with the new 3-step ReAct architecture.

## Basic Setup

```python
from app.llm.modules.ConversationOrchestrator import ConversationOrchestrator
from app.models import ConversationMessage

# Initialize the orchestrator
orchestrator = ConversationOrchestrator()

# Prepare conversation history (if any)
previous_conversation = []
```

## Example 1: Event Search Query

```python
# User wants to find events
user_message = "I'm looking for jazz concerts in San Francisco this weekend"
page_context = "home_page"

response = orchestrator(
    user_message=user_message,
    previous_conversation=previous_conversation,
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: User wants event search for jazz concerts
# 2. Call: SearchEvent(query="jazz concerts", location="San Francisco", date="this weekend")
# 3. Return: Formatted list of jazz concerts with URLs and membership mentions
```

## Example 2: Membership Inquiry

```python
# User asks about membership
user_message = "What benefits do I get with premium membership?"
page_context = "membership_page"

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: User wants membership benefits information
# 2. Call: MembershipInfo(query_type="benefits")
# 3. Return: Detailed list of membership benefits
```

## Example 3: Ticket Refund Question

```python
# User needs refund information
user_message = "How do I get a refund for my ticket?"
page_context = "my_tickets_page"

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: User needs ticket refund policy
# 2. Call: TicketInfo(topic="refund")
# 3. Return: Clear refund policy with steps and deadlines
```

## Example 4: Multi-Turn Conversation

```python
# Turn 1: Initial event search
conv = []
user_msg1 = "Show me music concerts"

response1 = orchestrator(
    user_message=user_msg1,
    previous_conversation=conv,
    page_context=""
)
print(f"Bot: {response1}")

# Update conversation history
conv.append(ConversationMessage(role="user", content=user_msg1))
conv.append(ConversationMessage(role="assistant", content=response1))

# Turn 2: Follow-up with location
user_msg2 = "Any in New York?"

response2 = orchestrator(
    user_message=user_msg2,
    previous_conversation=conv,
    page_context=""
)
print(f"Bot: {response2}")

# Expected: ReAct agent will:
# 1. Reason: User is following up on previous music concert search
# 2. Call: SearchEvent(query="music concerts", location="New York")
# 3. Return: Music concerts in New York with context from previous query
```

## Example 5: Ambiguous Query Handling

```python
# User query is too vague
user_message = "events"
page_context = ""

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: Query too vague, need clarification
# 2. Call: AskClarification(
#       reason="query too vague",
#       suggested_question="What type of events are you interested in? For example, concerts, sports, theater, or festivals?"
#    )
# 3. Return: Clarifying question to help user be more specific
```

## Example 6: Platform Help Request

```python
# User needs help with account
user_message = "How do I update my payment method?"
page_context = "account_page"

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: User needs account management help
# 2. Call: GeneralHelp(category="account")
# 3. Return: Instructions for account management including payment methods
```

## Example 7: Greeting

```python
# User greets the agent
user_message = "Hi there!"
page_context = ""

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: This is a greeting, no tools needed
# 2. Call: None
# 3. Return: Warm greeting and offer to help
```

## Example 8: Multi-Intent Query

```python
# User has multiple questions
user_message = "I want to find rock concerts in LA, and also how much is membership?"
page_context = ""

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: User has two questions - event search + membership
# 2. Call: SearchEvent(query="rock concerts", location="Los Angeles")
# 3. Call: MembershipInfo(query_type="pricing")
# 4. Return: Combined response with rock concerts AND membership pricing
```

## Example 9: Multilingual Support

```python
# User asks in Chinese
user_message = "我想找音樂會"
page_context = ""

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: User wants music concerts, query in Chinese
# 2. Translate: "音樂會" → "music concerts" for SearchEvent
# 3. Call: SearchEvent(query="music concerts")
# 4. Return: Response in Chinese with music concert recommendations
```

## Example 10: Error Handling

```python
# Simulate guardrail violation (out of scope)
user_message = "What's the weather like today?"
page_context = ""

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected:
# 1. PreGuardrails: Detects out-of-scope query
# 2. Return: Friendly redirect message without reaching ReAct agent
# Example: "I'm here to help you find amazing events and manage your tickets!
#           For weather information, I'd recommend checking a weather service.
#           How can I help you with events today?"
```

## Example 11: Context-Aware Response

```python
# User is on event detail page
user_message = "How do I buy tickets?"
page_context = "event_detail_page"

response = orchestrator(
    user_message=user_message,
    previous_conversation=[],
    page_context=page_context
)

print(response)
# Expected: ReAct agent will:
# 1. Reason: User on event detail page, wants purchase help
# 2. Call: TicketInfo(topic="purchase", event_context="event_detail_page")
# 3. Return: Contextual instructions for buying tickets for the current event
```

## Example 12: Complex Multi-Step Conversation

```python
# Full conversation flow
conv = []

# Step 1: User searches for events
msg1 = "Show me tech events"
resp1 = orchestrator(msg1, conv, "")
print(f"User: {msg1}")
print(f"Bot: {resp1}\n")
conv.extend([
    ConversationMessage(role="user", content=msg1),
    ConversationMessage(role="assistant", content=resp1)
])

# Step 2: User asks about membership
msg2 = "Do I get discounts with membership?"
resp2 = orchestrator(msg2, conv, "")
print(f"User: {msg2}")
print(f"Bot: {resp2}\n")
conv.extend([
    ConversationMessage(role="user", content=msg2),
    ConversationMessage(role="assistant", content=resp2)
])

# Step 3: User wants to know pricing
msg3 = "How much does it cost?"
resp3 = orchestrator(msg3, conv, "")
print(f"User: {msg3}")
print(f"Bot: {resp3}\n")
conv.extend([
    ConversationMessage(role="user", content=msg3),
    ConversationMessage(role="assistant", content=resp3)
])

# Step 4: User decides to purchase
msg4 = "How do I sign up?"
resp4 = orchestrator(msg4, conv, "")
print(f"User: {msg4}")
print(f"Bot: {resp4}\n")

# Expected flow:
# Step 1: SearchEvent for tech events
# Step 2: MembershipInfo about benefits (maintains context from step 1)
# Step 3: MembershipInfo with pricing (knows we're talking about membership from step 2)
# Step 4: MembershipInfo with upgrade instructions (completes the journey)
```

## Testing Individual Tools

For development and testing, you can also test tools directly:

```python
from app.llm.tools import (
    SearchEvent,
    MembershipInfo,
    TicketInfo,
    GeneralHelp,
    AskClarification
)

# Test SearchEvent
result = SearchEvent.func(query="jazz concerts", location="San Francisco")
print(result["events"])

# Test MembershipInfo
result = MembershipInfo.func(query_type="pricing")
print(result["info"])

# Test TicketInfo
result = TicketInfo.func(topic="refund")
print(result["info"])

# Test GeneralHelp
result = GeneralHelp.func(category="account")
print(result["info"])

# Test AskClarification
result = AskClarification.func(
    reason="query too vague",
    suggested_question="What type of events are you looking for?"
)
print(result["clarification"])
```

## Monitoring and Debugging

```python
# Enable verbose logging to see ReAct reasoning
import logging
logging.basicConfig(level=logging.DEBUG)

orchestrator = ConversationOrchestrator()

response = orchestrator(
    user_message="Find concerts",
    previous_conversation=[],
    page_context=""
)

# Check the console output for:
# [PreGuardrail] - Input validation results
# [ReAct Agent] - Tool calls and reasoning
# [PostGuardrail] - Output validation results
```

## Performance Monitoring

```python
import time

# Measure response time
start = time.time()
response = orchestrator(
    user_message="What are the membership benefits?",
    previous_conversation=[],
    page_context=""
)
elapsed = time.time() - start

print(f"Response generated in {elapsed:.2f} seconds")
print(f"Response: {response}")

# Track tool usage (if using ReAct trajectory)
# orchestrator.agent will have trajectory attribute showing tool calls
```

## Best Practices

1. **Always provide conversation history** for multi-turn conversations
2. **Include page_context** when relevant for contextual responses
3. **Handle errors gracefully** - the orchestrator returns meaningful fallbacks
4. **Monitor guardrail violations** to improve input/output quality
5. **Log tool usage** to understand which tools are most valuable
6. **Test edge cases** like empty queries, very long queries, multilingual input

## Common Patterns

### Pattern 1: Event Discovery Flow
```
User: General interest → SearchEvent (broad results)
User: Refinement → SearchEvent (filtered results)
User: Membership question → MembershipInfo (benefits)
```

### Pattern 2: Ticket Purchase Flow
```
User: Find events → SearchEvent
User: How to buy → TicketInfo (purchase)
User: Refund policy → TicketInfo (refund)
User: Membership benefits → MembershipInfo
```

### Pattern 3: Help & Support Flow
```
User: Account question → GeneralHelp
User: Ticket question → TicketInfo
User: Membership question → MembershipInfo
```

## Troubleshooting

### Issue: ReAct agent not calling expected tool
**Solution:** Check ConversationSignature instructions - may need to clarify when to use each tool

### Issue: Response in wrong language
**Solution:** Ensure ConversationSignature language instruction is clear

### Issue: Guardrail violations
**Solution:** Review PreGuardrails configuration and adjust thresholds

### Issue: Missing conversation context
**Solution:** Ensure previous_conversation is properly formatted as list[ConversationMessage]

---

For more details, see:
- Architecture: `/Users/xavierau/Code/python/showeasy_chatbot/REFACTORING_NOTES.md`
- Summary: `/Users/xavierau/Code/python/showeasy_chatbot/REFACTORING_SUMMARY.md`
- Validation: `python scripts/validate_refactoring.py`
