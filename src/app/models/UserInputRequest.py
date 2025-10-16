from pydantic import BaseModel
from typing import Optional

class UserInputRequest(BaseModel):
    user_input: str
    user_id: Optional[int]
    session_id: str
    current_url: Optional[str]

class GetMessagesRequest(BaseModel):
    session_id: str