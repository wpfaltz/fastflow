from __future__ import annotations
import paramiko
from pathlib import Path
from typing import Iterable
import os


class RemoteFileManager:
    """
    File management utility for remote hosts accessed via SSH/SFTP.
    """

    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None
        self.sftp = None

    def connect(self):
        """Establish SSH and SFTP connections."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(self.host, port=self.port, username=self.username, password=self.password)
        self.sftp = self.client.open_sftp()

    def disconnect(self):
        """Close open connections."""
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()

    # ---------- Core file operations ----------

    def list_dir(self, path: str) -> Iterable[str]:
        return self.sftp.listdir(path)

    def copy(self, local_src: str | Path, remote_dest: str) -> None:
        """Upload local file to remote."""
        self.sftp.put(str(local_src), remote_dest)

    def download(self, remote_src: str, local_dest: str | Path) -> None:
        """Download remote file to local."""
        local_dest = Path(local_dest)
        local_dest.parent.mkdir(parents=True, exist_ok=True)
        self.sftp.get(remote_src, str(local_dest))

    def delete(self, remote_path: str) -> None:
        """Delete file or directory on remote host."""
        try:
            self.sftp.remove(remote_path)
        except IOError:
            # if it's a directory
            for f in self.sftp.listdir(remote_path):
                self.delete(f"{remote_path}/{f}")
            self.sftp.rmdir(remote_path)

    def exists(self, remote_path: str) -> bool:
        """Check if remote path exists."""
        try:
            self.sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
