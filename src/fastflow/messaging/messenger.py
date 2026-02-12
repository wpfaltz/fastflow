from __future__ import annotations
from .clients.base import BaseMessenger
# from .clients.telegram import TelegramClient
# from .clients.email import EmailClient

def _build_telegram(**kw) -> BaseMessenger:
    from .clients.telegram import TelegramClient
    return TelegramClient(**kw)

_BUILDERS = {
    "telegram": _build_telegram,
    # "whatsapp": _build_whatsapp (futuro)
}

class Messenger:
    def __init__(self, client: BaseMessenger):
        self._client = client

    @classmethod
    def from_config(cls, kind: str, **cfg) -> "Messenger":
        kind = kind.lower()
        if kind not in _BUILDERS:
            raise ValueError(f"Mensageria não suportada: {kind}")
        return cls(_BUILDERS[kind](**cfg))

    def send(self, text: str) -> None:
        self._client.send(text)
