import os
import socket

def env_hook(server_host_env: str = "FASTFLOW_SERVER_HOST"):
    """Cria um hook que adiciona uma tag de ambiente (PRD/DEV) ao flow.

    Compara o hostname da máquina local com o valor da variável de ambiente
    especificada por ``server_host_env``. Se forem iguais (case-insensitive),
    a tag ``env:PRD`` é adicionada ao estado do flow, indicando execução em
    produção. Caso contrário, adiciona ``env:DEV`` para indicar ambiente de
    desenvolvimento.

    Args:
        server_host_env: Nome da variável de ambiente que contém o hostname
            do servidor de produção. Padrão: ``"FASTFLOW_SERVER_HOST"``.

    Returns:
        Função hook que recebe o dicionário ``state`` do flow e adiciona
        a tag de ambiente à lista ``state["tags"]``.
    """
    def hook(state: dict):
        hostname = socket.gethostname()
        server_host = os.getenv(server_host_env, "")

        if hostname.lower() == server_host.lower():
            state["tags"].append("env:PRD")
        else:
            state["tags"].append("env:DEV")

    return hook