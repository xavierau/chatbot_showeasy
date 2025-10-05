import dspy
import os
import mysql.connector
from typing import Dict, List, Optional
from langfuse import observe


class DatabaseInsights:
    """Generates intelligent insights about the events database."""

    def __init__(self):
        """Initialize database connection parameters."""
        self.db_host = os.getenv("DB_HOST")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_name = os.getenv("DB_NAME")

        if not all([self.db_host, self.db_user, self.db_password, self.db_name]):
            raise ValueError("Database environment variables not set")

    def _execute_query(self, query: str) -> List[Dict]:
        """Execute SQL query and return results."""
        connection = None
        try:
            connection = mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            return results
        except mysql.connector.Error as err:
            print(f"Database error in insights: {err}")
            return []
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    @observe()
    def get_categories_insight(self) -> Dict:
        """Get available event categories with counts."""
        query = """
        SELECT
            JSON_UNQUOTE(JSON_EXTRACT(c.name, '$.en')) AS category_name,
            COUNT(e.id) AS event_count
        FROM categories c
        LEFT JOIN events e ON e.category_id = c.id
        WHERE e.event_status = 'published'
        AND e.visibility = 'public'
        GROUP BY c.id, category_name
        HAVING event_count > 0
        ORDER BY event_count DESC
        """
        results = self._execute_query(query)

        summary = []
        for row in results:
            summary.append(f"{row['category_name']} ({row['event_count']} events)")

        return {
            "categories": results,
            "summary": f"Available categories: {', '.join(summary)}" if summary else "No categories available"
        }

    @observe()
    def get_locations_insight(self) -> Dict:
        """Get cities/locations with event counts."""
        query = """
        SELECT
            JSON_UNQUOTE(JSON_EXTRACT(v.city, '$.en')) AS city_name,
            COUNT(DISTINCT eo.event_id) AS event_count
        FROM venues v
        INNER JOIN event_occurrences eo ON eo.venue_id = v.id
        INNER JOIN events e ON e.id = eo.event_id
        WHERE e.event_status = 'published'
        AND e.visibility = 'public'
        AND v.city IS NOT NULL
        GROUP BY city_name
        HAVING city_name IS NOT NULL
        ORDER BY event_count DESC
        LIMIT 20
        """
        results = self._execute_query(query)

        summary = []
        for row in results:
            summary.append(f"{row['city_name']} ({row['event_count']} events)")

        return {
            "locations": results,
            "summary": f"Events available in: {', '.join(summary)}" if summary else "No locations available"
        }

    @observe()
    def get_date_ranges_insight(self) -> Dict:
        """Get upcoming events date ranges."""
        query = """
        SELECT
            MIN(eo.start_at_utc) AS earliest_event,
            MAX(eo.start_at_utc) AS latest_event,
            COUNT(DISTINCT e.id) AS total_upcoming_events
        FROM event_occurrences eo
        INNER JOIN events e ON e.id = eo.event_id
        WHERE e.event_status = 'published'
        AND e.visibility = 'public'
        AND eo.start_at_utc >= NOW()
        """
        results = self._execute_query(query)

        if results and results[0]['total_upcoming_events'] > 0:
            earliest = results[0]['earliest_event']
            latest = results[0]['latest_event']
            total = results[0]['total_upcoming_events']
            summary = f"{total} upcoming events from {earliest.strftime('%Y-%m-%d') if earliest else 'now'} to {latest.strftime('%Y-%m-%d') if latest else 'future'}"
        else:
            summary = "No upcoming events available"

        return {
            "date_ranges": results[0] if results else {},
            "summary": summary
        }

    @observe()
    def get_popular_events_insight(self) -> Dict:
        """Get popular/featured events."""
        query = """
        SELECT
            JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')) AS event_name,
            JSON_UNQUOTE(JSON_EXTRACT(c.name, '$.en')) AS category_name,
            JSON_UNQUOTE(JSON_EXTRACT(e.slug, '$.en')) AS slug,
            MIN(eo.start_at_utc) AS next_occurrence
        FROM events e
        INNER JOIN categories c ON c.id = e.category_id
        INNER JOIN event_occurrences eo ON eo.event_id = e.id
        WHERE e.event_status = 'published'
        AND e.visibility = 'public'
        AND eo.start_at_utc >= NOW()
        GROUP BY e.id, event_name, category_name, slug
        ORDER BY next_occurrence ASC
        LIMIT 10
        """
        results = self._execute_query(query)

        summary = []
        for row in results:
            summary.append(f"{row['event_name']} ({row['category_name']})")

        return {
            "popular_events": results,
            "summary": f"Featured upcoming events: {', '.join(summary[:5])}" if summary else "No popular events"
        }

    @observe()
    def get_statistics_insight(self) -> Dict:
        """Get overall database statistics."""
        query = """
        SELECT
            (SELECT COUNT(*) FROM events WHERE event_status = 'published' AND visibility = 'public') AS total_events,
            (SELECT COUNT(*) FROM categories) AS total_categories,
            (SELECT COUNT(DISTINCT venue_id) FROM event_occurrences) AS total_venues,
            (SELECT COUNT(*) FROM event_occurrences WHERE start_at_utc >= NOW()) AS upcoming_occurrences
        """
        results = self._execute_query(query)

        if results:
            stats = results[0]
            summary = f"Database contains {stats['total_events']} published events across {stats['total_categories']} categories, {stats['total_venues']} venues, with {stats['upcoming_occurrences']} upcoming occurrences"
        else:
            summary = "No statistics available"

        return {
            "statistics": results[0] if results else {},
            "summary": summary
        }

    @observe()
    def generate_all_insights(self) -> Dict[str, Dict]:
        """Generate all insights at once."""
        return {
            "categories": self.get_categories_insight(),
            "locations": self.get_locations_insight(),
            "date_ranges": self.get_date_ranges_insight(),
            "popular_events": self.get_popular_events_insight(),
            "statistics": self.get_statistics_insight()
        }

    def compile_context_summary(self, insights: Dict[str, Dict]) -> str:
        """Compile insights into a natural language context summary for LLM."""
        summaries = []

        for insight_type, data in insights.items():
            if data and 'summary' in data:
                summaries.append(data['summary'])

        if not summaries:
            return "No database insights available."

        context = "DATABASE CONTEXT:\n" + "\n".join(f"- {s}" for s in summaries)

        # Add semantic mapping hints for categories (Layer 1)
        if insights.get('categories', {}).get('categories'):
            context += "\n\nSEMANTIC MATCHING GUIDE:"
            context += "\n- When users search with category-like terms, match them to the EXACT category names listed above"
            context += "\n- Examples of semantic matches:"

            categories = insights['categories']['categories']
            semantic_examples = []

            for cat in categories:
                cat_name = cat.get('category_name', '')
                if cat_name:
                    # Generate common search variations
                    variations = self._generate_search_variations(cat_name)
                    if variations:
                        semantic_examples.append(f"  '{variations}' → '{cat_name}'")

            if semantic_examples:
                context += "\n" + "\n".join(semantic_examples[:5])  # Limit to 5 examples

        return context

    def _generate_search_variations(self, category_name: str) -> str:
        """Generate common user search variations for a category name."""
        variations = []

        # Lower case version
        base = category_name.lower()

        # Singular version (remove trailing 's')
        if category_name.endswith('s'):
            singular = category_name[:-1].lower()
            if singular != base:
                variations.append(singular)

        # Common word substitutions
        substitutions = {
            'concerts': 'concert',
            'exhibitions': 'exhibition',
            'workshops': 'workshop',
            'conferences': 'conference',
        }

        for plural, singular in substitutions.items():
            if plural in base:
                variations.append(base.replace(plural, singular))

        return variations[0] if variations else base
