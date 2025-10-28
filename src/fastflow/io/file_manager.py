from __future__ import annotations
import shutil
from pathlib import Path
from typing import Iterable
import time
import platform
if platform.system() == "Windows":
    import win32security


class FileManager:
    """
    Cross-platform file and directory management utility.

    Provides safe and simple interfaces for common operations:
    - Copying files or directories
    - Moving files or directories
    - Deleting files or directories
    - Listing contents
    - Checking for existence and size

    All paths are normalized via pathlib, ensuring compatibility with
    both Windows and Unix-based systems.
    """

    # ---------- Private helpers ----------

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        """Normalize and expand user paths."""
        return Path(path).expanduser().resolve()

    # ---------- Copy ----------

    @staticmethod
    def copy(src: str | Path, dest: str | Path, overwrite: bool = True) -> bool:
        """
        Copy file or directory from src to dest.

        Args:
            src: source path (file or directory)
            dest: destination path
            overwrite: if False, will not overwrite existing files
        Returns:
            True if copy succeeded, False otherwise.
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
    def move(src: str | Path, dest: str | Path, overwrite: bool = True) -> bool:
        """
        Move file or directory from src to dest.
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
    def delete(path: str | Path) -> bool:
        """
        Delete a file or directory (recursively if needed).
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
    def list_dir(path: str | Path, recursive: bool = False) -> Iterable[Path]:
        """
        List directory contents.
        """
        path = FileManager._resolve_path(path)
        if not path.exists() or not path.is_dir():
            print(f"[FileManager] Directory not found: {path}")
            return []
        return path.rglob("*") if recursive else path.iterdir()

    # ---------- Check existence ----------

    @staticmethod
    def exists(path: str | Path) -> bool:
        """Return True if path exists."""
        return FileManager._resolve_path(path).exists()

    # ---------- File info ----------

    @staticmethod
    def size(path: str | Path) -> int:
        """Return file size in bytes."""
        p = FileManager._resolve_path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        if p.is_dir():
            return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return p.stat().st_size
    
    @staticmethod
    def modification_time(path: str | Path, format: str | None = "%Y-%m-%d %H:%M:%S") -> float:
        """Return last modification time as a timestamp."""
        p = FileManager._resolve_path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        modification_time = p.stat().st_mtime
        if format is not None:
            return time.strftime(format, time.localtime(modification_time))
        return modification_time
    
    @staticmethod    
    def get_file_owner(path: str | Path) -> str:
        """
        Return the owner of a file or directory.

        On Windows, uses pywin32 to retrieve the NTFS owner.
        On Unix-like systems, uses pwd to resolve UID to username.
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
