# Booking Enquiry System Architecture

**Date:** 2025-11-14
**Author:** Claude Code
**Status:** Implemented
**Version:** 1.0.0

## Overview

The Booking Enquiry System enables users to send custom booking requests directly to event organizers/merchants through the chatbot. The system handles the entire lifecycle from enquiry creation to merchant reply, with LLM-powered message formatting and multi-channel notification support.

## System Architecture

### High-Level Flow

```
User → Chatbot → BookingEnquiry Tool → Database → Notification Service → Merchant
                                                                              ↓
User ← Chatbot ← Memory Update ← LLM Analyzer ← Database ← API Endpoint ← Merchant Reply
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Conversation Layer                        │
├─────────────────────────────────────────────────────────────┤
│  ConversationOrchestrator                                   │
│    └── ReAct Agent                                          │
│          └── BookingEnquiry Tool (DSPy)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Business Logic Layer                        │
├─────────────────────────────────────────────────────────────┤
│  _create_booking_enquiry()                                  │
│    ├── Fetch merchant info (Database)                      │
│    ├── Create enquiry record (Database)                    │
│    ├── Send notification (NotificationService)             │
│    └── Update status (Database)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Data Layer                                  │
├─────────────────────────────────────────────────────────────┤
│  Database Tables:                                           │
│    - booking_enquiries                                      │
│    - enquiry_replies                                        │
│    - events (existing)                                      │
│    - organizers (existing)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│               Notification Layer (Strategy Pattern)         │
├─────────────────────────────────────────────────────────────┤
│  NotificationService (Facade)                               │
│    └── NotificationChannel (Interface)                     │
│          ├── LogNotificationChannel ✅                      │
│          ├── EmailNotificationChannel (planned)            │
│          └── WhatsAppNotificationChannel (planned)         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
                  [Merchant]


┌─────────────────────────────────────────────────────────────┐
│                  Merchant Reply Flow                         │
└─────────────────────────────────────────────────────────────┘

[Merchant] → POST /api/enquiry-reply
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  API Layer                                    │
├──────────────────────────────────────────────────────────────┤
│  handle_enquiry_reply(request: EnquiryReplyRequest)         │
│    ├── Validate enquiry exists (Database)                   │
│    ├── Format reply (MerchantReplyAnalyzer - DSPy LLM)      │
│    ├── Store reply (Database)                               │
│    ├── Update enquiry status (Database)                     │
│    ├── Send notification to user (NotificationService)      │
│    └── Update conversation history (MemoryManager)          │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
                     [User]
```

## Database Schema

### booking_enquiries Table

```sql
CREATE TABLE booking_enquiries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NULL,
    session_id VARCHAR(255) NOT NULL,
    event_id BIGINT NOT NULL,
    organizer_id BIGINT NOT NULL,
    enquiry_type VARCHAR(50) NOT NULL DEFAULT 'custom_booking',
    user_message TEXT NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    merchant_email VARCHAR(255) NOT NULL,
    merchant_phone VARCHAR(50) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_user_session (user_id, session_id),
    INDEX idx_organizer (organizer_id),
    INDEX idx_event (event_id),
    INDEX idx_status (status)
);
```

**Status Flow:**
```
pending → sent → replied → completed
                     ↓
                 cancelled
```

**Enquiry Types:**
- `custom_booking`: Custom arrangements or packages
- `group_booking`: Large groups (20+ people)
- `special_request`: Accessibility, accommodations, etc.

### enquiry_replies Table

```sql
CREATE TABLE enquiry_replies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    enquiry_id BIGINT NOT NULL,
    reply_from VARCHAR(50) NOT NULL,
    reply_message TEXT NOT NULL,
    reply_channel VARCHAR(50) NOT NULL DEFAULT 'api',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_enquiry_id (enquiry_id),
    INDEX idx_reply_from (reply_from),
    FOREIGN KEY (enquiry_id) REFERENCES booking_enquiries(id) ON DELETE CASCADE
);
```

**reply_from Values:**
- `merchant`: Reply from event organizer
- `user`: Follow-up from user
- `system`: Automated system messages

**reply_channel Values:**
- `email`: Reply received via email
- `whatsapp`: Reply received via WhatsApp
- `api`: Direct API submission

## DSPy Components

### 1. BookingEnquiry Tool

**Location:** `src/app/llm/tools/BookingEnquiry.py`
**Type:** DSPy Tool (wraps private function)

**Pattern:**
```python
# Private implementation function
def _create_booking_enquiry(event_id, user_message, contact_email, ...) -> Dict:
    # Business logic
    pass

# DSPy Tool wrapper
BookingEnquiry = dspy.Tool(
    func=_create_booking_enquiry,
    name="booking_enquiry",
    desc="Detailed description for ReAct agent..."
)
```

**Responsibilities:**
1. Validate event exists and is published
2. Retrieve merchant contact information
3. Create enquiry record in database
4. Send notification to merchant
5. Update enquiry status based on notification result
6. Return user-friendly confirmation message

