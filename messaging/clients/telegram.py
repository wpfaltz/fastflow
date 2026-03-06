from __future__ import annotations
import os
import telegram
from .base import BaseMessenger
from ...engine.task import ff_task


class TelegramClient(BaseMessenger):
    """Client de Telegram que herda de ``BaseMessenger``.

    Envia mensagens para um chat do Telegram utilizando a biblioteca
    ``python-telegram-bot``. O token do bot é lido da variável de
    ambiente ``TELEGRAM_BOT_TOKEN`` (arquivo ``.env``).

    Attributes:
        recipient: Identificador do chat (chat_id) de destino.
        bot_token: Token de autenticação do bot do Telegram.
    """

    def __init__(self, recipient: str, bot_token: str | None = None) -> None:
        super().__init__(recipient)
        self.bot_token = bot_token or os.environ["TELEGRAM_BOT_TOKEN"]

    @ff_task
    def send(self, text: str) -> None:
        """Envia uma mensagem de texto no chat configurado.

        Funciona tanto em contexto síncrono quanto dentro de um event
        loop já em execução.

        Args:
            text: Conteúdo textual da mensagem.
        """
        import asyncio

        bot = telegram.Bot(token=self.bot_token)
        coro = bot.send_message(chat_id=self.recipient, text=text)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(asyncio.run, coro).result()
        else:
            asyncio.run(coro)

    def test_method(self) -> None:
        """Método de teste para verificar a funcionalidade do TelegramClient."""
        self.send("Olá! Esta é uma mensagem de teste enviada pelo TelegramClient do FastFlow.")