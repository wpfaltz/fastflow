import json
import os
import time
import socket
import webbrowser
import getpass
from pathlib import Path
from typing import Optional
import requests
import jwt

def os_user_hook(
    *,
    server_host_env: str = "FASTFLOW_SERVER_HOST",
    server_user_tag_env: str = "FASTFLOW_SERVER_USER_TAG",
    server_user_fallback: str = "prefect",
    tag_prefix: str = "user",
    extra_tag_prefix: Optional[str] = None,  # ex.: "os_user" se quiser manter ambos
):
    """
    Adiciona tag de identidade com base no usuário do SO.

    - Se estiver no servidor (hostname == FASTFLOW_SERVER_HOST):
        user:<FASTFLOW_SERVER_USER_TAG> (ou fallback)
    - Caso contrário:
        user:<getpass.getuser()>

    Parâmetros úteis:
    - tag_prefix: normalmente "user"
    - extra_tag_prefix: se setado, adiciona também uma segunda tag, ex.:
        os_user:<username>
      (bom se você usar Gmail como user principal e quer manter OS user para debug)
    """
    def hook(state: dict) -> None:
        hostname = socket.gethostname()
        server_host = os.getenv(server_host_env, "").strip()

        is_server = server_host and hostname.lower() == server_host.lower()

        if is_server:
            server_user_tag = os.getenv(server_user_tag_env, "").strip() or server_user_fallback
            user_value = server_user_tag
            os_user_value = server_user_tag  # opcional, para consistência
        else:
            os_user_value = getpass.getuser()
            user_value = os_user_value

        state["tags"].append(f"{tag_prefix}:{user_value}")

        if extra_tag_prefix:
            state["tags"].append(f"{extra_tag_prefix}:{os_user_value}")

        state["context"]["os_user"] = os_user_value
        state["context"]["is_server"] = is_server

    return hook

def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()

def _load_cached_token(token_path: Path) -> Optional[str]:
    if not token_path.exists():
        return None
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
        return data.get("token")
    except Exception:
        return None

def _save_cached_token(token_path: Path, token: str) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({"token": token}), encoding="utf-8")

def _decode_email(token: str) -> str:
    # Sem verificar assinatura no cliente (para tagging é ok).
    # Para segurança forte, você pode validar assinatura com chave pública/secret compartilhado.
    payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
    email = payload.get("email")
    if not email or "@" not in email:
        raise RuntimeError("JWT inválido: email ausente.")
    return email

def server_identity_hook(
    *,
    auth_server_url_env: str = "FASTFLOW_AUTH_SERVER_URL",
    token_dir_env: str = "FASTFLOW_AUTH_TOKEN_DIR",
    token_file_env: str = "FASTFLOW_AUTH_TOKEN_FILE",
    require_env: str = "FASTFLOW_AUTH_REQUIRE",
    timeout_env: str = "FASTFLOW_AUTH_TIMEOUT",
    poll_interval_env: str = "FASTFLOW_AUTH_POLL_INTERVAL",
    tag_prefix: str = "user",
):
    def hook(state: dict) -> None:
        require = os.getenv(require_env, "1").strip().lower() in ("1", "true", "yes", "y", "on")
        auth_url = os.getenv(auth_server_url_env, "").rstrip("/")
        if not auth_url:
            if require:
                raise RuntimeError(f"{auth_server_url_env} não definido (URL do auth server).")
            return

        token_dir = os.getenv(token_dir_env, "~/.fastflow/tokens")
        token_file = os.getenv(token_file_env, "fastflow_jwt.json")
        token_path = _expand(token_dir) / token_file

        token = _load_cached_token(token_path)
        if token:
            email = _decode_email(token)
            state["tags"].append(f"{tag_prefix}:{email}")
            state["context"]["user_email"] = email
            return

        # 1) cria ticket
        r = requests.post(f"{auth_url}/auth/ticket", timeout=15)
        r.raise_for_status()
        ticket_id = r.json()["ticket_id"]
        login_url = r.json()["login_url"]

        # 2) abre browser
        webbrowser.open(login_url)

        # 3) poll até receber token
        timeout = int(os.getenv(timeout_env, "180"))
        interval = float(os.getenv(poll_interval_env, "2"))
        deadline = time.time() + timeout

        while time.time() < deadline:
            p = requests.get(f"{auth_url}/auth/poll", params={"ticket_id": ticket_id}, timeout=15)
            p.raise_for_status()
            data = p.json()
            if data.get("status") == "ready":
                token = data["token"]
                _save_cached_token(token_path, token)
                email = _decode_email(token)
                state["tags"].append(f"{tag_prefix}:{email}")
                state["context"]["user_email"] = email
                return
            time.sleep(interval)

        raise RuntimeError("Timeout aguardando login Google. Tente novamente.")

    return hook