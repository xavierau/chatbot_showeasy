import dspy
import os
import mysql.connector
from typing import Optional, Dict, List
from contextlib import contextmanager

# Import the necessary models and, specifically, the QueryGeneration CLASS
from app.models import SearchEventInput
from app.llm.modules.QueryGeneration import QueryGeneration
from app.llm.modules.DatabaseInsights import DatabaseInsights
from app.utils.insight_cache import InsightCache
from app.utils.category_matcher import CategoryMatcher
from config.database import DatabaseConnectionPool


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.

    Ensures connections are properly closed even if errors occur.
    """
    pool = DatabaseConnectionPool()
    connection = pool.get_connection()
    try:
        yield connection
    finally:
        if connection.is_connected():
            connection.close()


def _execute_query(sql: str) -> List[Dict]:
    """
    Execute a SQL query and return results.

    Args:
        sql: The SQL query to execute.

    Returns:
        List of dictionaries containing query results.

    Raises:
        mysql.connector.Error: If query execution fails.
    """
    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        return results

def _format_event_results(results: List[Dict], event_platform_base_url: str) -> str:
    """
    Format event query results into natural language summary.

    IMPORTANT: Every event result MUST include a URL using the event ID.
    URLs are constructed as: {EVENT_PLATFORM_HOST}/events/{event.id}

    Args:
        results: List of event dictionaries from database. Each MUST contain 'id' field.
        event_platform_base_url: Base URL for event platform.

    Returns:
        Formatted string summarizing the events with URLs always included.

    Raises:
        ValueError: If any event is missing the required 'id' field.
    """
    if not results:
        return "No events found matching the specified criteria."

    summaries = []
    for event in results:
        summary = f"Event: '{event.get('event_name')}'"
        if event.get('description'):
            summary += f", Description: '{event.get('description')}'"
        if event.get('city'):
            summary += f", Location: '{event.get('city')}'"
        if event.get('start_time'):
            summary += f", Starts on: '{event.get('start_time')}'"

        # ALWAYS use event.id for URL construction (REQUIRED field)
        event_id = event.get('id')
        if not event_id:
            raise ValueError(f"Event missing required 'id' field: {event}")

        utm_params = "utm_source=chatbot&utm_medium=ai&utm_campaign=event_search"
        summary += f", Link: {event_platform_base_url}/events/{event_id}?{utm_params}"

        summaries.append(summary)

    full_summary = " ".join(summaries)
    return f"Found {len(results)} events. Details: {full_summary}"


def _search_logic(
    query: Optional[str] = None,
    location: Optional[str] = None,
    date: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, str]:
    """
    Executes a dynamically generated SQL query to find events in the database.

    This tool uses a QueryGeneration module to convert the user's search criteria into a MySQL query.
    If the query fails due to a syntax error, it will attempt to correct itself up to 3 times.

    Args:
        query (Optional[str]): The semantic intent/main search term (e.g., "search music concert events" for user input "any music concert").
                               If not provided, will be constructed from other parameters.
        location (Optional[str]): The location to search for events.
        date (Optional[str]): The date or date range for the events.
        category (Optional[str]): The category of the event.

    Returns:
        A dictionary with a key 'events' containing a conclusive, natural-language summary of the findings.
    """
    # Construct semantic query if not provided
    if not query:
        query_parts = []
        if category:
            query_parts.append(f"search {category} events")
        if location:
            query_parts.append(f"in {location}")
        if date:
            query_parts.append(f"on {date}")

        query = " ".join(query_parts) if query_parts else "all events"
        print(f"Constructed semantic query from parameters: '{query}'")
    max_attempts = 3
    last_error = None
    previous_query = None

    event_platform_base_url = os.getenv("EVENT_PLATFORM_BASE_URL", "https://showeasy.ai")

    # Validate database configuration
    try:
        DatabaseConnectionPool()
    except ValueError as e:
        return {"error": str(e)}

    # --- Load or Generate Database Insights ---
    cache = InsightCache()
    cached_insights = cache.get_all_insights()

    # If any insights are missing, regenerate all
    if len(cached_insights) < len(InsightCache.INSIGHT_TYPES):
        print("Generating fresh database insights...")
        try:
            insights_generator = DatabaseInsights()
            all_insights = insights_generator.generate_all_insights()

            # Cache each insight type
            for insight_type, insight_data in all_insights.items():
                cache.set(insight_type, insight_data)

            cached_insights = all_insights
        except Exception as e:
            print(f"Error generating insights: {e}")
            cached_insights = {}

    # Compile insights into context summary for LLM
    db_context = ""
    if cached_insights:
        try:
            insights_generator = DatabaseInsights()
            db_context = insights_generator.compile_context_summary(cached_insights)
            print(f"Database Context:\n{db_context}")
        except Exception as e:
            print(f"Error compiling context: {e}")

    # --- Fuzzy Match Query to Categories (Layer 3) ---
    enriched_query = query
    if cached_insights.get('categories', {}).get('categories'):
        matched_category = CategoryMatcher.find_best_match(
            query, cached_insights['categories']['categories']
        )
        if matched_category:
            print(f"Fuzzy matched '{query}' to category '{matched_category}'")
            enriched_query = f"{query} (matched category: {matched_category})"

    for attempt in range(max_attempts):
        print(f"--- Query Generation Attempt {attempt + 1} of {max_attempts} ---")
        try:
            query_generator = QueryGeneration()
            search_input = SearchEventInput(
                query=enriched_query, location=location, date=date, category=category
            )
            generated_sql = query_generator(
                request=search_input,
                previous_query=previous_query,
                db_error=last_error,
                database_insights=db_context
            )
            
            if generated_sql.startswith("```sql"):
                generated_sql = generated_sql[6:]
            if generated_sql.endswith("```"):
                generated_sql = generated_sql[:-3]
            generated_sql = generated_sql.strip()
            previous_query = generated_sql

            print(f"Cleaned & Generated SQL Query: {generated_sql}")

            try:
                results = _execute_query(generated_sql)
                print("Query executed successfully!")

                # Format results with suggestions if empty
                if not results:
                    suggestions = []
                    if cached_insights.get('categories', {}).get('summary'):
                        suggestions.append(cached_insights['categories']['summary'])
                    if cached_insights.get('locations', {}).get('summary'):
                        suggestions.append(cached_insights['locations']['summary'])

                    base_message = "No events found matching the specified criteria."
                    if suggestions:
                        suggestion_text = " Try: " + ". ".join(suggestions)
                        return {"events": base_message + suggestion_text}
                    return {"events": base_message}

                # Format successful results
                formatted_results = _format_event_results(results, event_platform_base_url)
                return {"events": formatted_results}

            except mysql.connector.Error as err:
                print(f"Database Error on attempt {attempt + 1}: {err}")
                last_error = str(err)
        
        except Exception as e:
            print(f"An unexpected error occurred on attempt {attempt + 1}: {e}")
            last_error = str(e)

    print("All query generation attempts failed.")
    return {"error": f"Failed to generate a valid SQL query after {max_attempts} attempts. Last error: {last_error}"}


# Create a dspy.Tool instance from the search logic function.
SearchEvent = dspy.Tool(
    func=_search_logic,
    name="search_event",
    desc="""Search for events in the database based on user intent.

IMPORTANT: The 'query' parameter should capture the SEMANTIC INTENT of the user's request, not just keywords.

Examples of proper usage:
- User: "any music concert" → query="search music concert events" or query="music concerts"
- User: "art shows in SF" → query="art shows", location="San Francisco"
- User: "what's happening this weekend" → query="events", date="this weekend"
- User: "tech events" → query="tech events" or category="tech"

Parameters:
- query: The semantic intent/search term (e.g., "music concerts", "art exhibitions"). Can be omitted if category is specific enough.
- location: City or venue name
- date: Date or time range
- category: Event category

At least ONE parameter must be provided. If you have a category, you can omit query and it will be auto-generated."""
)
