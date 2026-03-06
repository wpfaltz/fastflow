from __future__ import annotations

import os
import requests
from typing import Iterable
import json


def keyvault_hook(
    *,
    control_plane_url_env: str = "FASTFLOW_AUTH_SERVER_URL",
    jwt_env: str = "FASTFLOW_JWT",
    secrets: Iterable[str] | None = None,
    inject_into_context_key: str = "secrets",
    fail_if_missing: bool = True,
    vault_path: str = "/vault/secrets",
):
    """Cria um hook que busca secrets no Key Vault via control-plane.

    Realiza uma requisição autenticada (JWT) ao servidor control-plane para
    obter os valores de secrets genéricos armazenados no Key Vault. Os
    secrets são injetados exclusivamente em memória, no dicionário
    ``state["context"][inject_into_context_key]``, sem persisti-los em
    variáveis de ambiente ou disco.

    O token JWT é obtido, em ordem de prioridade, de:
    1. ``state["context"]["jwt"]`` (definido pelo ``server_identity_hook``).
    2. Variável de ambiente ``FASTFLOW_JWT``.

    Se o valor do JWT for um caminho de arquivo (inicia com ``~``), ele
    será expandido e o token será lido do arquivo JSON correspondente.

    Args:
        control_plane_url_env: Variável de ambiente com a URL do servidor
            control-plane. Padrão: ``"FASTFLOW_AUTH_SERVER_URL"``.
        jwt_env: Variável de ambiente com o JWT ou caminho para o arquivo
            de token. Padrão: ``"FASTFLOW_JWT"``.
        secrets: Coleção de nomes de secrets genéricos a serem buscados
            no Key Vault. Se ``None`` ou vazio, o hook não faz nada.
        inject_into_context_key: Chave sob a qual os secrets serão
            armazenados em ``state["context"]``. Padrão: ``"secrets"``.
        fail_if_missing: Se ``True``, levanta ``RuntimeError`` caso algum
            secret solicitado não seja retornado pelo vault. Padrão:
            ``True``.
        vault_path: Caminho do endpoint de secrets no control-plane.
            Padrão: ``"/vault/secrets"``.

    Returns:
        Função hook que recebe ``state`` e popula o contexto com os
        secrets carregados.

    Raises:
        RuntimeError: Se a URL do control-plane não estiver definida;
            se o JWT não estiver disponível; se a requisição ao vault
            falhar; ou se secrets obrigatórios estiverem ausentes
            (quando ``fail_if_missing=True``).
    """

    def hook(state: dict) -> None:
        if not secrets:
            return

        control_plane_url = os.getenv(control_plane_url_env, "").rstrip("/")
        if not control_plane_url:
            raise RuntimeError(
                f"{control_plane_url_env} not defined. Cannot reach Key Vault."
            )

        jwt_path = state.get("context", {}).get("jwt") or os.getenv(jwt_env)
        # jwt_path is a relative path that starts with ~. Expand it to an absolute path.
        if jwt_path and jwt_path.startswith("~"):
            jwt_path = os.path.expanduser(jwt_path)
        jwt = None
        if jwt_path and os.path.isfile(jwt_path):
            # json loads
                with open(jwt_path, "r") as f:
                    jwt = json.load(f)['token']
        if not jwt:
            raise RuntimeError(
                "JWT not available for Key Vault access. "
                "Ensure server_identity_hook runs before keyvault_hook."
            )

        names = ",".join(secrets)
        resp = requests.get(
            f"{control_plane_url}/vault/secrets",
            headers={"Authorization": f"Bearer {jwt}"},
            params={"names": names},
            timeout=20,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"KeyVault request failed: {resp.status_code} {resp.text}"
            )

        data = resp.json().get("secrets", {})

        missing = [s for s in secrets if s not in data]
        if missing and fail_if_missing:
            raise RuntimeError(f"Missing secrets from KeyVault: {missing}")

        # injeta apenas na memória do flow
        ctx = state.setdefault("context", {})
        ctx.setdefault(inject_into_context_key, {}).update(data)

    return hook