**Error Handling:**
- Event not found → User-friendly error
- Merchant contact missing → Suggest contacting support
- Notification failure → Error with support contact
- Database errors → Generic error with support

**Return Format:**
```python
{
    "status": "success" | "error",
    "message": "Human-readable message for user",
    "enquiry_id": "123"  # Only on success
}
```

### 2. MerchantReplyAnalyzer Module

**Location:** `src/app/llm/modules/MerchantReplyAnalyzer.py`
**Type:** DSPy Module with ChainOfThought

**Signature:**
```python
class MerchantReplySignature(dspy.Signature):
    """Analyze and reformat merchant's reply..."""

    user_enquiry: str = dspy.InputField(...)
    merchant_reply: str = dspy.InputField(...)
    event_name: str = dspy.InputField(...)
    formatted_response: str = dspy.OutputField(...)
```

**Purpose:**
- Transform informal/brief merchant replies into professional, clear messages
- Preserve all important details (pricing, contact info, conditions)
- Maintain friendly, customer-service tone
- Add context if merchant's reply was unclear

**Example Transformation:**

**Input (Merchant):**
```
"yes 15% discount for 50+ ppl call 1234"
```

**Output (User):**
```
Great news! The event organizer for [Event Name] has confirmed they can
accommodate your group booking request.

Details:
• Group discount: 15% off for groups of 50 or more people
• Contact: Please call (852) 1234 to finalize the booking

If you have any additional questions, feel free to continue the conversation!
```

## API Endpoints

### POST /api/enquiry-reply

**Purpose:** Receive merchant replies to booking enquiries

**Request:**
```python
class EnquiryReplyRequest(BaseModel):
    enquiry_id: int
    reply_message: str
    reply_channel: str = "api"  # 'email', 'whatsapp', 'api'
```

**Response:**
```json
{
  "status": "success",
  "message": "Reply delivered to user"
}
```

**Workflow:**
1. Validate enquiry exists (database query)
2. Use MerchantReplyAnalyzer to format reply (LLM call)
3. Store reply in `enquiry_replies` table
4. Update enquiry status to 'replied'
5. Send notification to user (NotificationService)
6. Update conversation history (MemoryManager)

**Error Responses:**
```json
{
  "status": "error",
  "message": "Enquiry not found"
}
```

## Integration with ReAct Agent

### Tool Registration

**File:** `src/app/llm/modules/ConversationOrchestrator.py`

```python
from ..tools import BookingEnquiry

tools = [
    Thinking,       # Working memory
    SearchEvent,    # Event discovery
    MembershipInfo, # Membership queries
    TicketInfo,     # Ticket info
    GeneralHelp,    # Platform help
    BookingEnquiry, # NEW: Booking enquiries
]

agent = dspy.ReAct(ConversationSignature, tools=tools, max_iters=10)
```

### Agent Selection Logic

The ReAct agent automatically selects `BookingEnquiry` when detecting:

**Explicit Triggers:**
- "I want to enquire about..."
- "Can I book X tickets for..."
- "Do you offer group discounts..."
- "I need special accommodations..."

**Implicit Triggers:**
- Large quantity mentions (50+ tickets)
- Corporate event keywords
- Custom request language
- Accessibility needs

**Tool Description (guides agent):**
```
Use this tool when users want to:
- Request custom booking arrangements
- Book large groups (usually 20+ people)
- Ask organizers specific questions before purchasing
- Request customizations or special accommodations

DO NOT use for:
- General ticket questions (use TicketInfo)
- Standard purchases (direct users to platform)
- Membership questions (use MembershipInfo)
```

## Notification System

See [Notification Strategy Pattern Architecture](./2025-11-14-notification-strategy-pattern.md) for detailed documentation.

**Current Implementation:** LogNotificationChannel
**Planned:** EmailNotificationChannel, WhatsAppNotificationChannel

## Conversation Flow Examples

### Example 1: Group Booking Enquiry

```
User: I want to book 50 tickets for my company event to the Broadway Musical on Dec 15

Agent: [Uses Thinking] User wants group booking for 50 people
       [Uses SearchEvent] Finds event ID: 123, "Broadway Musical"
       [Uses BookingEnquiry] Creates enquiry
         - event_id: 123
         - user_message: "Group booking for 50 people on Dec 15"
         - enquiry_type: "group_booking"
         - contact_email: from session
         - contact_phone: optional

Agent Response: "Your enquiry has been sent to the event organizer.
                 Reference: #456. They will respond within 24-48 hours via email."

[System creates enquiry in database]
[Notification sent to merchant email/WhatsApp]
```

### Example 2: Merchant Reply

