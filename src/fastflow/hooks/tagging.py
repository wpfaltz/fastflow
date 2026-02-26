import os
import socket

def host_tag_hook(
    server_host_env: str = "FASTFLOW_SERVER_HOST",
    server_alias: str = "prefect-server",
):
    """Cria um hook que adiciona uma tag com o hostname da máquina ao flow.

    Identifica o hostname da máquina que está executando o flow e adiciona
    uma tag no formato ``host:{hostname}`` ao estado. Se o hostname
    corresponder ao servidor de produção (definido pela variável de ambiente
    ``server_host_env``), utiliza o alias configurado em ``server_alias``
    em vez do hostname real.

    Args:
        server_host_env: Nome da variável de ambiente que contém o hostname
            do servidor de produção. Padrão: ``"FASTFLOW_SERVER_HOST"``.
        server_alias: Alias amigável a ser utilizado como tag quando a
            execução ocorre no servidor de produção. Padrão:
            ``"prefect-server"``.

    Returns:
        Função hook que recebe ``state`` e adiciona a tag de host à
        lista ``state["tags"]``.
    """
    def hook(state: dict):
        hostname = socket.gethostname()
        server_host = os.getenv(server_host_env, "")

        if hostname.lower() == server_host.lower():
            state["tags"].append(f"host:{server_alias}")
        else:
            state["tags"].append(f"host:{hostname}")

    return hook
