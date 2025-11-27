# Notification Service - Strategy Pattern Architecture

**Date:** 2025-11-14
**Author:** Claude Code
**Status:** Implemented
**Related:** Booking Enquiry System

## Overview

The notification service implements the **Strategy Pattern** to support multiple notification channels (email, SMS, WhatsApp, log) with a pluggable architecture. This design allows the system to:

1. Send notifications through different channels without changing client code
2. Add new channels without modifying existing code (Open/Closed Principle)
3. Test notification logic without external dependencies
4. Switch channels at runtime based on configuration

## Design Pattern: Strategy Pattern

### Components

```
NotificationChannel (Interface)
    ↑
    ├── LogNotificationChannel (Concrete Strategy)
    ├── EmailNotificationChannel (Future)
    ├── WhatsAppNotificationChannel (Future)
    └── SMSNotificationChannel (Future)

NotificationService (Context/Facade)
    └── uses → NotificationChannel
```

### Key Interfaces

#### NotificationChannel (Abstract Base Class)

```python
class NotificationChannel(ABC):
    @abstractmethod
    def send_enquiry_to_merchant(self, notification: EnquiryNotification) -> Dict

    @abstractmethod
    def send_reply_to_user(self, notification: ReplyNotification) -> Dict

    @abstractmethod
    def get_channel_name(self) -> str

    def is_available(self) -> bool
```

**Responsibilities:**
- Define interface for all notification channels
- Ensure consistent return types across implementations
- Provide availability checking mechanism

#### Data Transfer Objects (DTOs)

**EnquiryNotification:**
```python
@dataclass
class EnquiryNotification:
    enquiry_id: int
    event_name: str
    user_message: str
    user_email: str
    user_phone: Optional[str]
    merchant_email: str
    merchant_phone: Optional[str]
    reply_url: str
```

**ReplyNotification:**
```python
@dataclass
class ReplyNotification:
    enquiry_id: int
    event_name: str
    merchant_reply: str
    user_email: str
    user_phone: Optional[str]
```

**Purpose:** Decouple notification content from delivery mechanism

## Current Implementation

### 1. LogNotificationChannel (Test Implementation)

**Purpose:** Testing and development without external services
**Location:** `src/app/services/notification/log_channel.py`

**Features:**
- Writes JSON Lines format to log file
- Includes both raw data and formatted messages
- Shows what email/SMS would look like
- Configurable log path via environment variable

**Log Format:**
```json
{
  "timestamp": "2025-11-14T10:30:00Z",
  "type": "enquiry_to_merchant",
  "channel": "log",
  "enquiry_id": 123,
  "event_name": "Concert XYZ",
  "merchant": {...},
  "user": {...},
  "formatted_message": "..."
}
```

**Configuration:**
```bash
NOTIFICATION_CHANNEL=log
NOTIFICATION_LOG_PATH=logs/notifications.log
```

**Use Cases:**
- Local development
- CI/CD testing
- Debugging notification content
- Demo environments

## Future Channel Implementations

### 2. EmailNotificationChannel (Planned)

**Provider Options:**
- Gmail SMTP (development/small scale)
- SendGrid (production - recommended)
- AWS SES (cost-effective for high volume)
- Mailgun (developer-friendly)

**Implementation Location:** `src/app/services/notification/email_channel.py`

**Required Configuration:**
```bash
NOTIFICATION_CHANNEL=email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@showeasy.ai
```

**Features to Implement:**
- HTML email templates
- Reply-to parsing (for merchant responses)
- Delivery confirmation
- Bounce handling
- Rate limiting

**Sample Implementation Structure:**
```python
class EmailNotificationChannel(NotificationChannel):
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT"))
        # ...

    def send_enquiry_to_merchant(self, notification: EnquiryNotification):
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = notification.merchant_email
        msg['Subject'] = f"New Booking Enquiry #{notification.enquiry_id}"

        # Use HTML template
        body = self._render_template('enquiry_to_merchant.html', notification)
        msg.attach(MIMEText(body, 'html'))

        # Send via SMTP
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

        return {"success": True, "channel": "email"}
```

### 3. WhatsAppNotificationChannel (Planned)

