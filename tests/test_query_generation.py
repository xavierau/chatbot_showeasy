import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app.llm.modules import QueryGeneration
from app.models import SearchEventInput
from config import configure_llm


def main():
    """Main function to run the QueryGeneration test."""
    # Configure the language model
    print("Configuring language model...")
    configure_llm()

    # Instantiate the query generator
    print("Instantiating QueryGeneration module...")
    query_generator = QueryGeneration()

    # Simulate a user's search request
    print("Simulating user input...")
    user_search_request = SearchEventInput(
        query="tech conferences",
        location="San Francisco",
        date="next month",
        category="Technology"
    )

    # Generate the SQL query
    print("Generating SQL query...")
    generated_sql = query_generator(request=user_search_request)

    # Print the results
    print("\n--- User Search Request ---")
    print(user_search_request.model_dump_json(indent=2))
    print("\n--- Generated SQL Query ---")
    print(generated_sql)
    print("\n")


if __name__ == "__main__":
    main()
