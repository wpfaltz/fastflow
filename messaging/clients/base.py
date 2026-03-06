from __future__ import annotations
from abc import ABC, abstractmethod


class BaseMessenger(ABC):
    """Classe-base abstrata (facade) para clients de mensageria do FastFlow.

    Define a interface e atributos comuns que todo client de mensageria
    deve implementar. Serve como fachada unificada para os clients
    concretos ``TelegramClient`` e ``EmailClient``.

    Attributes:
        recipient: Destinatário padrão da mensagem (chat_id, e-mail, etc.).
    """

    def __init__(self, recipient: str) -> None:
        self.recipient = recipient

    @abstractmethod
    def send(self, text: str) -> None:
        """Envia uma mensagem de texto pelo canal de mensageria.

        Args:
            text: Conteúdo textual da mensagem a ser enviada.
        """
        ...
