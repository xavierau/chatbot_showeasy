import os
import dspy
from langfuse import get_client
from openinference.instrumentation.dspy import DSPyInstrumentor


def configure_llm():
    """
    Configures the language model for dspy.

    Sets up the default LLM provider and model based on environment variables.
    Environment variables should be loaded before calling this function.
    """
    llm_provider = os.getenv("DSPY_LLM_DEFAULT_PROVIDER")
    llm_model = os.getenv("DSPY_LLM_DEFAULT_MODEL")

    langfuse = get_client()

    # Verify connection (non-blocking - don't crash on failure)
    try:
        if langfuse.auth_check():
            print("Langfuse client is authenticated and ready!")
        else:
            print("Warning: Langfuse authentication failed. Tracing may not work.")
    except Exception as e:
        print(f"Warning: Could not connect to Langfuse: {e}. Continuing without tracing.")

    DSPyInstrumentor().instrument()

    if llm_provider == "gemini":
        lm = dspy.LM(f"{llm_provider}/{llm_model}", api_key=os.getenv('GOOGLE_API_KEY'))
        dspy.configure(lm=lm)
    elif llm_provider == "azure":
        api_key = os.getenv("AZURE_API_KEY")
        api_base = os.getenv("AZURE_API_BASE")
        api_version = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")

        lm = dspy.LM(
            f"azure/{llm_model}",
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            stream=False
        )
        dspy.configure(lm=lm)
    else:
        raise NotImplementedError(f"LLM provider '{llm_provider}' is not supported.")
