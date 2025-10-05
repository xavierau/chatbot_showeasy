import dspy
from typing import Optional


class QueryGenerationSignature(dspy.Signature):
    """Given a user's request and a database schema, generate a valid and efficient MySQL query.

    The query should be designed to run on the provided database schema and answer the user's request.

    CRITICAL REQUIREMENTS - The query MUST select these columns with EXACT aliases:
    1. e.id AS id (REQUIRED for event identification)
    2. JSON_UNQUOTE(JSON_EXTRACT(e.slug, '$.en')) AS slug (REQUIRED for URL construction)
    3. JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')) AS event_name
    4. JSON_UNQUOTE(JSON_EXTRACT(e.description, '$.en')) AS description
    5. JSON_UNQUOTE(JSON_EXTRACT(v.city, '$.en')) AS city
    6. eo.start_at_utc AS start_time

    IMPORTANT: The query MUST be ordered by the event's start date in ascending order (eo.start_at_utc ASC)
    and MUST be limited to a maximum of 10 results using a LIMIT clause.
    """

    user_request: str = dspy.InputField(
        desc="A structured string representing the user's search criteria."
    )
    db_schema: str = dspy.InputField(desc="The simplified MySQL database schema.")
    database_insights: Optional[str] = dspy.InputField(
        desc="(Optional) Current database context with available categories, locations, and statistics to help generate relevant queries.",
        prefix="Database Context:"
    )
    previous_query: Optional[str] = dspy.InputField(
        desc="(Optional) The previously generated SQL query that failed.",
        prefix="Failed Query:"
    )
    db_error: Optional[str] = dspy.InputField(
        desc="(Optional) The error message returned from the database for the failed query.",
        prefix="Database Error:"
    )

    sql_query: str = dspy.OutputField(
        desc="A single, valid, and efficient MySQL query that answers the user's request based on the schema, including an ORDER BY and a LIMIT clause."
    )
