import dspy
from app.models import SearchEventInput
from app.llm.signatures import QueryGenerationSignature
from typing import Optional
from langfuse import observe
import datetime


class QueryGeneration(dspy.Module):
    """A DSPy module that generates a MySQL query from a user's search request."""

    def __init__(self):
        super().__init__()
        self.generator = dspy.ChainOfThought(QueryGenerationSignature)
        self.mysql_db_schema = """-- Organizers: The people or companies hosting events
CREATE TABLE `organizers` (
  `id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `slug` varchar,
  `description` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `website_url` varchar,
  `contact_email` varchar,
  `contact_phone` varchar,
  `social_media_links` json,
  `address_line_1` varchar,
  `city` varchar,
  `country_id` bigint,
  `state_id` bigint,
  `is_active` tinyint
);

-- Events: The main happenings (concerts, shows, etc.)
CREATE TABLE `events` (
  `id` bigint,
  `organizer_id` bigint,
  `category_id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `slug` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `description` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `short_summary` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `event_status` varchar,
  `visibility` varchar,
  `is_featured` tinyint,
  `contact_email` varchar,
  `contact_phone` varchar,
  `website_url` varchar,
  `social_media_links` json,
  `youtube_video_id` varchar,
  `published_at` timestamp
);

-- Venues: The physical (or virtual) locations for events
CREATE TABLE `venues` (
  `id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `description` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `slug` varchar,
  `organizer_id` bigint,
  `address_line_1` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `address_line_2` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `city` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `postal_code` varchar,
  `state_id` bigint,
  `country_id` bigint,
  `latitude` decimal,
  `longitude` decimal,
  `website_url` varchar,
  `seating_capacity` int,
  `is_active` tinyint
);

-- Event Occurrences: Specific dates/times for an event
CREATE TABLE `event_occurrences` (
  `id` bigint,
  `event_id` bigint,
  `venue_id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `description` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `start_at_utc` timestamp,
  `end_at_utc` timestamp,
  `timezone` varchar,
  `is_online` tinyint,
  `online_meeting_link` varchar,
  `status` varchar,
  `capacity` int
);

-- Ticket Definitions: The types of tickets available for sale
CREATE TABLE `ticket_definitions` (
  `id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `description` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `price` int,
  `currency` varchar,
  `total_quantity` int,
  `availability_window_start_utc` timestamp,
  `availability_window_end_utc` timestamp,
  `status` varchar
);

-- Pivot Table: Links specific occurrences to ticket types
CREATE TABLE `event_occurrence_ticket_definition` (
  `event_occurrence_id` bigint,
  `ticket_definition_id` bigint,
  `quantity_for_occurrence` int,
  `price_override` int,
  `availability_status` varchar
);

-- Categories: For filtering events (e.g., "Music", "Theater")
CREATE TABLE `categories` (
  `id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `slug` varchar,
  `parent_id` bigint,
  `is_active` tinyint
);

-- Tags: For adding keywords to events (e.g., "Pop", "Outdoor")
CREATE TABLE `tags` (
  `id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `slug` varchar
);

-- Pivot Table: Links events to tags
CREATE TABLE `event_tag` (
  `event_id` bigint,
  `tag_id` bigint
);

-- Countries: Location data
CREATE TABLE `countries` (
  `id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `iso_code_2` varchar,
  `is_active` tinyint
);

-- States: Location data (provinces, regions, etc.)
CREATE TABLE `states` (
  `id` bigint,
  `country_id` bigint,
  `name` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `code` varchar,
  `is_active` tinyint
);

-- CMS Pages: For static content like "About Us", "FAQ", etc.
CREATE TABLE `cms_pages` (
  `id` bigint,
  `title` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `slug` varchar,
  `content` json COMMENT 'Multilingual content {"en": "...", "zh-TW": "...", ...}',
  `is_published` tinyint,
  `published_at` timestamp
);
"""

    @observe()
    def forward(
        self,
        request: SearchEventInput,
        previous_query: Optional[str] = None,
        db_error: Optional[str] = None,
        database_insights: Optional[str] = None
    ) -> str:
        """Generates a MySQL query based on the structured search request and database insights."""
        criteria = []
        if request.query:
            criteria.append(f"General query: '{request.query}'")
        if request.location:
            criteria.append(f"Location: '{request.location}'")
        if request.date:
            criteria.append(f"Date or time frame: '{request.date}'")
        if request.category:
            criteria.append(f"Category: '{request.category}'")
        # ** NEW **: Add checks for all the new 'optimal' fields
        if request.tags:
            tag_list = ", ".join([f"'{t}'" for t in request.tags])
            criteria.append(f"Must have tags: [{tag_list}]")
        if request.is_online is True:
            criteria.append("Event must be online")
        elif request.is_online is False:
            criteria.append("Event must be in-person (not online)")
        if request.max_price is not None:
            if request.max_price == 0:
                criteria.append("Event must be free")
            else:
                criteria.append(f"Maximum ticket price: {request.max_price}")
        if request.organizer_name:
            criteria.append(f"Hosted by organizer: '{request.organizer_name}'")
        if request.venue_name:
            criteria.append(f"At venue: '{request.venue_name}'")
        # --- End of updates ---

        utc_now_string = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

        if not criteria:
            user_request_str = f"Current UTC Datetime: {utc_now_string} \n User is asking for general event recommendations (no specific criteria given)."
        else:
            user_request_str = f"Current UTC Datetime: {utc_now_string} \n User is searching for events with the following criteria: " + ", ".join(criteria) + "."

        prediction = self.generator(
            user_request=user_request_str,
            db_schema=self.mysql_db_schema,
            database_insights=database_insights,
            previous_query=previous_query,
            db_error=db_error
        )

        return prediction.sql_query