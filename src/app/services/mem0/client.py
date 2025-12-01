"""
Mem0 Client Factory

This module provides a factory function for initializing and configuring
the Mem0 memory client with support for multiple LLM providers, embedders,
and vector stores.

Design Patterns:
- Factory Pattern: Creates configured Mem0 instances
- Configuration Object: Encapsulates all configuration options
- Singleton-like: Typically one client per application

Usage:
    from app.services.mem0 import get_mem0_client, Mem0Config

    # Default configuration (uses environment variables)
    memory = get_mem0_client()

    # Custom configuration
    config = Mem0Config(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        vector_store_provider="qdrant",
    )
    memory = get_mem0_client(config)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal

from mem0 import Memory

logger = logging.getLogger(__name__)

# Type aliases for supported providers
LLMProvider = Literal["openai", "azure", "azure_openai", "gemini", "anthropic", "groq"]
EmbedderProvider = Literal["openai", "azure", "azure_openai", "huggingface", "gemini"]
VectorStoreProvider = Literal["qdrant", "chroma", "pinecone", "pgvector", "milvus"]


@dataclass
class Mem0Config:
    """
    Configuration object for Mem0 client initialization.

    This class encapsulates all configuration options for the Mem0 memory system,
    including LLM, embedder, and vector store settings. It supports loading
    defaults from environment variables.

    Attributes:
        llm_provider: LLM provider (openai, azure, gemini, anthropic, groq)
        llm_model: Model name for the LLM
        llm_temperature: Temperature for LLM responses
        llm_max_tokens: Maximum tokens for LLM responses
        llm_api_key: API key for LLM provider (defaults to env var)

        embedder_provider: Embedding provider (openai, azure, huggingface, gemini)
        embedder_model: Model name for embeddings
        embedder_api_key: API key for embedder (defaults to env var)
        embedding_dims: Dimension of embedding vectors

        vector_store_provider: Vector store provider (qdrant, chroma, pinecone, etc.)
        vector_store_host: Host for vector store
        vector_store_port: Port for vector store
        vector_store_collection: Collection/index name
        vector_store_api_key: API key for vector store (if required)
        vector_store_path: Path for file-based vector stores (like Chroma)

        version: Mem0 API version
        custom_prompt: Custom prompt for memory extraction
    """

    # LLM Configuration
    llm_provider: LLMProvider = field(
        default_factory=lambda: os.getenv("MEM0_LLM_PROVIDER", "openai")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("MEM0_LLM_MODEL", "gpt-4o-mini")
    )
    llm_temperature: float = field(
        default_factory=lambda: float(os.getenv("MEM0_LLM_TEMPERATURE", "0.1"))
    )
    llm_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("MEM0_LLM_MAX_TOKENS", "2000"))
    )
    llm_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("MEM0_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    )

    # Azure-specific LLM config
    azure_api_base: Optional[str] = field(
        default_factory=lambda: os.getenv("MEM0_AZURE_API_BASE") or os.getenv("AZURE_API_BASE")
    )
    azure_api_version: Optional[str] = field(
        default_factory=lambda: os.getenv("MEM0_AZURE_API_VERSION", "2024-02-01")
    )

    # Gemini-specific config
    google_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY")
    )

    # Embedder Configuration
    embedder_provider: EmbedderProvider = field(
        default_factory=lambda: os.getenv("MEM0_EMBEDDER_PROVIDER", "openai")
    )
    embedder_model: str = field(
        default_factory=lambda: os.getenv("MEM0_EMBEDDER_MODEL", "text-embedding-3-small")
    )
    embedder_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("MEM0_EMBEDDER_API_KEY") or os.getenv("OPENAI_API_KEY")
    )
    embedding_dims: int = field(
        default_factory=lambda: int(os.getenv("MEM0_EMBEDDING_DIMS", "1536"))
    )

    # Vector Store Configuration
    vector_store_provider: VectorStoreProvider = field(
        default_factory=lambda: os.getenv("MEM0_VECTOR_STORE_PROVIDER", "chroma")
    )
    vector_store_host: str = field(
        default_factory=lambda: os.getenv("MEM0_VECTOR_STORE_HOST", "localhost")
    )
    vector_store_port: int = field(
        default_factory=lambda: int(os.getenv("MEM0_VECTOR_STORE_PORT", "6333"))
    )
    vector_store_collection: str = field(
        default_factory=lambda: os.getenv("MEM0_VECTOR_STORE_COLLECTION", "showeasy_memories")
    )
    vector_store_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("MEM0_VECTOR_STORE_API_KEY")
    )
    vector_store_path: str = field(
        default_factory=lambda: os.getenv("MEM0_VECTOR_STORE_PATH", "./chroma_db")
    )

    # General Configuration
    version: str = field(default_factory=lambda: os.getenv("MEM0_VERSION", "v1.1"))
    custom_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to Mem0-compatible dictionary format."""
        config: Dict[str, Any] = {"version": self.version}

        # Build LLM configuration
        config["llm"] = self._build_llm_config()

        # Build Embedder configuration
        config["embedder"] = self._build_embedder_config()

        # Build Vector Store configuration
        config["vector_store"] = self._build_vector_store_config()

        # Add custom prompt if provided
        if self.custom_prompt:
            config["custom_prompt"] = self.custom_prompt

        return config

    def _build_llm_config(self) -> Dict[str, Any]:
        """Build LLM configuration section."""
        llm_config: Dict[str, Any] = {
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "max_tokens": self.llm_max_tokens,
        }

        provider = self.llm_provider
        if self.llm_provider in ("azure", "azure_openai"):
            # Use azure_openai provider (not azure_openai_structured which has a bug in v1.0.1)
            provider = "azure_openai"
            azure_kwargs: Dict[str, Any] = {
                "azure_deployment": self.llm_model,
            }
            if self.llm_api_key:
                azure_kwargs["api_key"] = self.llm_api_key
            if self.azure_api_base:
                azure_kwargs["azure_endpoint"] = self.azure_api_base
            if self.azure_api_version:
                azure_kwargs["api_version"] = self.azure_api_version
            llm_config["azure_kwargs"] = azure_kwargs
        elif self.llm_provider == "gemini":
            llm_config["api_key"] = self.google_api_key
        else:
            if self.llm_api_key:
                llm_config["api_key"] = self.llm_api_key

        return {"provider": provider, "config": llm_config}

    def _build_embedder_config(self) -> Dict[str, Any]:
        """Build embedder configuration section."""
        embedder_config: Dict[str, Any] = {"model": self.embedder_model}

        if self.embedder_provider in ("azure", "azure_openai"):
            # Mem0 uses azure_kwargs for Azure OpenAI embedder configuration
            azure_kwargs: Dict[str, Any] = {}
            if self.embedder_api_key:
                azure_kwargs["api_key"] = self.embedder_api_key
            if self.azure_api_base:
                azure_kwargs["azure_endpoint"] = self.azure_api_base
            if self.azure_api_version:
                azure_kwargs["api_version"] = self.azure_api_version
            # Use model name as deployment name if not specified separately
            azure_kwargs["azure_deployment"] = self.embedder_model
            embedder_config["azure_kwargs"] = azure_kwargs
        elif self.embedder_provider == "gemini":
            embedder_config["api_key"] = self.google_api_key
        else:
            if self.embedder_api_key:
                embedder_config["api_key"] = self.embedder_api_key

        return {"provider": self.embedder_provider, "config": embedder_config}

    def _build_vector_store_config(self) -> Dict[str, Any]:
        """Build vector store configuration section."""
        vs_config: Dict[str, Any] = {
            "collection_name": self.vector_store_collection,
            "embedding_model_dims": self.embedding_dims,
        }

        if self.vector_store_provider == "qdrant":
            vs_config["host"] = self.vector_store_host
            vs_config["port"] = self.vector_store_port
            if self.vector_store_api_key:
                vs_config["api_key"] = self.vector_store_api_key

        elif self.vector_store_provider == "chroma":
            vs_config["path"] = self.vector_store_path

        elif self.vector_store_provider == "pinecone":
            if self.vector_store_api_key:
                vs_config["api_key"] = self.vector_store_api_key

        elif self.vector_store_provider == "pgvector":
            vs_config["host"] = self.vector_store_host
            vs_config["port"] = self.vector_store_port

        elif self.vector_store_provider == "milvus":
            vs_config["host"] = self.vector_store_host
            vs_config["port"] = self.vector_store_port

        return {"provider": self.vector_store_provider, "config": vs_config}


