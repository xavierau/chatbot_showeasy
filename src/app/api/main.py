from fastapi import FastAPI
import os
import dspy
from ..models.UserInputRequest import UserInputRequest, GetMessagesRequest
from ..llm.modules.ConversationOrchestrator import ConversationOrchestrator
from ..memory_manager import MemoryManager, FileMemoryService
from ..middleware.logging_middleware import LoggingMiddleware
from config import configure_llm, configure_logging
from ..utils.web_scraper import get_page_content
import json
import uuid
import re
import structlog
from langfuse import observe, get_client



configure_llm()
configure_logging()

langfuse = get_client()
app = FastAPI()
app.add_middleware(LoggingMiddleware)

logger = structlog.get_logger(__name__)

# Instantiate Memory Service and Manager
file_memory_service = FileMemoryService()
memory_manager = MemoryManager(memory_service=file_memory_service)


@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.post('/chat')
def chat(request: UserInputRequest):

    log = logger.bind(
        session_id=request.session_id,
        user_id=request.user_id,
        endpoint="/chat"
    )

    log.info("Chat request started", current_url=request.current_url)

    # Get previous conversation
    previous_conversation = memory_manager.get_memory(request.session_id)
    log.debug("Retrieved conversation history", message_count=len(previous_conversation.messages))

    page_context = ""
    if request.current_url:
        page_context = get_page_content(request.current_url)
        log.debug("Page context retrieved", context_length=len(page_context))



    @observe()
    def wrapper_function():
        orchestrator = ConversationOrchestrator()

        # Get response from orchestrator
        response_content = orchestrator(user_message=request.user_input,
                                        previous_conversation=previous_conversation,
                                        page_context=page_context)

        langfuse.update_current_trace(
            user_id=request.user_id,
            session_id=request.session_id,
        )

        return response_content

    response_content = wrapper_function()

    log.debug("Orchestrator response generated", response_length=len(response_content))

    # Create new messages in dspy.History format
    user_message = {"role": "user", "content": request.user_input}
    assistant_message = {"role": "assistant", "content": response_content}

    # Update conversation history with dspy.History
    new_messages = previous_conversation.messages + [user_message, assistant_message]
    new_conversation = dspy.History(messages=new_messages)
    memory_manager.update_memory(request.session_id, new_conversation)

    log.info("Chat request completed successfully")
    return {"message": response_content}
    
@app.post("/chat/messages")
def get_messages(request: GetMessagesRequest):
    log = logger.bind(session_id=request.session_id, endpoint="/chat/messages")
    log.info("Retrieving messages")

    history = memory_manager.get_memory(request.session_id)

    # Add UUID to each message dict
    messages_array = []
    for msg in history.messages:
        msg_dict = dict(msg)
        msg_dict['id'] = str(uuid.uuid4())
        messages_array.append(msg_dict)

    log.info("Messages retrieved successfully", message_count=len(messages_array))
    return {"messages": messages_array}

@app.get("/health")
def get_health():
    return {"status": "ok"}
