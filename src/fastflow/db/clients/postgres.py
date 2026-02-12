from __future__ import annotations
import psycopg2
import psycopg2.extras
import pandas as pd
import io
import logging
from typing import Any, Optional


class PostgresClient:
    """
    PostgreSQL Client for FastFlow.

    Provides basic connection management, query execution and merge operations.
    Designed to be used through the DBManager interface.
    """

    DEFAULT_PORT = 5432

    def __init__(
        self,
        user: str,
        password: str,
        database: str,
        host: str = "localhost",
        port: Optional[int] = None,
        role: Optional[str] = None,
    ):
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port or self.DEFAULT_PORT
        self.role = role
        self.conn = None
        self.logger = logging.getLogger(self.__class__.__name__)

    # ---------- Connection Handling ----------

    def connector(self):
        """Create a psycopg2 connection and store it in self.conn."""
        if self.conn and not self.conn.closed:
            return self.conn
        try:
            self.conn = psycopg2.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database,
            )
            self.logger.info(f"Connected to PostgreSQL database '{self.database}' on {self.host}.")
            return self.conn
        except Exception as e:
            self.logger.error(f"Error connecting to PostgreSQL: {e}")
            raise

    def close(self):
        """Close the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.logger.info("PostgreSQL connection closed.")

    # ---------- Read ----------

    def read(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        connector: Optional[Any] = None,
        fetch_size: Optional[int] = None,
    ):
        """Execute a query and return results as list of dicts."""
        conn = connector or self.connector()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if not query:
            if not table:
                raise ValueError("Either 'query' or 'table' must be provided.")
            query = f"SELECT * FROM {table}"

        self.logger.info(f"Executing query on PostgreSQL: {query}")
        cursor.execute(query)

        if fetch_size:
            rows = cursor.fetchmany(fetch_size)
        else:
            rows = cursor.fetchall()

        cursor.close()
        return list(rows)

    # ---------- Merge ----------

    def merge(
        self,
        table: str,
        data: pd.DataFrame | list[dict],
        key_columns: list[str],
        update_columns: list[str],
        connector: Optional[Any] = None,
        mode: str = "merge",
    ):
        """
        Merge or replace rows into a target table.

        mode='merge' → perform UPSERT
        mode='replace' → delete matching rows and reinsert
        """
        import uuid

        conn = connector or self.connector()
        cur = conn.cursor()
        tmp_table = f"{table}_tmp_{uuid.uuid4().hex[:6]}"
        self.logger.info(f"Creating temporary table {tmp_table}")

        df = pd.DataFrame(data)
        if df.empty:
            self.logger.warning("No data provided to merge; skipping operation.")
            return

        # Create temp table
        cur.execute(f"CREATE TEMP TABLE {tmp_table} (LIKE {table} INCLUDING ALL);")

        # Load data into temp table
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, header=False)
        buffer.seek(0)
        cur.copy_expert(f"COPY {tmp_table} FROM STDIN WITH CSV", buffer)

        if mode == "merge":
            set_clause = ", ".join([f"{col}=EXCLUDED.{col}" for col in update_columns])
            keys = ", ".join(key_columns)
            sql = f"""
                INSERT INTO {table} SELECT * FROM {tmp_table}
                ON CONFLICT ({keys}) DO UPDATE SET {set_clause};
            """
        elif mode == "replace":
            where = " AND ".join([f"t.{k}=tmp.{k}" for k in key_columns])
            sql = f"""
                DELETE FROM {table} t USING {tmp_table} tmp WHERE {where};
                INSERT INTO {table} SELECT * FROM {tmp_table};
            """
        else:
            raise ValueError("mode must be 'merge' or 'replace'")

        self.logger.info(f"Running merge in mode='{mode}'")
        cur.execute(sql)
        cur.execute(f"DROP TABLE {tmp_table}")
        conn.commit()
        cur.close()
        self.logger.info(f"Merge operation completed successfully for table {table}.")
