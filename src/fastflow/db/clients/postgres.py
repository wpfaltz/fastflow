from __future__ import annotations
import psycopg2
import psycopg2.extras
import pandas as pd
import io
import logging
from typing import Any, Optional


class PostgresClient:
    """Client de banco de dados PostgreSQL para o FastFlow.

    Fornece gerenciamento básico de conexão, execução de consultas SQL e
    operações de merge (UPSERT / DELETE+INSERT) utilizando o driver
    ``psycopg2``. Projetado para ser utilizado através da interface
    ``DBManager``.

    O client mantém uma conexão persistente (``self.conn``) que é
    estabelecida de forma lazy pelo método ``connector`` e reutilizada
    em operações subsequentes.

    Attributes:
        DEFAULT_PORT: Porta padrão do PostgreSQL (5432).
        user: Nome de usuário para autenticação.
        password: Senha para autenticação.
        database: Nome do banco de dados PostgreSQL.
        host: Endereço do servidor.
        port: Porta de conexão.
        role: Role opcional.
        conn: Objeto de conexão ``psycopg2`` ativo ou ``None``.
        logger: Logger da classe.
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
        """Inicializa o PostgresClient com as credenciais de conexão.

        Armazena os parâmetros de conexão sem estabelecer a conexão
        imediatamente. A conexão será criada de forma lazy na primeira
        chamada a ``connector``.

        Args:
            user: Nome de usuário para autenticação no PostgreSQL.
            password: Senha para autenticação.
            database: Nome do banco de dados PostgreSQL.
            host: Endereço do servidor PostgreSQL. Padrão: ``"localhost"``.
            port: Porta de conexão. Se ``None``, utiliza ``DEFAULT_PORT``
                (5432).
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
        """Cria uma conexão com o banco de dados PostgreSQL.

        Utiliza ``psycopg2.connect`` para estabelecer a conexão com os
        parâmetros armazenados na instanciação. Se já existir uma conexão
        aberta (não fechada), retorna a conexão existente sem criar uma
        nova.

        Returns:
            Objeto de conexão ``psycopg2.connection``.

        Raises:
            Exception: Propaga qualquer erro de conexão lançado pelo
                ``psycopg2``.
        """
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
        """Encerra a conexão com o banco de dados PostgreSQL.

        Fecha a conexão armazenada em ``self.conn``, se ela existir e
        não estiver já fechada, liberando os recursos de rede e do
        servidor.
        """
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
        """Executa uma consulta SQL no PostgreSQL e retorna os resultados.

        Utiliza ``RealDictCursor`` do ``psycopg2.extras`` para que cada
        linha seja retornada como um dicionário. Se nenhuma ``query`` for
        fornecida, gera automaticamente um ``SELECT * FROM <table>``.

        Args:
            query: Instrução SQL a ser executada. Se ``None``, o parâmetro
                ``table`` será utilizado para gerar uma query padrão.
            table: Nome da tabela para gerar ``SELECT *``. Utilizado
                apenas quando ``query`` é ``None``.
            connector: Conexão PostgreSQL externa opcional. Se ``None``,
                utiliza a conexão interna (``self.connector()``).
            fetch_size: Quantidade máxima de linhas a buscar. Se ``None``,
                busca todas as linhas (``fetchall``).

        Returns:
            Lista de dicionários (``RealDictRow``), cada um representando
            uma linha do resultado.

        Raises:
            ValueError: Se nem ``query`` nem ``table`` forem fornecidos.
        """
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
        """Realiza uma operação de UPSERT ou REPLACE em uma tabela PostgreSQL.

        Cria uma tabela temporária (``CREATE TEMP TABLE ... LIKE``),
        carrega os dados nela via ``COPY FROM STDIN WITH CSV`` e executa
        a estratégia escolhida:

        - ``mode='merge'``: Utiliza ``INSERT ... ON CONFLICT DO UPDATE``
          para inserir linhas novas e atualizar as existentes com base
          nas ``key_columns``.
        - ``mode='replace'``: Remove as linhas correspondentes da tabela
          de destino utilizando ``DELETE ... USING`` e insere todos os
          dados da tabela temporária.

        Após a operação, a tabela temporária é descartada.

        Args:
            table: Nome da tabela de destino no PostgreSQL.
            data: Dados a serem mesclados. Aceita ``pd.DataFrame`` ou
                lista de dicionários.
            key_columns: Lista de colunas que compõem a chave de conflito
                (cláusula ``ON CONFLICT``).
            update_columns: Lista de colunas a serem atualizadas em caso
                de conflito.
            connector: Conexão PostgreSQL externa opcional. Se ``None``,
                utiliza a conexão interna.
            mode: Estratégia de merge: ``"merge"`` (padrão) para UPSERT
                ou ``"replace"`` para DELETE + INSERT.

        Raises:
            ValueError: Se ``mode`` não for ``"merge"`` nem ``"replace"``.
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
