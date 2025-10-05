"""
Database configuration and connection management.

This module provides centralized database configuration and connection pooling
following SOLID principles and separation of concerns.
"""
import os
from dataclasses import dataclass
from typing import Optional
import mysql.connector
from mysql.connector import pooling


@dataclass(frozen=True)
class DatabaseConfig:
    """Immutable database configuration."""

    host: str
    user: str
    password: str
    name: str
    port: int = 3306

    @classmethod
    def from_env(cls) -> Optional['DatabaseConfig']:
        """
        Load database configuration from environment variables.

        Returns:
            DatabaseConfig if all required variables are set, None otherwise.
        """
        host = os.getenv("DB_HOST")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        name = os.getenv("DB_NAME")
        port = int(os.getenv("DB_PORT", "3306"))

        if not all([host, user, password, name]):
            return None

        return cls(
            host=host,
            user=user,
            password=password,
            name=name,
            port=port
        )


class DatabaseConnectionPool:
    """
    Singleton connection pool for database operations.

    This class implements the Singleton pattern to ensure only one connection
    pool exists throughout the application lifecycle, improving performance
    and resource management.
    """

    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the connection pool if not already initialized."""
        if self._pool is None:
            config = DatabaseConfig.from_env()
            if config is None:
                raise ValueError(
                    "Database configuration is incomplete. "
                    "Ensure DB_HOST, DB_USER, DB_PASSWORD, and DB_NAME are set."
                )

            self._pool = pooling.MySQLConnectionPool(
                pool_name="event_pool",
                pool_size=5,
                pool_reset_session=True,
                host=config.host,
                user=config.user,
                password=config.password,
                database=config.name,
                port=config.port
            )

    def get_connection(self):
        """
        Get a connection from the pool.

        Returns:
            A MySQL connection object from the pool.

        Raises:
            ValueError: If the pool is not initialized.
        """
        if self._pool is None:
            raise ValueError("Connection pool not initialized")
        return self._pool.get_connection()


__all__ = ["DatabaseConfig", "DatabaseConnectionPool"]