def get_mem0_client(config: Optional[Mem0Config] = None) -> Memory:
    """
    Factory function to create and configure a Mem0 Memory client.

    This function initializes a Mem0 Memory instance with the provided
    configuration or defaults from environment variables. It supports
    multiple LLM providers, embedders, and vector stores.

    Args:
        config: Optional Mem0Config object. If not provided, defaults
                are loaded from environment variables.

    Returns:
        Configured Memory instance ready for use.

    Raises:
        ValueError: If required configuration is missing.
        ConnectionError: If unable to connect to vector store.

    Example:
        # Using defaults from environment
        memory = get_mem0_client()

        # Using custom configuration
        config = Mem0Config(
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            vector_store_provider="qdrant",
            vector_store_host="localhost",
            vector_store_port=6333,
        )
        memory = get_mem0_client(config)
    """
    if config is None:
        config = Mem0Config()

    # Validate configuration
    _validate_config(config)

    # Convert to dictionary format
    config_dict = config.to_dict()

    logger.info(
        f"Initializing Mem0 client with LLM={config.llm_provider}/{config.llm_model}, "
        f"Embedder={config.embedder_provider}/{config.embedder_model}, "
        f"VectorStore={config.vector_store_provider}"
    )
    logger.debug(f"Full Mem0 config: {_sanitize_config_for_logging(config_dict)}")

    # Create Memory instance
    memory = Memory.from_config(config_dict)

    logger.info("Mem0 client initialized successfully")
    return memory


