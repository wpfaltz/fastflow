from __future__ import annotations
from typing import Iterable
# from minio import Minio

class MinioManager:
    """Gerenciador de armazenamento de objetos MinIO para o FastFlow.

    Fornece uma interface simplificada para operações comuns com
    armazenamento compatível com S3 (MinIO), incluindo listagem de
    arquivos e download de objetos.

    Utiliza o client oficial ``minio.Minio`` para comunicação com
    o servidor MinIO.

    Attributes:
        _cli: Instância do client ``Minio`` configurado.
    """

    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        """Inicializa o MinioManager com as credenciais de acesso.

        Cria imediatamente uma instância do client ``Minio`` conectado
        ao endpoint especificado.

        Args:
            endpoint: URL do servidor MinIO (ex.: ``"minio.example.com:9000"``).
            access_key: Chave de acesso (equivalente ao AWS Access Key).
            secret_key: Chave secreta (equivalente ao AWS Secret Key).
            secure: Se ``True``, utiliza HTTPS para conexão. Padrão:
                ``False`` (HTTP).
        """
        self._cli = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def list_files(self, bucket: str, prefix: str = "") -> Iterable[str]:
        """Lista os nomes dos objetos (arquivos) em um bucket MinIO.

        Realiza listagem recursiva de todos os objetos no bucket cujo
        nome começa com o prefixo especificado.

        Args:
            bucket: Nome do bucket MinIO.
            prefix: Prefixo para filtrar objetos. Se vazio (padrão),
                lista todos os objetos do bucket.

        Returns:
            Gerador (iterator) de strings com os nomes completos
            (``object_name``) de cada objeto encontrado.
        """
        return (o.object_name for o in self._cli.list_objects(bucket, prefix=prefix, recursive=True))

    def download(self, bucket: str, object_name: str, dest_path: str) -> None:
        """Faz download de um objeto do MinIO para o sistema de arquivos local.

        Utiliza ``fget_object`` para transferir o objeto diretamente
        para um arquivo no caminho de destino especificado.

        Args:
            bucket: Nome do bucket MinIO contendo o objeto.
            object_name: Nome completo (chave) do objeto no bucket.
            dest_path: Caminho local onde o arquivo será salvo.

        Raises:
            S3Error: Se o bucket ou objeto não existirem, ou em caso
                de erro de comunicação com o servidor.
        """
        self._cli.fget_object(bucket, object_name, dest_path)
