from __future__ import annotations
from typing import Any, Optional
import logging

from .postgres import PostgresClient
from .oracle import OracleClient


class DBManager:
    """
    High-level interface to interact with supported databases.
    
    Example:
        pg = DBManager("postgres")
        conn = pg.connector(user="u", password="p", database="d")
        pg.read(query="SELECT * FROM tabela")
    """

    _CLIENTS = {
        "postgres": PostgresClient,
        "oracle": OracleClient,
    }

    def __init__(self, engine: str):
        self.engine = engine.lower()
        if self.engine not in self._CLIENTS:
            raise ValueError(f"Unsupported database engine: {engine}")
        self._client_class = self._CLIENTS[self.engine]
        self._client = None
        self.logger = logging.getLogger(self.__class__.__name__)

    # ---------- Connection Handling ----------

    def connector(
        self,
        user: str,
        password: str,
        database: str,
        host: str = "localhost",
        port: Optional[int] = None,
        role: Optional[str] = None,
    ) -> Any:
        """Create and store a connection client."""
        self._client = self._client_class(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port,
            role=role,
        )
        self.logger.info(f"Connected to {self.engine} database: {database}")
        return self._client

    # ---------- Delegation Methods ----------

    def read(self, *args, **kwargs) -> Any:
        """Read from the active database connection."""
        self._ensure_client()
        return self._client.read(*args, **kwargs)

    def merge(self, *args, **kwargs) -> Any:
        """Perform a merge operation on the active database."""
        self._ensure_client()
        return self._client.merge(*args, **kwargs)

    def close(self) -> None:
        """Close the active connection, if any."""
        if self._client and hasattr(self._client, "close"):
            self._client.close()
            self.logger.info("Database connection closed.")

    # ---------- Private helpers ----------

    def _ensure_client(self):
        if not self._client:
            raise RuntimeError(
                "No active client. You must call `.connector()` before performing operations."
            )