def _validate_config(config: Mem0Config) -> None:
    """
    Validate the Mem0 configuration.

    Args:
        config: Configuration to validate.

    Raises:
        ValueError: If required configuration is missing.
    """
    # Validate LLM API key based on provider
    if config.llm_provider in ("openai", "anthropic", "groq"):
        if not config.llm_api_key:
            raise ValueError(
                f"API key required for LLM provider '{config.llm_provider}'. "
                f"Set MEM0_LLM_API_KEY or OPENAI_API_KEY environment variable."
            )
    elif config.llm_provider in ("azure", "azure_openai"):
        if not config.llm_api_key or not config.azure_api_base:
            raise ValueError(
                "Azure OpenAI requires both API key and API base. "
                "Set MEM0_LLM_API_KEY and MEM0_AZURE_API_BASE environment variables."
            )
    elif config.llm_provider == "gemini":
        if not config.google_api_key:
            raise ValueError(
                "Google API key required for Gemini. "
                "Set GOOGLE_API_KEY environment variable."
            )

    # Validate embedder API key
    if config.embedder_provider in ("openai", "azure", "azure_openai"):
        if not config.embedder_api_key:
            raise ValueError(
                f"API key required for embedder provider '{config.embedder_provider}'. "
                f"Set MEM0_EMBEDDER_API_KEY or OPENAI_API_KEY environment variable."
            )

    # Validate vector store specific requirements
    if config.vector_store_provider == "pinecone":
        if not config.vector_store_api_key:
            raise ValueError(
                "Pinecone API key required. "
                "Set MEM0_VECTOR_STORE_API_KEY environment variable."
            )


def _sanitize_config_for_logging(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive information from config for logging.

    Args:
        config: Configuration dictionary.

    Returns:
        Sanitized configuration safe for logging.
    """
    import copy

    sanitized = copy.deepcopy(config)

    # Mask API keys
    sensitive_keys = ["api_key", "api_base"]
    for section in ["llm", "embedder", "vector_store"]:
        if section in sanitized and "config" in sanitized[section]:
            for key in sensitive_keys:
                if key in sanitized[section]["config"]:
                    value = sanitized[section]["config"][key]
                    if value:
                        sanitized[section]["config"][key] = f"{value[:8]}...{value[-4:]}"

    return sanitized