**Provider Options:**
- Twilio WhatsApp API (recommended)
- WhatsApp Business API (direct)
- Meta Cloud API

**Implementation Location:** `src/app/services/notification/whatsapp_channel.py`

**Required Configuration:**
```bash
NOTIFICATION_CHANNEL=whatsapp
WHATSAPP_ENABLED=true
WHATSAPP_API_KEY=your_api_key
WHATSAPP_FROM_NUMBER=+85212345678
```

**Features to Implement:**
- Template message support (WhatsApp requirement)
- Rich media attachments (event images)
- Delivery status webhooks
- Interactive buttons for reply
- Rate limiting (WhatsApp restrictions)

**Sample Implementation:**
```python
class WhatsAppNotificationChannel(NotificationChannel):
    def __init__(self):
        self.api_key = os.getenv("WHATSAPP_API_KEY")
        self.from_number = os.getenv("WHATSAPP_FROM_NUMBER")
        self.client = TwilioClient(...)  # or WhatsApp Business Client

    def send_enquiry_to_merchant(self, notification: EnquiryNotification):
        # Use approved template
        message = self.client.messages.create(
            from_=f'whatsapp:{self.from_number}',
            to=f'whatsapp:{notification.merchant_phone}',
            content_sid='TEMPLATE_SID',
            content_variables={
                'event_name': notification.event_name,
                'user_message': notification.user_message,
                # ...
            }
        )

        return {"success": True, "channel": "whatsapp", "message_id": message.sid}
```

### 4. SMSNotificationChannel (Future)

**Provider Options:**
- Twilio SMS
- AWS SNS
- Vonage (Nexmo)

**Use Cases:**
- SMS-only fallback for merchants
- One-time verification codes
- Critical notifications

## NotificationService (Facade)

**Location:** `src/app/services/notification/notification_service.py`

**Responsibilities:**
1. Select appropriate channel based on configuration
2. Validate channel availability before sending
3. Provide simplified interface for clients
4. Build reply URLs
5. Handle channel failures gracefully

**Usage Example:**
```python
from app.services.notification import NotificationService

service = NotificationService()  # Auto-detects channel from env

result = service.send_enquiry_to_merchant(
    enquiry_id=123,
    event_name="Concert",
    user_message="I want to book 50 tickets",
    user_email="user@example.com",
    merchant_email="merchant@example.com"
)

if result['success']:
    print(f"Sent via {result['channel']}")
else:
    print(f"Failed: {result['message']}")
```

## Extension Guide

### Adding a New Notification Channel

**Step 1:** Create channel implementation
```bash
touch src/app/services/notification/sms_channel.py
```

**Step 2:** Implement NotificationChannel interface
```python
from .notification_interface import NotificationChannel

class SMSNotificationChannel(NotificationChannel):
    def send_enquiry_to_merchant(self, notification):
        # Implementation
        pass

    def send_reply_to_user(self, notification):
        # Implementation
        pass

    def get_channel_name(self):
        return "sms"

    def is_available(self):
        # Check API credentials
        return bool(os.getenv("SMS_API_KEY"))
```

**Step 3:** Export from `__init__.py`
```python
from .sms_channel import SMSNotificationChannel

__all__ = [..., "SMSNotificationChannel"]
```

**Step 4:** Update NotificationService factory
```python
def _get_channel_from_env(self):
    channel_type = os.getenv("NOTIFICATION_CHANNEL", "log").lower()

    if channel_type == "log":
        return LogNotificationChannel()
    elif channel_type == "email":
        return EmailNotificationChannel()
    elif channel_type == "whatsapp":
        return WhatsAppNotificationChannel()
    elif channel_type == "sms":
        return SMSNotificationChannel()  # NEW
    else:
        raise ValueError(f"Unknown channel: {channel_type}")
```

**Step 5:** Add environment variables to `.env.example`
```bash
# SMS Configuration
NOTIFICATION_CHANNEL=sms
SMS_API_KEY=your_api_key
SMS_FROM_NUMBER=+85212345678
```

