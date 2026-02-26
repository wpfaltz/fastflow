from __future__ import annotations
from typing import Protocol

class BaseMessenger(Protocol):
    """Protocolo base para clients de mensageria do FastFlow.

    Define a interface mínima que todo client de mensageria deve
    implementar. Utiliza ``typing.Protocol`` para tipagem estrutural
    (duck typing estático), permitindo que qualquer classe que
    implemente o método ``send`` seja considerada compatível.
    """

    def send(self, text: str) -> None:
        """Envia uma mensagem de texto pelo canal de mensageria.

        Args:
            text: Conteúdo textual da mensagem a ser enviada.
        """
        ...
