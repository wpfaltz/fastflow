from __future__ import annotations
# import oracledb
import pandas as pd
import io
import uuid
import logging
from typing import Any, Optional


class OracleClient:
    """Client de banco de dados Oracle para o FastFlow.

    Fornece gerenciamento de conexão, operações de leitura (SELECT) e
    operações de merge (MERGE INTO / DELETE+INSERT) utilizando SQL Oracle.
    Utiliza o driver ``oracledb`` para comunicação com o servidor Oracle.

    O client mantém uma conexão persistente (``self.conn``) que é
    estabelecida de forma lazy pelo método ``connector`` e reutilizada
    nas operações subsequentes.

    Attributes:
        DEFAULT_PORT: Porta padrão do Oracle (1521).
        user: Nome de usuário para autenticação.
        password: Senha para autenticação.
        database: Service name do banco de dados Oracle.
        host: Endereço do servidor.
        port: Porta de conexão.
        role: Role opcional do banco.
        conn: Objeto de conexão ativo ou ``None``.
        logger: Logger da classe.
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
        """Inicializa o OracleClient com as credenciais de conexão.

        Armazena os parâmetros de conexão sem estabelecer a conexão
        imediatamente. A conexão será criada de forma lazy na primeira
        chamada a ``connector``.

        Args:
            user: Nome de usuário para autenticação no Oracle.
            password: Senha para autenticação.
            database: Service name do banco de dados Oracle.
            host: Endereço do servidor Oracle. Padrão: ``"localhost"``.
            port: Porta de conexão. Se ``None``, utiliza ``DEFAULT_PORT``
                (1521).
            role: Role opcional a ser utilizada na sessão.
        """
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
        """Estabelece uma conexão com o banco de dados Oracle.

        Utiliza ``oracledb.makedsn`` para construir o DSN (Data Source Name)
        a partir de ``host``, ``port`` e ``database`` (service name) e, em
        seguida, abre a conexão via ``oracledb.connect``. Se já existir uma
        conexão ativa, retorna a conexão existente sem criar uma nova.

        Returns:
            Objeto de conexão ``oracledb.Connection``.

        Raises:
            Exception: Propaga qualquer erro de conexão lançado pelo driver
                ``oracledb``.
        """
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
        """Encerra a conexão com o banco de dados Oracle.

        Fecha a conexão armazenada em ``self.conn``, se houver uma conexão
        ativa, liberando os recursos de rede e do servidor.
        """
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
        """Executa uma consulta SQL no Oracle e retorna os resultados.

        Se nenhuma ``query`` for fornecida, gera automaticamente um
        ``SELECT * FROM <table>``. Os resultados são retornados como uma
        lista de dicionários, onde as chaves correspondem aos nomes das
        colunas.

        Args:
            query: Instrução SQL a ser executada. Se ``None``, o parâmetro
                ``table`` será utilizado para gerar uma query padrão.
            table: Nome da tabela para gerar ``SELECT *``. Utilizado
                apenas quando ``query`` é ``None``.
            connector: Conexão Oracle externa opcional. Se ``None``,
                utiliza a conexão interna (``self.connector()``).
            fetch_size: Quantidade máxima de linhas a buscar. Se ``None``,
                busca todas as linhas (``fetchall``).

        Returns:
            Lista de dicionários, cada um representando uma linha do
            resultado, com chaves iguais aos nomes das colunas.

        Raises:
            ValueError: Se nem ``query`` nem ``table`` forem fornecidos.
        """
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
        """Realiza uma operação de MERGE ou REPLACE em uma tabela Oracle.

        Cria uma tabela temporária global, carrega os dados nela, e então
        executa a estratégia escolhida:

        - ``mode='merge'``: Utiliza ``MERGE INTO`` para inserir linhas novas
          e atualizar linhas existentes com base nas ``key_columns``.
        - ``mode='replace'``: Remove as linhas correspondentes da tabela
          de destino e insere todos os dados da tabela temporária.

        Após a operação, a tabela temporária é descartada com ``DROP ... PURGE``.

        Args:
            table: Nome da tabela de destino no Oracle.
            data: Dados a serem mesclados. Aceita ``pd.DataFrame`` ou lista
                de dicionários.
            key_columns: Lista de colunas que compõem a chave de junção
                (cláusula ``ON`` do MERGE).
            update_columns: Lista de colunas a serem atualizadas quando
                houver correspondência (cláusula ``WHEN MATCHED``).
            connector: Conexão Oracle externa opcional. Se ``None``,
                utiliza a conexão interna.
            mode: Estratégia de merge: ``"merge"`` (padrão) para UPSERT
                ou ``"replace"`` para DELETE + INSERT.

        Raises:
            ValueError: Se ``mode`` não for ``"merge"`` nem ``"replace"``.
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
