#!/usr/bin/env python
"""
Test script to verify the signature fix prevents infinite loop.
"""
import os
import sys

# Set PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import dspy
from app.llm.modules import ConversationOrchestrator
from app.models import ConversationMessage

# Configure DSPy with Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable not set")
    sys.exit(1)

# Configure LM
lm = dspy.LM(
    'google/gemini-2.5-flash',
    api_key=GOOGLE_API_KEY,
    max_tokens=8096
)
dspy.configure(lm=lm)

print("Testing ReAct agent with membership query...")
print("=" * 60)

orchestrator = ConversationOrchestrator()
result = orchestrator(
    user_message='會員優惠係咩？',
    previous_conversation=[]
)

# Analyze trajectory
print("\n[TRAJECTORY ANALYSIS]")
print("-" * 60)
tool_calls = [k for k in result.trajectory.keys() if 'tool_name' in k]
print(f"Total tool calls: {len(tool_calls)}")
print()

# Check for finish tool
finish_found = False
for i, k in enumerate(tool_calls):
    tool_name = result.trajectory[k]
    thought_key = f'thought_{i}'
    thought = result.trajectory.get(thought_key, 'N/A')

    print(f"[{i}] Tool: {tool_name}")
    print(f"    Thought: {thought[:80]}...")

    if tool_name == 'finish':
        finish_found = True
        print(f"    ✅ FINISH TOOL CALLED (iteration {i})")
    print()

# Success criteria
print("\n[EVALUATION]")
print("-" * 60)
print(f"✅ Tool calls: {len(tool_calls)} (success if ≤ 3)" if len(tool_calls) <= 3 else f"❌ Tool calls: {len(tool_calls)} (expected ≤ 3)")
print(f"✅ Finish tool called" if finish_found else "❌ Finish tool NOT called")
print(f"✅ No redundant document_summary calls" if len([k for k in tool_calls if result.trajectory[k] == 'document_summary']) <= 1 else "❌ Multiple document_summary calls detected")

print("\n[AGENT RESPONSE]")
print("-" * 60)
print(result.answer[:300] + "..." if len(result.answer) > 300 else result.answer)

# Exit with appropriate code
if len(tool_calls) <= 3 and finish_found:
    print("\n✅ TEST PASSED")
    sys.exit(0)
else:
    print("\n❌ TEST FAILED")
    sys.exit(1)
