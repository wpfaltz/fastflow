from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .base import BaseMessenger


class EmailClient(BaseMessenger):
    """Client de e-mail que herda de ``BaseMessenger``.

    Envia mensagens por SMTP utilizando as credenciais e configurações
    informadas no construtor.

    Attributes:
        recipient: Endereço de e-mail do destinatário.
        smtp_server: Endereço do servidor SMTP.
        smtp_port: Porta do servidor SMTP.
        username: Usuário para autenticação SMTP.
        password: Senha (ou app password) para autenticação SMTP.
        from_addr: Endereço de e-mail do remetente.
        subject: Assunto padrão das mensagens enviadas.
    """

    def __init__(
        self,
        recipient: str,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        subject: str = "",
    ) -> None:
        super().__init__(recipient)
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.subject = subject

    def send(self, text: str) -> None:
        """Envia um e-mail com o texto informado.

        Args:
            text: Corpo da mensagem de e-mail.
        """
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = self.recipient
        msg["Subject"] = self.subject
        msg.attach(MIMEText(text, "plain"))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.recipient, msg.as_string())
