from __future__ import annotations
from typing import Protocol

class BaseMessenger(Protocol):
    def send(self, text: str) -> None:
        ...
