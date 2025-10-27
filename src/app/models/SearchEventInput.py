from pydantic import BaseModel, Field
from typing import Optional, List


class SearchEventInput(BaseModel):
    """Input model for the SearchEvent tool."""

    # Core search
    query: Optional[str] = Field(
        None, description="The main search term (e.g., 'AI conference', 'Taylor Swift')."
    )
    location: Optional[str] = Field(
        None, description="The location (e.g., 'San Francisco', 'Tokyo', 'National Theater')."
    )
    date: Optional[str] = Field(
        None, description="The date or range (e.g., 'today', 'next week', 'in August')."
    )

    # --- Enhancements for Precision ---

    category: Optional[str] = Field(
        None, description="The primary category (e.g., 'Music', 'Tech')."
    )
    tags: Optional[List[str]] = Field(
        None, description="Specific keywords or tags (e.g., ['outdoor', 'family-friendly'])."
    )

    # Filters that map directly to schema columns
    is_online: Optional[bool] = Field(
        None, description="Set to 'true' for online-only events, 'false' for in-person only."
    )
    max_price: Optional[int] = Field(
        None, description="The maximum ticket price. Use 0 for 'free' events."
    )

    # Specific entity searches
    organizer_name: Optional[str] = Field(
        None, description="Search for events by a specific organizer's name."
    )
    venue_name: Optional[str] = Field(
        None, description="Search for events at a specific venue's name."
    )