from pydantic import BaseModel, Field
from typing import Optional


class SearchEventInput(BaseModel):
    """Input model for the SearchEvent tool."""
    query: str = Field(..., description="The main search term for events.")
    location: Optional[str] = Field(
        None, description="The location to search for events (e.g., 'San Francisco')."
    )
    date: Optional[str] = Field(
        None, description="The date or date range for the events (e.g., 'today', 'next week')."
    )
    category: Optional[str] = Field(
        None, description="The category of the event (e.g., 'tech', 'music')."
    )
