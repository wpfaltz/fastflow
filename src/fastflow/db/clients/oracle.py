from __future__ import annotations
# import oracledb
import pandas as pd
import io
import uuid
import logging
from typing import Any, Optional


class OracleClient:
    """
    Oracle Database Client for FastFlow.

    Provides connection handling, read and merge operations using Oracle SQL.
    """

    DEFAULT_PORT = 1521

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
        """Establish an Oracle connection."""
        if self.conn:
            return self.conn
        try:
            dsn = oracledb.makedsn(self.host, self.port, service_name=self.database)
            self.conn = oracledb.connect(user=self.user, password=self.password, dsn=dsn)
            self.logger.info(f"Connected to Oracle database '{self.database}' at {self.host}.")
            return self.conn
        except Exception as e:
            self.logger.error(f"Error connecting to Oracle: {e}")
            raise

    def close(self):
        """Close the Oracle connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Oracle connection closed.")

    # ---------- Read ----------

    def read(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        connector: Optional[Any] = None,
        fetch_size: Optional[int] = None,
    ):
        """Execute a query and return all results."""
        conn = connector or self.connector()
        cur = conn.cursor()

        if not query:
            if not table:
                raise ValueError("Either 'query' or 'table' must be provided.")
            query = f"SELECT * FROM {table}"

        self.logger.info(f"Executing Oracle query: {query}")
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        if fetch_size:
            rows = cur.fetchmany(fetch_size)
        else:
            rows = cur.fetchall()
        cur.close()
        return [dict(zip(columns, row)) for row in rows]

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
        Perform a MERGE or REPLACE operation in Oracle.

        mode='merge' → use Oracle MERGE INTO
        mode='replace' → delete then insert
        """
        conn = connector or self.connector()
        cur = conn.cursor()
        df = pd.DataFrame(data)
        if df.empty:
            self.logger.warning("No data provided to merge; skipping operation.")
            return

        tmp_table = f"{table}_TMP_{uuid.uuid4().hex[:6]}"
        cols = ", ".join(df.columns)

        # Create temporary table
        self.logger.info(f"Creating temporary table {tmp_table}")
        cur.execute(f"CREATE GLOBAL TEMPORARY TABLE {tmp_table} AS SELECT * FROM {table} WHERE 1=0")

        # Insert data into temp table
        placeholders = ", ".join([":" + str(i + 1) for i in range(len(df.columns))])
        insert_sql = f"INSERT INTO {tmp_table} ({cols}) VALUES ({placeholders})"
        cur.executemany(insert_sql, df.itertuples(index=False, name=None))
        conn.commit()

        if mode == "merge":
            on_clause = " AND ".join([f"t.{k}=s.{k}" for k in key_columns])
            set_clause = ", ".join([f"t.{col}=s.{col}" for col in update_columns])
            merge_sql = f"""
                MERGE INTO {table} t
                USING {tmp_table} s
                ON ({on_clause})
                WHEN MATCHED THEN UPDATE SET {set_clause}
                WHEN NOT MATCHED THEN INSERT ({cols}) VALUES ({', '.join(['s.' + c for c in df.columns])})
            """
        elif mode == "replace":
            where = " AND ".join([f"t.{k}=s.{k}" for k in key_columns])
            merge_sql = f"""
                DELETE FROM {table} t WHERE EXISTS (
                    SELECT 1 FROM {tmp_table} s WHERE {where}
                )
            """
            cur.execute(merge_sql)
            insert_sql = f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {tmp_table}"
            cur.execute(insert_sql)
        else:
            raise ValueError("mode must be 'merge' or 'replace'")

        self.logger.info(f"Running merge in mode='{mode}'")
        cur.execute(merge_sql)
        conn.commit()

        # Drop temp table
        cur.execute(f"DROP TABLE {tmp_table} PURGE")
        conn.commit()
        cur.close()
        self.logger.info(f"Merge completed successfully for table {table}.")
