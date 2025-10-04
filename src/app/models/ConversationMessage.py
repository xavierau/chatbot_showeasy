from pydantic import BaseModel

class ConversationMessage(BaseModel):
    content: str
    role: str