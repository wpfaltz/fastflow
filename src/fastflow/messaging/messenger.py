from __future__ import annotations
from .clients.base import BaseMessenger
# from .clients.telegram import TelegramClient
# from .clients.email import EmailClient

def _build_telegram(**kw) -> BaseMessenger:
    """Constrói e retorna uma instância de client Telegram.

    Fábrica interna utilizada pelo registro ``_BUILDERS`` para instanciar
    um ``TelegramClient`` com os parâmetros recebidos. A importação é
    feita de forma lazy para evitar dependências desnecessárias.

    Args:
        **kw: Parâmetros repassados ao construtor de ``TelegramClient``
            (ex.: ``bot_token``, ``chat_id``).

    Returns:
        Uma instância de ``TelegramClient`` pronta para envio.
    """
    from .clients.telegram import TelegramClient
    return TelegramClient(**kw)

_BUILDERS = {
    "telegram": _build_telegram,
    # "whatsapp": _build_whatsapp (futuro)
}

class Messenger:
    """Gerenciador de alto nível para envio de mensagens.

    Atua como uma fachada (facade) que abstrai o tipo de canal de
    mensageria subjacente (Telegram, WhatsApp futuro, etc.), delegando
    o envio ao client concreto.

    A instância pode ser criada diretamente, injetando um client, ou
    por meio do método de fábrica ``from_config``.

    Attributes:
        _client: Instância concreta do client de mensageria.
    """

    def __init__(self, client: BaseMessenger):
        """Inicializa o Messenger com um client de mensageria concreto.

        Args:
            client: Instância que implementa o protocolo ``BaseMessenger``.
        """
        self._client = client

    @classmethod
    def from_config(cls, kind: str, **cfg) -> "Messenger":
        """Cria uma instância de ``Messenger`` a partir do tipo de canal.

        Utiliza o registro interno ``_BUILDERS`` para localizar a fábrica
        correspondente ao canal de mensageria informado e instancia o
        client adequado.

        Args:
            kind: Tipo do canal de mensageria (ex.: ``"telegram"``).
                Case-insensitive.
            **cfg: Parâmetros de configuração repassados ao construtor
                do client.

        Returns:
            Uma instância de ``Messenger`` configurada com o client
            correspondente.

        Raises:
            ValueError: Se ``kind`` não for um canal suportado.
        """
        kind = kind.lower()
        if kind not in _BUILDERS:
            raise ValueError(f"Mensageria não suportada: {kind}")
        return cls(_BUILDERS[kind](**cfg))

    def send(self, text: str) -> None:
        """Envia uma mensagem de texto através do canal configurado.

        Delega o envio ao client de mensageria subjacente.

        Args:
            text: Conteúdo textual da mensagem a ser enviada.
        """
        self._client.send(text)
