import dspy
import os
import mysql.connector
from typing import Optional, Dict

# Import the necessary models and, specifically, the QueryGeneration CLASS
from app.models import SearchEventInput
from app.llm.modules.QueryGeneration import QueryGeneration


def _search_logic(
    query: str,
    location: Optional[str] = None,
    date: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, str]:
    """Executes a dynamically generated SQL query to find events in the database.

    This tool uses a QueryGeneration module to convert the user's search criteria into a MySQL query.
    If the query fails due to a syntax error, it will attempt to correct itself up to 2 times.

    Args:
        query (str): The main search term for events.
        location (Optional[str]): The location to search for events.
        date (Optional[str]): The date or date range for the events.
        category (Optional[str]): The category of the event.

    Returns:
        A dictionary with a key \'events\' containing a conclusive, natural-language summary of the findings.
    """
    max_attempts = 3
    last_error = None
    previous_query = None

    # --- Database Environment Variable Check (moved outside the loop) ---
    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    event_platform_base_url = os.getenv("EVENT_PLATFORM_BASE_URL", "https://eventplatform.test")

    if not all([db_host, db_user, db_password, db_name]):
        return {"error": "Database environment variables are not set. Cannot perform search."}

    for attempt in range(max_attempts):
        print(f"--- Query Generation Attempt {attempt + 1} of {max_attempts} ---")
        try:
            query_generator = QueryGeneration()
            search_input = SearchEventInput(
                query=query, location=location, date=date, category=category
            )
            generated_sql = query_generator(
                request=search_input, 
                previous_query=previous_query, 
                db_error=last_error
            )
            
            if generated_sql.startswith("```sql"):
                generated_sql = generated_sql[6:]
            if generated_sql.endswith("```"):
                generated_sql = generated_sql[:-3]
            generated_sql = generated_sql.strip()
            previous_query = generated_sql

            print(f"Cleaned & Generated SQL Query: {generated_sql}")

            connection = None
            try:
                connection = mysql.connector.connect(
                    host=db_host, user=db_user, password=db_password, database=db_name
                )
                # Use a dictionary cursor to get results with column names
                cursor = connection.cursor(dictionary=True)
                cursor.execute(generated_sql)
                results = cursor.fetchall()
                
                print("Query executed successfully!")
                
                # --- New Rich & Conclusive Output Formatting ---
                if not results:
                    return {"events": "No events found matching the specified criteria."}
                else:
                    summaries = []
                    for event in results:
                        summary = f"Event: '{event.get('event_name')}'"
                        if event.get('description'):
                            summary += f", Description: '{event.get('description')}'"
                        if event.get('city'):
                            summary += f", Location: '{event.get('city')}'"
                        if event.get('start_time'):
                            summary += f", Starts on: '{event.get('start_time')}'"

                        # Generate URL with UTM tracking - use slug if available, otherwise use id
                        event_identifier = event.get('slug') or event.get('id')
                        if event_identifier:
                            utm_params = "utm_source=chatbot&utm_medium=ai&utm_campaign=event_search"
                            summary += f", Link: {event_platform_base_url}/events/{event_identifier}?{utm_params}"

                        summaries.append(summary)

                    full_summary = " ".join(summaries)
                    return {"events": f"Found {len(results)} events. Details: {full_summary}"}\

            except mysql.connector.Error as err:
                print(f"Database Error on attempt {attempt + 1}: {err}")
                last_error = str(err)

            finally:
                if connection and connection.is_connected():
                    cursor.close()
                    connection.close()
        
        except Exception as e:
            print(f"An unexpected error occurred on attempt {attempt + 1}: {e}")
            last_error = str(e)

    print("All query generation attempts failed.")
    return {"error": f"Failed to generate a valid SQL query after {max_attempts} attempts. Last error: {last_error}"}\


# Create a dspy.Tool instance from the search logic function.
SearchEvent = dspy.Tool(func=_search_logic, name="search_event")
