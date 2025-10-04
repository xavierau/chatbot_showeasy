from fastapi import FastAPI
import os
import dspy
from ..models.UserInputRequest import UserInputRequest, GetMessagesRequest
from ..llm.modules.ConversationOrchestrator import ConversationOrchestrator
from ..memory_manager import MemoryManager, FileMemoryService, Message
from config import configure_llm
from ..utils.web_scraper import get_page_content
import json
import uuid
import re

configure_llm()

app = FastAPI()

# Instantiate Memory Service and Manager
file_memory_service = FileMemoryService()
memory_manager = MemoryManager(memory_service=file_memory_service)

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.post('/chat')
def chat(request: UserInputRequest):
    # Get previous conversation
    previous_conversation = memory_manager.get_memory(request.session_id)
    
    page_context = ""
    if request.current_url:
        page_context = get_page_content(request.current_url)

        print("page_context:", page_context)

    orchestrator = ConversationOrchestrator()
    
    # Get response from orchestrator
    response_content = orchestrator(user_message=request.user_input, 
                                    previous_conversation=previous_conversation,
                                    page_context=page_context)

    # Create new messages
    user_message = Message(role="user", content=request.user_input)
    assistant_message = Message(role="assistant", content=response_content)

    # Update conversation history
    new_conversation = previous_conversation + [user_message, assistant_message]
    memory_manager.update_memory(request.session_id, new_conversation)
    
    return {"message": response_content}
    
@app.post("/chat/messages")
def get_messages(request: GetMessagesRequest):
    messages = memory_manager.get_memory(request.session_id)
    
    # Convert messages to a list of dicts and add a UUID
    messages_array = []
    for msg in messages:
        msg_dict = msg.model_dump()
        msg_dict['id'] = str(uuid.uuid4())
        messages_array.append(msg_dict)

    return {"messages": messages_array}

@app.get("/health")
def get_health():
    return {"status": "ok"}
