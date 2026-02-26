from __future__ import annotations
from typing import Any, Mapping
from .clients.base import DBManager
from .clients.postgres import PostgresClient
from .clients.oracle import OracleClient

def _build_postgres(**kw) -> DBManager:
    """Constrói e retorna uma instância de cliente PostgreSQL.

    Fábrica interna utilizada pelo registro ``_BUILDERS`` para instanciar um
    ``PostgresClient`` com os parâmetros de conexão recebidos via keyword
    arguments. A importação é feita de forma lazy para evitar dependências
    desnecessárias caso o engine PostgreSQL não seja utilizado.

    Args:
        **kw: Parâmetros de conexão repassados diretamente ao construtor
            de ``PostgresClient`` (ex.: ``user``, ``password``, ``database``,
            ``host``, ``port``).

    Returns:
        Uma instância de ``PostgresClient`` pronta para uso.
    """
    from .clients.postgres import PostgresClient
    return PostgresClient(**kw)

def _build_oracle(**kw) -> DBManager:
    """Constrói e retorna uma instância de cliente Oracle.

    Fábrica interna utilizada pelo registro ``_BUILDERS`` para instanciar um
    ``OracleClient`` com os parâmetros de conexão recebidos via keyword
    arguments. A importação é feita de forma lazy para evitar dependências
    desnecessárias caso o engine Oracle não seja utilizado.

    Args:
        **kw: Parâmetros de conexão repassados diretamente ao construtor
            de ``OracleClient`` (ex.: ``user``, ``password``, ``database``,
            ``host``, ``port``).

    Returns:
        Uma instância de ``OracleClient`` pronta para uso.
    """
    from .clients.oracle import OracleClient
    return OracleClient(**kw)

_BUILDERS = {
    "postgres": _build_postgres,
    "oracle": _build_oracle,
}

class DBManager:
    """Gerenciador de alto nível para operações em banco de dados.

    Atua como uma fachada (facade) que abstrai o tipo de banco de dados
    subjacente, delegando as operações de leitura, escrita e fechamento
    de conexão a um client concreto (``PostgresClient``, ``OracleClient``,
    etc.).

    A instância pode ser criada diretamente, injetando um client, ou por
    meio do método de fábrica ``from_config``, que seleciona
    automaticamente o client correto com base no nome do engine.

    Attributes:
        _client: Instância concreta do client de banco de dados que
            implementa as operações reais de I/O.
    """

    def __init__(self, client: BaseDBClient):
        """Inicializa o DBManager com um client de banco de dados concreto.

        Args:
            client: Instância de um client que segue a interface
                ``BaseDBClient``, responsável pela comunicação efetiva
                com o banco de dados.
        """
        self._client = client

    @classmethod
    def from_config(cls, engine: str, **cfg) -> "DBManager":
        """Cria uma instância de ``DBManager`` a partir do nome do engine.

        Utiliza o registro interno ``_BUILDERS`` para localizar a fábrica
        correspondente ao ``engine`` informado e instancia o client adequado
        com as configurações passadas em ``**cfg``.

        Args:
            engine: Identificador do banco de dados (ex.: ``"postgres"``,
                ``"oracle"``). Case-insensitive.
            **cfg: Parâmetros de conexão repassados ao construtor do client.

        Returns:
            Uma instância de ``DBManager`` configurada com o client
            correspondente.

        Raises:
            ValueError: Se ``engine`` não for um dos engines suportados.
        """
        engine = engine.lower()
        if engine not in _BUILDERS:
            raise ValueError(f"Engine não suportado: {engine}")
        client = _BUILDERS[engine](**cfg)
        return cls(client)

    def read(self, sql: str, params: Mapping[str, Any] | None = None):
        """Executa uma consulta SQL de leitura e retorna os resultados.

        Delega a execução da query ao client de banco de dados subjacente.

        Args:
            sql: Instrução SQL ``SELECT`` (ou qualquer consulta de leitura)
                a ser executada.
            params: Dicionário opcional de parâmetros para bind na query,
                prevenindo SQL injection.

        Returns:
            Os resultados da consulta no formato retornado pelo client
            (tipicamente uma lista de dicionários).
        """
        return self._client.read(sql, params)

    def write(self, table: str, data: Any, if_exists: str = "append") -> int:
        """Escreve dados em uma tabela do banco de dados.

        Delega a operação de escrita ao client de banco de dados subjacente.

        Args:
            table: Nome da tabela de destino na qual os dados serão inseridos.
            data: Dados a serem escritos (ex.: ``pd.DataFrame``, lista de
                dicionários, etc.).
            if_exists: Estratégia de escrita quando a tabela já possui dados.
                Valores aceitos: ``"append"`` (padrão) para adicionar linhas,
                ou outro comportamento definido pelo client.

        Returns:
            Número de linhas afetadas pela operação de escrita.
        """
        return self._client.write(table, data, if_exists)

    def close(self) -> None:
        """Encerra a conexão com o banco de dados.

        Delega ao client subjacente o fechamento da conexão ativa,
        liberando os recursos associados.
        """
        self._client.close()
