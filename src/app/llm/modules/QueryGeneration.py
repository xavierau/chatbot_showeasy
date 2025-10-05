import dspy
from app.models import SearchEventInput
from app.llm.signatures import QueryGenerationSignature
from typing import Optional
from langfuse import observe


class QueryGeneration(dspy.Module):
    """A DSPy module that generates a MySQL query from a user's search request."""

    def __init__(self):
        super().__init__()
        self.generator = dspy.ChainOfThought(QueryGenerationSignature)
        self.mysql_db_schema = """### Simplified Database Schema for Event Search

This schema focuses on the four main tables required to find events and their details.

### Querying Guidelines
- **Use `LIKE` for Flexibility:** For all user-provided text filters (on names, descriptions, cities, or categories), you **MUST** use a case-insensitive `LIKE` comparison with wildcards (e.g., `LOWER(column) LIKE '%keyword%'`). Do NOT use exact matches (`=`).
- **Smart Keyword Logic:** The user's main `query` (e.g., "interesting events") should be broken into keywords ("interesting", "events"). The generated SQL should find events where **any** of these keywords appear in `events.name`, `events.description`, or `categories.name`. All keyword checks must be combined with `OR`. Do not use `AND` to connect different keywords.
- **Case-Insensitive Searches:** All `LIKE` comparisons MUST be case-insensitive. Achieve this by wrapping the column expression in the `LOWER()` function.
- **JSON Columns:** The `name`, `description`, `city`, and `slug` columns are JSON. Use `JSON_UNQUOTE(JSON_EXTRACT(column, '$.en'))` to query the English text.
- **Required SELECT Columns:** ALL queries MUST include both `e.id AS id` and `JSON_UNQUOTE(JSON_EXTRACT(e.slug, '$.en')) AS slug` in the SELECT clause. These fields are required to construct event detail page URLs (slug is preferred, but id is used as fallback when slug is NULL).

#### 1. `events` table
This is the main table for events.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `bigint` | **Primary Key** for the event. |
| `name` | `json` | The name of the event (e.g., `{"en": "Tech Conference"}`). |
| `slug` | `json` | URL-friendly slug for the event (e.g., `{"en": "tech-conference"}`). Used to construct event detail page URLs: `https://eventplatform.test/events/{slug}`. |
| `description`| `json` | A detailed description of the event. |
| `category_id`| `bigint` | **Foreign Key** linking to the `categories` table. |
| `event_status`| `varchar` | The status of the event (e.g., 'published', 'draft'). |
| `visibility` | `varchar` | The visibility of the event (e.g., 'public', 'private'). |

---

#### 2. `categories` table
This table stores the categories for events.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `bigint` | **Primary Key** for the category. |
| `name` | `json` | The name of the category (e.g., `{"en": "Tech"}`). |

*__Relationship:__ `events.category_id` links to `categories.id`.*

---

#### 3. `event_occurrences` table
This table stores the specific dates and times for each event. An event can have multiple occurrences.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `bigint` | **Primary Key** for the occurrence. |
| `event_id` | `bigint` | **Foreign Key** linking to the `events` table. |
| `venue_id` | `bigint` | **Foreign Key** linking to the `venues` table. |
| `start_at_utc`| `timestamp`| The start date and time of the occurrence in UTC. |

*__Relationship:__ `event_occurrences.event_id` links to `events.id`.*

---

#### 4. `venues` table
This table stores the location details for event occurrences.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `bigint` | **Primary Key** for the venue. |
| `city` | `json` | The city where the venue is located (e.g., `{"en": "San Francisco"}`). |

*__Relationship:__ `event_occurrences.venue_id` links to `venues.id`.*"""

    @observe()
    def forward(self, request: SearchEventInput, previous_query: Optional[str] = None, db_error: Optional[str] = None) -> str:
        """Generates a MySQL query based on the structured search request."""
        criteria = []
        if request.query:
            criteria.append(f"General query: '{request.query}'")
        if request.location:
            criteria.append(f"Location: '{request.location}'")
        if request.date:
            criteria.append(f"Date or time frame: '{request.date}'")
        if request.category:
            criteria.append(f"Category: '{request.category}'")
        
        user_request_str = "User is searching for events with the following criteria: " + ", ".join(criteria) + "."

        prediction = self.generator(
            user_request=user_request_str, 
            db_schema=self.mysql_db_schema,
            previous_query=previous_query,
            db_error=db_error
        )
        
        return prediction.sql_query
