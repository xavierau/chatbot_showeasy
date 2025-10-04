import os
import dspy
from dotenv import load_dotenv
from langfuse import get_client
from openinference.instrumentation.dspy import DSPyInstrumentor


def configure_llm():
    """
    Configures the language model for dspy.

    Loads configuration from the .env file and sets up the default LLM
    provider and model.
    """
    load_dotenv()

    llm_provider = os.getenv("DSPY_LLM_DEFAULT_PROVIDER")
    llm_model = os.getenv("DSPY_LLM_DEFAULT_MODEL")

    langfuse = get_client()

    # Verify connection
    if langfuse.auth_check():
        print("Langfuse client is authenticated and ready!")
    else:
        print("Authentication failed. Please check your credentials and host.")

    DSPyInstrumentor().instrument()

    if llm_provider == "gemini":
        lm = dspy.LM(f"{llm_provider}/{llm_model}", api_key=f"{os.getenv('GOOGLE_API_KEY')}")
        dspy.configure(lm=lm)
    else:
        raise NotImplementedError(f"LLM provider '{llm_provider}' is not supported.")
