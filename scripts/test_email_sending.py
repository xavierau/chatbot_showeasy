#!/usr/bin/env python
"""
Test script for EmailNotificationChannel

Sends test emails to verify the email notification system works correctly.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.services.notification import EmailNotificationChannel, EnquiryNotification, ReplyNotification


def main():
    # Set email configuration
    os.environ['MAIL_HOST'] = 'smtp.gmail.com'
    os.environ['MAIL_PORT'] = '465'
    os.environ['MAIL_USERNAME'] = 'info@showeasy.ai'
    os.environ['MAIL_PASSWORD'] = 'xxqlzcwqlozgqnjy'
    os.environ['MAIL_FROM_ADDRESS'] = 'info@showeasy.ai'
    os.environ['MAIL_FROM_NAME'] = 'ShowEasy.ai'

    # Test recipient
    test_email = 'xavier.au@anacreation.com'

    print("=" * 60)
    print("EmailNotificationChannel Test")
    print("=" * 60)

    # Create channel
    channel = EmailNotificationChannel()

    print(f"\nConfiguration:")
    print(f"  Host: {channel.host}")
    print(f"  Port: {channel.port}")
    print(f"  From: {channel.from_name} <{channel.from_address}>")
    print(f"  Available: {channel.is_available()}")

    # Test 1: Send enquiry to merchant
    print("\n" + "-" * 60)
    print("Test 1: Sending enquiry email (merchant notification)")
    print("-" * 60)

    enquiry_notification = EnquiryNotification(
        enquiry_id=12345,
        event_name="ShowEasy Test Concert 2025",
        user_message="Hi, I would like to book 50 tickets for my company's annual event. "
                     "We need seats together if possible. Can you also provide any group discounts? "
                     "Please let me know the available options.",
        user_email="customer@example.com",
        user_phone="+852 9123 4567",
        merchant_email=test_email,  # Send to test email
        merchant_phone="+852 2345 6789",
        reply_url="http://localhost:3010/api/enquiry-reply?id=12345"
    )

    result1 = channel.send_enquiry_to_merchant(enquiry_notification)
    print(f"Result: {result1}")

    if result1['success']:
        print(f"✓ Enquiry email sent to {test_email}")
    else:
        print(f"✗ Failed: {result1['message']}")

    # Test 2: Send reply to user
    print("\n" + "-" * 60)
    print("Test 2: Sending reply email (user notification)")
    print("-" * 60)

    reply_notification = ReplyNotification(
        enquiry_id=12345,
        event_name="ShowEasy Test Concert 2025",
        merchant_reply="Great news! We're pleased to confirm that we can accommodate your group booking request.\n\n"
                       "Details:\n"
                       "• Group discount: 15% off for groups of 50 or more people\n"
                       "• Seating: We can arrange adjacent seats in Section A\n"
                       "• Total: HK$42,500 (after discount)\n\n"
                       "To proceed, please contact us at events@showeasy.ai or call +852 2345 6789.\n\n"
                       "We look forward to hosting your company event!",
        user_email=test_email,  # Send to test email
        user_phone="+852 9123 4567"
    )

    result2 = channel.send_reply_to_user(reply_notification)
    print(f"Result: {result2}")

    if result2['success']:
        print(f"✓ Reply email sent to {test_email}")
    else:
        print(f"✗ Failed: {result2['message']}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Enquiry email (to merchant): {'✓ Sent' if result1['success'] else '✗ Failed'}")
    print(f"Reply email (to user):       {'✓ Sent' if result2['success'] else '✗ Failed'}")
    print(f"\nCheck {test_email} for the test emails.")


if __name__ == '__main__':
    main()
