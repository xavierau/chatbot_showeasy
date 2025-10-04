import dspy
from typing import Optional


class QueryGenerationSignature(dspy.Signature):
    """Given a user's request and a database schema, generate a valid and efficient MySQL query.

    The query should be designed to run on the provided database schema and answer the user's request.
    IMPORTANT: The query MUST select the following columns with these exact aliases: event name as `event_name`, description as `description`, city as `city`, and start time as `start_time` (e.g., `JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')) as event_name`).
    IMPORTANT: The query MUST be ordered by the event's start date in ascending order (eo.start_at_utc ASC)
    and MUST be limited to a maximum of 10 results using a LIMIT clause.
    """

    user_request: str = dspy.InputField(
        desc="A structured string representing the user's search criteria."
    )
    db_schema: str = dspy.InputField(desc="The simplified MySQL database schema.")
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
