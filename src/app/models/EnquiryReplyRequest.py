"""
Pydantic model for Enquiry Reply API requests.

Validates incoming merchant reply data for the /api/enquiry-reply endpoint.
"""

from pydantic import BaseModel, Field


class EnquiryReplyRequest(BaseModel):
    """
    Request model for merchant replies to booking enquiries.

    This model validates the data when merchants or systems reply to
    user booking enquiries through the API.

    Attributes:
        enquiry_id: ID of the booking enquiry being replied to
        reply_message: The merchant's reply message
        reply_channel: How the merchant replied ('email', 'whatsapp', 'api')
    """

    enquiry_id: int = Field(
        ...,
        description="Unique identifier for the booking enquiry",
        gt=0
    )

    reply_message: str = Field(
        ...,
        description="The merchant's reply message to the user's enquiry",
        min_length=1,
        max_length=10000
    )

    reply_channel: str = Field(
        default="api",
        description="Channel through which the reply was received. "
                    "Options: 'email', 'whatsapp', 'api'",
        pattern="^(email|whatsapp|api)$"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "enquiry_id": 123,
                "reply_message": "Yes, we can accommodate 50 people with a 15% group discount. Please call us at (852) 1234-5678 to finalize the booking.",
                "reply_channel": "email"
            }
        }
