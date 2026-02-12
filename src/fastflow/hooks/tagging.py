import os
import socket

def host_tag_hook(
    server_host_env: str = "FASTFLOW_SERVER_HOST",
    server_alias: str = "prefect-server",
):
    def hook(state: dict):
        hostname = socket.gethostname()
        server_host = os.getenv(server_host_env, "")

        if hostname.lower() == server_host.lower():
            state["tags"].append(f"host:{server_alias}")
        else:
            state["tags"].append(f"host:{hostname}")

    return hook