**Step 6:** Write tests
```python
# tests/test_sms_channel.py
def test_sms_channel_sends_successfully():
    channel = SMSNotificationChannel()
    result = channel.send_enquiry_to_merchant(notification)
    assert result['success'] is True
    assert result['channel'] == 'sms'
```

## Benefits of Strategy Pattern

### 1. Open/Closed Principle
✅ **Open for extension:** Add new channels without modifying existing code
✅ **Closed for modification:** NotificationService doesn't change when adding channels

### 2. Dependency Inversion Principle
✅ NotificationService depends on abstraction (NotificationChannel), not concrete implementations
✅ Easy to mock/test with fake channels

### 3. Single Responsibility Principle
✅ Each channel handles only its own communication logic
✅ NotificationService handles only channel selection

### 4. Testability
✅ Can test each channel independently
✅ Can inject mock channels for unit testing
✅ LogChannel allows testing without external services

### 5. Runtime Flexibility
✅ Switch channels via environment variable
✅ No code changes needed to change notification method
✅ Can implement fallback chains (email fails → SMS backup)

## Testing Strategy

### Unit Tests
```python
# Test interface compliance
def test_channel_implements_interface():
    channel = LogNotificationChannel()
    assert isinstance(channel, NotificationChannel)

# Test each channel independently
def test_log_channel_writes_to_file():
    channel = LogNotificationChannel(log_path="test.log")
    result = channel.send_enquiry_to_merchant(notification)
    assert result['success'] is True
    assert Path("test.log").exists()
```

### Integration Tests
```python
# Test service with different channels
@pytest.mark.parametrize("channel_type", ["log", "email", "whatsapp"])
def test_notification_service_with_channel(channel_type):
    os.environ["NOTIFICATION_CHANNEL"] = channel_type
    service = NotificationService()
    # ... test notification sending
```

## Migration Path

### Phase 1: Log Channel Only (✅ Complete)
- Implement log channel for testing
- Validate notification flow
- Test message formatting

### Phase 2: Email Channel (Planned)
- Choose email provider (SendGrid recommended)
- Implement EmailNotificationChannel
- Create HTML email templates
- Set up reply-to parsing webhook

### Phase 3: WhatsApp Channel (Planned)
- Register with WhatsApp Business API
- Create approved message templates
- Implement WhatsAppNotificationChannel
- Handle delivery status webhooks

### Phase 4: Multi-Channel & Fallbacks (Future)
- Support multiple channels per notification
- Implement fallback chains (email → SMS)
- Add channel priority configuration
- Implement delivery tracking dashboard

## Configuration Matrix

| Channel   | Primary Config Var         | Additional Vars                              | Status      |
|-----------|----------------------------|----------------------------------------------|-------------|
| Log       | NOTIFICATION_CHANNEL=log   | NOTIFICATION_LOG_PATH                        | ✅ Implemented |
| Email     | NOTIFICATION_CHANNEL=email | SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL | 🔄 Planned   |
| WhatsApp  | NOTIFICATION_CHANNEL=whatsapp | WHATSAPP_API_KEY, WHATSAPP_FROM_NUMBER   | 🔄 Planned   |
| SMS       | NOTIFICATION_CHANNEL=sms   | SMS_API_KEY, SMS_FROM_NUMBER                 | 🔮 Future    |

## SOLID Principles Applied

✅ **Single Responsibility:** Each channel handles only its communication method
✅ **Open/Closed:** New channels added without modifying existing code
✅ **Liskov Substitution:** All channels interchangeable via NotificationChannel interface
✅ **Interface Segregation:** Minimal interface with only essential methods
✅ **Dependency Inversion:** High-level NotificationService depends on abstraction

## Related Documentation

- [Booking Enquiry System Architecture](./2025-11-14-booking-enquiry-system.md)
- [Booking Enquiry Implementation Guide](../guides/2025-11-14-booking-enquiry-implementation.md)
- Project CLAUDE.md - Booking Enquiry Tool Usage

## References

- **Design Pattern:** Strategy Pattern (Gang of Four)
- **Python ABC Module:** https://docs.python.org/3/library/abc.html
- **Dataclasses:** https://docs.python.org/3/library/dataclasses.html
- **SOLID Principles:** Robert C. Martin (Uncle Bob)
