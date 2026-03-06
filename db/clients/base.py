from __future__ import annotations
from typing import Any, Optional
import logging

from .postgres import PostgresClient
from .oracle import OracleClient


class DBManager:
    """Interface de alto nível para interação com bancos de dados suportados.

    Centraliza o gerenciamento de conexões e delega operações (leitura, merge,
    fechamento) ao client específico do engine escolhido (PostgreSQL, Oracle,
    etc.). O engine é selecionado no momento da instanciação e a conexão é
    estabelecida por meio do método ``connector``.

    Attributes:
        engine: Nome normalizado (minúsculas) do engine de banco de dados.
        _client_class: Classe do client correspondente ao engine escolhido.
        _client: Instância ativa do client após chamada a ``connector``.
        logger: Logger da classe para registro de eventos.

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
        """Inicializa o DBManager selecionando o engine de banco de dados.

        Valida se o ``engine`` informado é suportado e armazena a classe
        do client correspondente para posterior instanciação via
        ``connector``.

        Args:
            engine: Identificador do banco de dados (ex.: ``"postgres"``,
                ``"oracle"``). Case-insensitive.

        Raises:
            ValueError: Se o ``engine`` não estiver registrado em
                ``_CLIENTS``.
        """
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
        """Cria e armazena um client de conexão com o banco de dados.

        Instancia o client correspondente ao engine configurado, passando
        as credenciais e parâmetros de rede fornecidos. O client resultante
        é armazenado internamente para que métodos como ``read`` e ``merge``
        possam utilizá-lo sem necessidade de reconexão explícita.

        Args:
            user: Nome de usuário para autenticação no banco.
            password: Senha para autenticação no banco.
            database: Nome do banco de dados (ou service name, no caso
                do Oracle).
            host: Endereço do servidor de banco de dados. Padrão:
                ``"localhost"``.
            port: Porta de conexão. Se ``None``, utiliza a porta padrão
                do engine (5432 para PostgreSQL, 1521 para Oracle).
            role: Role ou schema opcional a ser utilizado na conexão.

        Returns:
            A instância do client de banco de dados criada e conectada.
        """
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
        """Executa uma operação de leitura no banco de dados ativo.

        Delega a chamada ao método ``read`` do client subjacente, repassando
        todos os argumentos posicionais e nomeados. Requer que ``connector``
        tenha sido chamado previamente.

        Args:
            *args: Argumentos posicionais repassados ao client (ex.: query SQL).
            **kwargs: Argumentos nomeados repassados ao client (ex.: ``table``,
                ``fetch_size``).

        Returns:
            Resultado da consulta no formato definido pelo client (geralmente
            uma lista de dicionários).

        Raises:
            RuntimeError: Se nenhum client estiver ativo.
        """
        self._ensure_client()
        return self._client.read(*args, **kwargs)

    def merge(self, *args, **kwargs) -> Any:
        """Executa uma operação de merge (upsert) no banco de dados ativo.

        Delega a chamada ao método ``merge`` do client subjacente. Suporta
        modos como ``"merge"`` (UPSERT) e ``"replace"`` (DELETE + INSERT),
        conforme implementação de cada client.

        Args:
            *args: Argumentos posicionais repassados ao client.
            **kwargs: Argumentos nomeados repassados ao client (ex.: ``table``,
                ``data``, ``key_columns``, ``update_columns``, ``mode``).

        Returns:
            Resultado da operação de merge conforme definido pelo client.

        Raises:
            RuntimeError: Se nenhum client estiver ativo.
        """
        self._ensure_client()
        return self._client.merge(*args, **kwargs)

    def close(self) -> None:
        """Encerra a conexão ativa com o banco de dados, se houver.

        Verifica se existe um client ativo e se ele possui o método
        ``close``, invocando-o para liberar os recursos de conexão.
        Caso não haja conexão ativa, a chamada é ignorada silenciosamente.
        """
        if self._client and hasattr(self._client, "close"):
            self._client.close()
            self.logger.info("Database connection closed.")

    # ---------- Private helpers ----------

    def _ensure_client(self):
        """Valida se um client de banco de dados está ativo.

        Método auxiliar interno que verifica se ``connector`` já foi
        chamado e se existe um client armazenado. Utilizado como
        pré-condição nos métodos de operação (``read``, ``merge``).

        Raises:
            RuntimeError: Se nenhum client estiver disponível.
        """
        if not self._client:
            raise RuntimeError(
                "No active client. You must call `.connector()` before performing operations."
            )
