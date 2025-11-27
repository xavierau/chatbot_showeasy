from pydantic import BaseModel
from typing import Optional

class UserInputRequest(BaseModel):
    user_input: str
    user_id: Optional[int]
    session_id: str
    current_url: Optional[str]
    page_content: Optional[str]

class GetMessagesRequest(BaseModel):
    session_id: str


class MessageRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class GetUserSessionRequest(BaseModel):
    user_id: str