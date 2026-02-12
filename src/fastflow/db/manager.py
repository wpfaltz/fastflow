from __future__ import annotations
from typing import Any, Mapping
from .clients.base import DBManager
from .clients.postgres import PostgresClient
from .clients.oracle import OracleClient

def _build_postgres(**kw) -> DBManager:
    from .clients.postgres import PostgresClient
    return PostgresClient(**kw)

def _build_oracle(**kw) -> DBManager:
    from .clients.oracle import OracleClient
    return OracleClient(**kw)

_BUILDERS = {
    "postgres": _build_postgres,
    "oracle": _build_oracle,
}

class DBManager:
    def __init__(self, client: BaseDBClient):
        self._client = client

    @classmethod
    def from_config(cls, engine: str, **cfg) -> "DBManager":
        engine = engine.lower()
        if engine not in _BUILDERS:
            raise ValueError(f"Engine não suportado: {engine}")
        client = _BUILDERS[engine](**cfg)
        return cls(client)

    def read(self, sql: str, params: Mapping[str, Any] | None = None):
        return self._client.read(sql, params)

    def write(self, table: str, data: Any, if_exists: str = "append") -> int:
        return self._client.write(table, data, if_exists)

    def close(self) -> None:
        self._client.close()
