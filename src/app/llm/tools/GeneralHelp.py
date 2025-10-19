"""
GeneralHelp Tool - Provides general platform help and information.

This tool handles:
- Platform navigation and features
- Account management
- General FAQs
- Platform policies
"""
import dspy
from typing import Dict


def _get_general_help(category: str = "navigation") -> Dict[str, str]:
    """
    Retrieves general help information.

    Args:
        category: Category of help - 'navigation', 'account', 'policies', 'features', 'contact'

    Returns:
        Dictionary with help information
    """

    help_info = {
        "navigation": """Platform Navigation:
        - Home: Browse featured and upcoming events
        - Search: Find events by category, location, or date
        - My Events: View your purchased tickets and upcoming events
        - Favorites: Save events you're interested in
        - Account: Manage profile, payment methods, and membership

        Use the search bar at the top to quickly find any event!""",

        "account": """Account Management:
        - Profile: Update your name, email, and preferences
        - Payment Methods: Add/remove credit cards and payment options
        - Order History: View all past ticket purchases
        - Preferences: Set favorite categories and notification settings
        - Membership: View or upgrade your membership status

        Access your account by clicking your profile icon in the top right.""",

        "policies": """Platform Policies:
        - Privacy Policy: We protect your personal information
        - Terms of Service: Rules and guidelines for platform use
        - Cookie Policy: How we use cookies to enhance your experience
        - Accessibility: We're committed to making events accessible to everyone

        Full policy documents available at https://eventplatform.test/policies""",

        "features": """Platform Features:
        - Smart Search: AI-powered event recommendations
        - Event Reminders: Never miss events you care about
        - Social Sharing: Share events with friends
        - Personalized Feed: Events tailored to your interests
        - Mobile App: Access tickets and discover events on the go
        - Wishlist: Save events for later

        Premium members get enhanced features like early access and exclusive events!""",

        "contact": """Contact Customer Support:
        - Phone: (852) 5538 3561 (answered within 24 hours)
        - Email: info@showeasy.ai (reply within 10 working days)
        - Office: 6/F, V Point, 18 Tang Lung Street, Causeway Bay, Hong Kong

        For account-specific issues, make sure you're logged in when contacting support."""
    }

    return {"info": help_info.get(category, help_info["navigation"])}


# Create DSPy Tool for general help
GeneralHelp = dspy.Tool(
    func=_get_general_help,
    name="general_help",
    desc="""Get general help and information about the ShowEasy platform.

Parameters:
- category: Type of help needed - 'navigation', 'account', 'policies', 'features', or 'contact'

Use this tool when users ask about:
- How to use the platform
- Account management
- Platform features
- Policies and terms
- How to contact support
- General platform questions"""
)
