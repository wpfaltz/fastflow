from __future__ import annotations
import paramiko
from pathlib import Path
from typing import Iterable
import os


class RemoteFileManager:
    """Utilitário de gerenciamento de arquivos em hosts remotos via SSH/SFTP.

    Permite realizar operações de arquivo (listagem, upload, download,
    exclusão, verificação de existência) em servidores remotos acessíveis
    por SSH, utilizando o protocolo SFTP implementado pelo ``paramiko``.

    A conexão SSH deve ser estabelecida explicitamente via ``connect``
    antes de qualquer operação, e encerrada via ``disconnect`` ao final.

    Attributes:
        host: Endereço do servidor remoto.
        username: Usuário para autenticação SSH.
        password: Senha para autenticação SSH.
        port: Porta SSH. Padrão: 22.
        client: Instância de ``paramiko.SSHClient`` ou ``None``.
        sftp: Canal SFTP aberto ou ``None``.
    """

    def __init__(self, host: str, username: str, password: str, port: int = 22):
        """Inicializa o RemoteFileManager com as credenciais de conexão SSH.

        Armazena os parâmetros de conexão sem estabelecer a conexão
        imediatamente. Use ``connect`` para estabelecer a conexão.

        Args:
            host: Endereço IP ou hostname do servidor remoto.
            username: Nome de usuário para autenticação SSH.
            password: Senha para autenticação SSH.
            port: Porta SSH do servidor. Padrão: ``22``.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None
        self.sftp = None

    def connect(self):
        """Estabelece conexões SSH e SFTP com o servidor remoto.

        Cria um ``SSHClient``, configura a política de aceitação
        automática de chaves de host (``AutoAddPolicy``), conecta ao
        servidor e abre um canal SFTP para transferência de arquivos.

        Raises:
            paramiko.SSHException: Se houver falha na conexão SSH.
            paramiko.AuthenticationException: Se as credenciais forem
                inválidas.
        """
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(self.host, port=self.port, username=self.username, password=self.password)
        self.sftp = self.client.open_sftp()

    def disconnect(self):
        """Encerra as conexões SFTP e SSH abertas.

        Fecha o canal SFTP e o client SSH, liberando os recursos de
        rede. Seguro para chamar mesmo que as conexões não estejam
        abertas (verifica antes de fechar).
        """
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()

    # ---------- Core file operations ----------

    def list_dir(self, path: str) -> Iterable[str]:
        """Lista o conteúdo de um diretório no servidor remoto.

        Args:
            path: Caminho absoluto do diretório no servidor remoto.

        Returns:
            Iterável de nomes de arquivos e subdiretórios contidos
            no diretório especificado.
        """
        return self.sftp.listdir(path)

    def copy(self, local_src: str | Path, remote_dest: str) -> None:
        """Faz upload de um arquivo local para o servidor remoto.

        Transfere o arquivo local especificado por ``local_src`` para
        o caminho remoto ``remote_dest`` via SFTP.

        Args:
            local_src: Caminho do arquivo local a ser enviado.
            remote_dest: Caminho de destino no servidor remoto.
        """
        self.sftp.put(str(local_src), remote_dest)

    def download(self, remote_src: str, local_dest: str | Path) -> None:
        """Faz download de um arquivo do servidor remoto para o sistema local.

        Transfere o arquivo remoto especificado por ``remote_src`` para
        o caminho local ``local_dest`` via SFTP. Cria automaticamente os
        diretórios necessários no destino local.

        Args:
            remote_src: Caminho do arquivo no servidor remoto.
            local_dest: Caminho de destino no sistema de arquivos local.
        """
        local_dest = Path(local_dest)
        local_dest.parent.mkdir(parents=True, exist_ok=True)
        self.sftp.get(remote_src, str(local_dest))

    def delete(self, remote_path: str) -> None:
        """Exclui um arquivo ou diretório no servidor remoto.

        Tenta remover o caminho como arquivo (``sftp.remove``). Se falhar
        (indicando que é um diretório), realiza exclusão recursiva,
        removendo primeiro todos os arquivos e subdiretórios contidos
        e, em seguida, o diretório em si.

        Args:
            remote_path: Caminho do arquivo ou diretório remoto a ser
                excluído.

        Raises:
            IOError: Se o caminho não puder ser removido.
        """
        try:
            self.sftp.remove(remote_path)
        except IOError:
            # if it's a directory
            for f in self.sftp.listdir(remote_path):
                self.delete(f"{remote_path}/{f}")
            self.sftp.rmdir(remote_path)

    def exists(self, remote_path: str) -> bool:
        """Verifica se um caminho existe no servidor remoto.

        Utiliza ``sftp.stat`` para verificar a existência do caminho.
        Retorna ``True`` se o stat for bem-sucedido, ``False`` se
        lançar ``FileNotFoundError``.

        Args:
            remote_path: Caminho a ser verificado no servidor remoto.

        Returns:
            ``True`` se o caminho existir, ``False`` caso contrário.
        """
        try:
            self.sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
