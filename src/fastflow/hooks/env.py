import os
import socket

def env_hook(server_host_env: str = "FASTFLOW_SERVER_HOST"):
    def hook(state: dict):
        hostname = socket.gethostname()
        server_host = os.getenv(server_host_env, "")

        if hostname.lower() == server_host.lower():
            state["tags"].append("env:PRD")
        else:
            state["tags"].append("env:DEV")

    return hook