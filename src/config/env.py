"""
Centralized environment configuration loader.

This module provides a single source of truth for loading environment variables
from the .env file. It ensures the .env file is loaded once at application startup
with an explicit path to avoid path resolution issues.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """
    Load environment variables from .env file.

    This function locates the project root (where .env resides) and loads
    environment variables. It should be called once at application startup
    before any other configuration modules are imported.

    The project structure is assumed to be:
    /project_root
        /.env
        /src
            /config
                /env.py (this file)
    """
    # Get the directory where this file (env.py) is located
    current_file = Path(__file__).resolve()

    # Navigate up to project root: src/config/env.py -> src/config -> src -> project_root
    project_root = current_file.parent.parent.parent

    # Construct path to .env file
    env_file = project_root / '.env'

    # Load environment variables
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
        print(f"✓ Environment loaded from: {env_file}")
    else:
        print(f"⚠ Warning: .env file not found at {env_file}")
        print("  Continuing with system environment variables only.")


# Expose the function
__all__ = ["load_environment"]
