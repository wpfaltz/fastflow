# carrega o .env antes de importar db/engine: o Prefect lê PREFECT_API_URL no primeiro import
from .utils.env import configure_environment

configure_environment(mode="auto")

from .db import DBManager, PostgresClient, OracleClient
from prefect import get_run_logger
from .engine import ff_task
from .io import FileManager, RemoteFileManager
from .messaging import BaseMessenger, EmailClient, TelegramClient
from .storage.minio_manager import MinioManager
from .version import __version__

__all__ = [
    # version
    "__version__",
    # db
    "DBManager",
    "PostgresClient",
    "OracleClient",
    # engine / prefect
    "ff_task",
    "get_run_logger",
    # io
    "FileManager",
    "RemoteFileManager",
    # messaging
    "BaseMessenger",
    "EmailClient",
    "TelegramClient",
    # storage
    "MinioManager"
]