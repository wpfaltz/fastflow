from __future__ import annotations
import shutil
from pathlib import Path
from typing import Iterable
import time
import platform
from ..engine.task import ff_task

if platform.system() == "Windows":
    import win32security


class FileManager:
    """Utilitário multiplataforma para gerenciamento de arquivos e diretórios.

    Fornece interfaces seguras e simples para operações comuns do sistema
    de arquivos local, incluindo:

    - **Cópia** de arquivos ou diretórios (recursiva).
    - **Movimentação** de arquivos ou diretórios.
    - **Exclusão** de arquivos ou diretórios (recursiva).
    - **Listagem** de conteúdos de diretórios.
    - **Verificação** de existência, tamanho e data de modificação.
    - **Identificação** do proprietário do arquivo (Windows e Unix).

    Todos os caminhos são normalizados via ``pathlib``, garantindo
    compatibilidade entre Windows e sistemas Unix. Todos os métodos
    de operação são estáticos e decorados como Prefect Tasks para
    rastreamento automático quando executados dentro de um flow.
    """

    # ---------- Private helpers ----------

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        """Normaliza e resolve um caminho de arquivo.

        Expande o til (``~``) para o diretório home do usuário e
        resolve o caminho para sua forma absoluta e canônica,
        eliminando links simbólicos e referências ``..``.

        Args:
            path: Caminho de arquivo ou diretório (string ou ``Path``).

        Returns:
            Objeto ``Path`` com o caminho absoluto e resolvido.
        """
        return Path(path).expanduser().resolve()

    # ---------- Copy ----------

    @staticmethod
    @ff_task(name="file_manager_copy", description="Copy a file or directory from source to destination.")
    def copy(src: str | Path, dest: str | Path, overwrite: bool = True) -> bool:
        """Copia um arquivo ou diretório da origem para o destino.

        Para diretórios, realiza cópia recursiva utilizando ``shutil.copytree``.
        Para arquivos, cria o diretório de destino caso não exista e utiliza
        ``shutil.copy2`` (preservando metadados).

        Args:
            src: Caminho de origem (arquivo ou diretório).
            dest: Caminho de destino.
            overwrite: Se ``False``, não sobrescreve arquivos existentes no
                destino. Para diretórios, controla ``dirs_exist_ok`` do
                ``copytree``. Padrão: ``True``.

        Returns:
            ``True`` se a cópia foi bem-sucedida, ``False`` em caso de erro
            ou se ``overwrite=False`` e o destino já existe.
        """
        src, dest = FileManager._resolve_path(src), FileManager._resolve_path(dest)

        try:
            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=overwrite)
            else:
                dest.mkdir(parents=True, exist_ok=True)
                if not overwrite and dest.exists():
                    return False
                shutil.copy2(src, dest)
            return True
        except Exception as e:
            print(f"[FileManager] Copy failed: {e}")
            return False

    # ---------- Move ----------
    @staticmethod
    @ff_task(name="file_manager_move", description="Move a file or directory from source to destination.")
    def move(src: str | Path, dest: str | Path, overwrite: bool = True) -> bool:
        """Move um arquivo ou diretório da origem para o destino.

        Utiliza ``shutil.move`` para realizar a movimentação. Cria o
        diretório de destino automaticamente caso ele não exista.

        Args:
            src: Caminho de origem (arquivo ou diretório). Deve existir.
            dest: Caminho de destino.
            overwrite: Se ``False`` e o destino já existir, a operação
                é cancelada. Padrão: ``True``.

        Returns:
            ``True`` se a movimentação foi bem-sucedida, ``False`` em caso
            de erro ou se ``overwrite=False`` e o destino já existe.
        """
        src, dest = FileManager._resolve_path(src), FileManager._resolve_path(dest)

        try:
            if not src.exists():
                raise FileNotFoundError(src)
            if not dest.exists():
                dest.mkdir(parents=True, exist_ok=True)
            if dest.exists() and not overwrite:
                print(f"[FileManager] Destination already exists and overwrite=False: {dest}")
                return False

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            return True
        except Exception as e:
            print(f"[FileManager] Move failed: {e}")
            return False

    # ---------- Delete ----------
    @staticmethod
    @ff_task(name="file_manager_delete", description="Delete a file or directory (recursively if needed).")
    def delete(path: str | Path) -> bool:
        """Exclui um arquivo ou diretório do sistema de arquivos.

        Para diretórios, realiza exclusão recursiva via ``shutil.rmtree``.
        Para arquivos, utiliza ``Path.unlink``. Se o caminho não existir,
        retorna ``False`` sem levantar exceção.

        Args:
            path: Caminho do arquivo ou diretório a ser excluído.

        Returns:
            ``True`` se a exclusão foi bem-sucedida, ``False`` se o
            caminho não existir ou em caso de erro.
        """
        path = FileManager._resolve_path(path)

        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=False)
            elif path.exists():
                path.unlink()
            else:
                print(f"[FileManager] Path not found: {path}")
                return False
            return True
        except Exception as e:
            print(f"[FileManager] Delete failed: {e}")
            return False

    # ---------- List ----------
    @staticmethod
    @ff_task(name="file_manager_list_dir", description="List contents of a directory, optionally recursively.")
    def list_dir(path: str | Path, recursive: bool = False) -> Iterable[Path]:
        """Lista o conteúdo de um diretório.

        Retorna um iterável com os caminhos dos arquivos e subdiretórios
        contidos no diretório especificado. Suporta listagem recursiva
        utilizando ``rglob``.

        Args:
            path: Caminho do diretório a ser listado.
            recursive: Se ``True``, lista recursivamente todos os
                arquivos e subdiretórios. Padrão: ``False``.

        Returns:
            Iterável de objetos ``Path`` representando o conteúdo do
            diretório. Retorna lista vazia se o diretório não existir.
        """
        path = FileManager._resolve_path(path)
        if not path.exists() or not path.is_dir():
            print(f"[FileManager] Directory not found: {path}")
            return []
        return path.rglob("*") if recursive else path.iterdir()

    # ---------- Check existence ----------

    @staticmethod
    @ff_task(name="file_manager_exists", description="Check if a file or directory exists.")
    def exists(path: str | Path) -> bool:
        """Verifica se um caminho (arquivo ou diretório) existe no sistema de arquivos.

        Args:
            path: Caminho a ser verificado.

        Returns:
            ``True`` se o caminho existir, ``False`` caso contrário.
        """
        return FileManager._resolve_path(path).exists()

    # ---------- File info ----------

    @staticmethod
    @ff_task(name="file_manager_size", description="Get size of a file or directory in bytes.")
    def size(path: str | Path) -> int:
        """Retorna o tamanho de um arquivo ou diretório em bytes.

        Para arquivos, retorna o tamanho direto via ``stat``. Para
        diretórios, calcula a soma dos tamanhos de todos os arquivos
        contidos recursivamente.

        Args:
            path: Caminho do arquivo ou diretório.

        Returns:
            Tamanho total em bytes.

        Raises:
            FileNotFoundError: Se o caminho não existir.
        """
        p = FileManager._resolve_path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        if p.is_dir():
            return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return p.stat().st_size
    
    @staticmethod
    @ff_task(name="file_manager_modification_time", description="Get last modification time of a file or directory.")
    def modification_time(path: str | Path, format: str | None = "%Y-%m-%d %H:%M:%S") -> float:
        """Retorna a última data de modificação de um arquivo ou diretório.

        Obtém o timestamp de modificação (``st_mtime``) do caminho
        especificado. Se um formato for fornecido, retorna a data como
        string formatada; caso contrário, retorna o timestamp numérico
        (float).

        Args:
            path: Caminho do arquivo ou diretório.
            format: Formato ``strftime`` para a data. Se ``None``, retorna
                o timestamp bruto como float. Padrão: ``"%Y-%m-%d %H:%M:%S"``.

        Returns:
            Data formatada como string (quando ``format`` é fornecido)
            ou timestamp numérico como float.

        Raises:
            FileNotFoundError: Se o caminho não existir.
        """
        p = FileManager._resolve_path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        modification_time = p.stat().st_mtime
        if format is not None:
            return time.strftime(format, time.localtime(modification_time))
        return modification_time
    
    @staticmethod    
    @ff_task(name="file_manager_get_file_owner", description="Get the owner of a file or directory.")
    def get_file_owner(path: str | Path) -> str:
        """Retorna o proprietário de um arquivo ou diretório.

        Identifica o usuário proprietário do caminho especificado,
        utilizando diferentes APIs conforme o sistema operacional:

        - **Windows:** Utiliza ``pywin32`` (``win32security``) para
          obter o SID do proprietário NTFS e resolver para
          ``DOMÍNIO\\Usuário``.
        - **Unix/Linux/macOS:** Utiliza o módulo ``pwd`` para resolver
          o UID retornado por ``stat`` para o nome de usuário.

        Args:
            path: Caminho do arquivo ou diretório.

        Returns:
            Nome do proprietário no formato ``DOMÍNIO\\Usuário``
            (Windows) ou nome de usuário simples (Unix).

        Raises:
            FileNotFoundError: Se o caminho não existir.
        """
        path = FileManager._resolve_path(path)

        if not path.exists():
            raise FileNotFoundError(path)

        if platform.system() == "Windows":
            sd = win32security.GetFileSecurity(
                str(path), win32security.OWNER_SECURITY_INFORMATION
            )
            owner_sid = sd.GetSecurityDescriptorOwner()
            name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
            return f"{domain}\\{name}"
        else:
            import pwd
            return pwd.getpwuid(path.stat().st_uid).pw_name