```
[Merchant receives notification via email]
[Merchant clicks reply link → lands on reply form]

Merchant fills form:
  Enquiry ID: 456
  Reply: "Yes, we can accommodate 50 people. 15% group discount applies.
          Please call (852) 1234-5678 to finalize booking details."
  Channel: email

[POST /api/enquiry-reply]
[MerchantReplyAnalyzer formats reply]
[Reply stored in database]
[User receives notification]
[Conversation history updated]

User sees in chatbot:
  "Great news! The event organizer for Broadway Musical has replied to
   your enquiry:

   They can accommodate your group of 50 people and offer a 15% group
   discount! To finalize the booking details, please contact them at
   (852) 1234-5678.

   If you have any follow-up questions, feel free to continue the
   conversation!"
```

## Security Considerations

### Input Validation
✅ Pydantic models validate all API inputs
✅ SQL parameterization prevents injection
✅ Email/phone format validation

### Data Privacy
✅ PII (contact info) stored securely
✅ No credit card storage
✅ Access control on enquiry endpoints (future)

### Rate Limiting
🔄 **Planned:** Rate limit enquiry creation per session
🔄 **Planned:** Rate limit merchant reply endpoint

### XSS Prevention
✅ LLM output passes through PostGuardrails
✅ HTML sanitization in formatted replies
✅ No direct HTML rendering of merchant replies

## Performance Considerations

### Database Optimization
✅ Indexes on frequently queried columns (session_id, status, organizer_id)
✅ Connection pooling (DatabaseConnectionPool)
✅ Efficient JOIN queries

### LLM Call Optimization
- MerchantReplyAnalyzer uses ChainOfThought (single LLM call)
- Langfuse observability tracks token usage
- Caching potential for similar enquiry types (future)

### Notification Delivery
- Async notification sending (future optimization)
- Fallback channels for delivery failures
- Retry logic with exponential backoff

## Testing Strategy

### Unit Tests
✅ BookingEnquiry tool logic
✅ MerchantReplyAnalyzer signature
✅ NotificationService channel selection
✅ API request validation

### Integration Tests
🔄 **Planned:** End-to-end enquiry flow
🔄 **Planned:** Database operations
🔄 **Planned:** Notification delivery

### Manual Testing Checklist
- [ ] Create enquiry via chatbot
- [ ] Verify database record created
- [ ] Check notification logged
- [ ] Submit merchant reply via API
- [ ] Verify LLM formatting
- [ ] Confirm conversation history updated

## Observability

### Langfuse Tracing
✅ BookingEnquiry tool calls traced
✅ MerchantReplyAnalyzer LLM calls traced
✅ Session tracking for enquiry lifecycle

### Structured Logging
✅ structlog for all enquiry operations
✅ Contextual logging (enquiry_id, session_id)
✅ Error logging with stack traces

### Metrics to Track
- Enquiry creation rate
- Merchant response time (created_at → replied_at)
- Notification delivery success rate
- LLM formatting quality

## Future Enhancements

### Phase 2: Email Integration
- Implement EmailNotificationChannel
- Email reply-to parsing webhook
- HTML email templates

### Phase 3: WhatsApp Integration
- WhatsAppNotificationChannel
- Interactive message templates
- Delivery status tracking

### Phase 4: Enhanced Features
- Enquiry status tracking dashboard (user-facing)
- Follow-up reminders (auto-remind merchant after 48 hours)
- Enquiry analytics for merchants
- User enquiry history endpoint

## Configuration

### Environment Variables

```bash
# Notification Channel Selection
NOTIFICATION_CHANNEL=log  # 'log', 'email', 'whatsapp'
NOTIFICATION_LOG_PATH=logs/notifications.log

# Email Configuration (future)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASSWORD=your_password
FROM_EMAIL=noreply@showeasy.ai

# API Configuration
API_BASE_URL=http://localhost:3010
```

### Database Migration

```bash
mysql -u root -p showeasy < migrations/001_booking_enquiries.sql
```

## SOLID Principles Applied

✅ **Single Responsibility:** Each component has one reason to change
  - BookingEnquiry: Enquiry creation logic only
  - MerchantReplyAnalyzer: Reply formatting only
  - NotificationService: Channel routing only

✅ **Open/Closed:** Open for extension, closed for modification
  - New notification channels added without modifying service

✅ **Liskov Substitution:** All NotificationChannels interchangeable
  - LogChannel, EmailChannel, WhatsAppChannel all implement same interface

✅ **Interface Segregation:** Minimal, focused interfaces
  - NotificationChannel has only essential methods

✅ **Dependency Inversion:** Depend on abstractions
  - NotificationService depends on NotificationChannel interface

## Related Documentation

- [Notification Strategy Pattern](./2025-11-14-notification-strategy-pattern.md)
- [Implementation Guide](../guides/2025-11-14-booking-enquiry-implementation.md)
- [Project CLAUDE.md](../../CLAUDE.md) - Tool usage

## Migration Scripts

**Location:** `migrations/001_booking_enquiries.sql`

**Rollback (if needed):**
```sql
DROP TABLE IF EXISTS enquiry_replies;
DROP TABLE IF EXISTS booking_enquiries;
```
