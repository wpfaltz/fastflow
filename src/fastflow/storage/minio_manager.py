from __future__ import annotations
from typing import Iterable
# from minio import Minio

class MinioManager:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self._cli = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def list_files(self, bucket: str, prefix: str = "") -> Iterable[str]:
        return (o.object_name for o in self._cli.list_objects(bucket, prefix=prefix, recursive=True))

    def download(self, bucket: str, object_name: str, dest_path: str) -> None:
        self._cli.fget_object(bucket, object_name, dest_path)
