import enum


class Intent(str, enum.Enum):
    GREETING = "Greeting"
    GOODBYE = "Goodbye"
    GENERAL_QUESTION = "General Question"
    FEATURE_REQUEST = "Feature Request"
    BUG_REPORT = "Bug Report"
    HELP_REQUEST = "Help Request"
    SEARCH_EVENT = "Search Event"
