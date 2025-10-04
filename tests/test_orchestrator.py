import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app.llm.modules import ConversationOrchestrator
from app.models import ConversationMessage
from app.config import configure_llm


def main():
    """Main function to run the ConversationOrchestrator test."""
    # Configure the language model
    configure_llm()

    # Instantiate the orchestrator
    orchestrator = ConversationOrchestrator()

    # Simulate a conversation
    previous_conversation = [
        ConversationMessage(role="user", content="Hi there!"),
        ConversationMessage(
            role="assistant", content="Hello! How can I help you today?"
        ),
    ]

    # Test with a general question
    user_message = "What is ShowEasy?"
    response = orchestrator(
        user_message=user_message, previous_conversation=previous_conversation
    )
    print(f"User: {user_message}")
    print(f"Assistant: {response}")

    print("\n" + "-" * 20 + "\n")

    # Test with an event search query
    user_message = "Are there any 藝術 exibitions?"
    response = orchestrator(
        user_message=user_message, previous_conversation=previous_conversation
    )
    print(f"User: {user_message}")
    print(f"Assistant: {response}")

    # Simulate a conversation
    previous_conversation = [
            ConversationMessage(role="user", content="Hi there!"),
            ConversationMessage(
                role="assistant", content="Hello! How can I help you today?"
            ),
            ConversationMessage(role="user", content=user_message),
            ConversationMessage(role="assistant", content=response),
        ]
    user_message_1 = "Tell me more about the first event"
    response = orchestrator(
        user_message=user_message_1, previous_conversation=previous_conversation
    )
    print(f"User: {user_message}")
    print(f"Assistant: {response}")

if __name__ == "__main__":
    main()
