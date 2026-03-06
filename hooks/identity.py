import json
import os
import time
import socket
import webbrowser
import getpass
from pathlib import Path
from typing import Optional, Tuple
from prefect import get_run_logger
import requests
import jwt

def os_user_hook(
    *,
    server_host_env: str = "FASTFLOW_SERVER_HOST",
    server_user_tag_env: str = "FASTFLOW_SERVER_USER_TAG",
    server_user_fallback: str = "prefect",
    tag_prefix: str = "user"
):
    """Cria um hook que adiciona uma tag de identidade baseada no usuário do SO.

    Determina o usuário que está executando o flow com base no contexto:

    - **No servidor de produção** (hostname == ``FASTFLOW_SERVER_HOST``):
      utiliza o valor de ``FASTFLOW_SERVER_USER_TAG`` ou o fallback fornecido.
    - **Fora do servidor** (máquina de desenvolvimento): utiliza
      ``getpass.getuser()`` para obter o usuário do sistema operacional.

    Além de adicionar a tag ``{tag_prefix}:{usuário}`` ao estado do flow,
    também popula ``state["context"]`` com as chaves ``os_user`` e
    ``is_server``.

    Args:
        server_host_env: Variável de ambiente com o hostname do servidor
            de produção. Padrão: ``"FASTFLOW_SERVER_HOST"``.
        server_user_tag_env: Variável de ambiente com o nome de usuário
            a ser utilizado quando no servidor. Padrão:
            ``"FASTFLOW_SERVER_USER_TAG"``.
        server_user_fallback: Valor utilizado caso ``server_user_tag_env``
            não esteja definida. Padrão: ``"prefect"``.
        tag_prefix: Prefixo da tag de identidade. Padrão: ``"user"``.

    Returns:
        Função hook que recebe ``state`` e adiciona tag de usuário e
        dados de contexto.
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
        state["context"]["os_user"] = os_user_value
        state["context"]["is_server"] = is_server

    return hook

def _expand(path: str) -> Path:
    """Expande e resolve um caminho de arquivo com variáveis de ambiente e til.

    Aplica ``os.path.expandvars`` para expandir variáveis de ambiente
    (ex.: ``$HOME``), ``os.path.expanduser`` para expandir ``~`` e, em
    seguida, resolve o caminho para sua forma absoluta e canônica.

    Args:
        path: Caminho de arquivo que pode conter ``~`` ou variáveis de
            ambiente.

    Returns:
        Objeto ``Path`` com o caminho absoluto e resolvido.
    """
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()

def _load_cached_token(token_path: Path) -> Optional[str]:
    """Carrega um token JWT cacheado de um arquivo local.

    Tenta ler o arquivo JSON no caminho especificado e extrair o valor
    da chave ``"token"``. Retorna ``None`` se o arquivo não existir ou
    se ocorrer qualquer erro de leitura/parse.

    Args:
        token_path: Caminho absoluto do arquivo JSON contendo o token.

    Returns:
        O token JWT como string, ou ``None`` se não for possível
        carregá-lo.
    """
    if not token_path.exists():
        return None
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
        return data.get("token")
    except Exception:
        return None

def _save_cached_token(token_path: Path, token: str) -> None:
    """Salva um token JWT em cache no sistema de arquivos local.

    Cria os diretórios necessários (caso não existam) e grava o token
    em formato JSON no caminho especificado.

    Args:
        token_path: Caminho absoluto do arquivo onde o token será
            armazenado.
        token: Token JWT a ser persistido.
    """
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({"token": token}), encoding="utf-8")

def _load_cached_public_key(path: Path) -> Optional[str]:
    """Carrega uma chave pública PEM cacheada do sistema de arquivos.

    Tenta ler o conteúdo do arquivo PEM no caminho especificado.
    Retorna ``None`` se o arquivo não existir ou se ocorrer qualquer
    erro de leitura.

    Args:
        path: Caminho absoluto do arquivo PEM contendo a chave pública.

    Returns:
        Conteúdo da chave pública em formato PEM como string, ou ``None``
        se não for possível carregá-la.
    """
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None

def _save_cached_public_key(path: Path, pem: str) -> None:
    """Salva uma chave pública PEM em cache no sistema de arquivos.

    Cria os diretórios necessários (caso não existam) e grava o
    conteúdo PEM no caminho especificado.

    Args:
        path: Caminho absoluto do arquivo onde a chave será armazenada.
        pem: Conteúdo da chave pública em formato PEM.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pem, encoding="utf-8")

def _get_public_key_from_server(auth_url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Obtém a chave pública de verificação JWT do servidor de autenticação.

    Realiza uma requisição ``GET`` ao endpoint ``/auth/public-key`` do
    servidor de autenticação e extrai a chave pública PEM, o identificador
    da chave (``kid``) e o algoritmo (``alg``).

    Args:
        auth_url: URL base do servidor de autenticação FastFlow
            (ex.: ``"https://auth.example.com"``).

    Returns:
        Tupla ``(public_key_pem, kid, alg)`` onde:
        - ``public_key_pem``: Chave pública em formato PEM.
        - ``kid``: Identificador da chave (pode ser ``None``).
        - ``alg``: Algoritmo de assinatura (pode ser ``None``).

    Raises:
        requests.HTTPError: Se a requisição falhar.
    """
    r = requests.get(f"{auth_url}/auth/public-key", timeout=10)
    r.raise_for_status()
    data = r.json()
    pem = data["public_key_pem"]
    kid = data.get("kid")
    alg = data.get("alg")
    return pem, kid, alg

def _decode_email_verified(
    token: str,
    public_key_pem: str,
    *,
    expected_audience: str = "fastflow",
    expected_issuer: str = "fastflow-auth",
    algorithms: Tuple[str, ...] = ("RS256",),
) -> str:
    """Decodifica e valida um token JWT, retornando o email verificado.

    Verifica a assinatura digital do token utilizando a chave pública PEM
    fornecida, além de validar as claims ``exp`` (expiração), ``aud``
    (audiência), ``iss`` (emissor) e a presença de um email válido.

    Args:
        token: Token JWT codificado a ser validado.
        public_key_pem: Chave pública PEM para verificação da assinatura.
        expected_audience: Audiência esperada na claim ``aud``.
            Padrão: ``"fastflow"``.
        expected_issuer: Emissor esperado na claim ``iss``.
            Padrão: ``"fastflow-auth"``.
        algorithms: Tupla de algoritmos aceitos para verificação.
            Padrão: ``("RS256",)``.

    Returns:
        Endereço de email extraído do payload do token.

    Raises:
        jwt.ExpiredSignatureError: Se o token estiver expirado.
        jwt.InvalidSignatureError: Se a assinatura for inválida.
        jwt.InvalidTokenError: Se o token não contiver um email válido
            ou falhar em outra validação.
    """
    payload = jwt.decode(
        token,
        public_key_pem,
        algorithms=list(algorithms),
        audience=expected_audience,
        issuer=expected_issuer,
        options={"require": ["exp", "iat", "email"]},
        leeway=30,
    )
    email = payload.get("email")
    if not email or "@" not in email:
        raise jwt.InvalidTokenError("JWT sem email válido.")
    return email

def server_identity_hook(
    *,
    auth_server_url_env: str = "FASTFLOW_AUTH_SERVER_URL",
    token_dir_env: str = "FASTFLOW_AUTH_TOKEN_DIR",
    token_file_env: str = "FASTFLOW_AUTH_TOKEN_FILE",
    require_env: str = "FASTFLOW_AUTH_REQUIRE",
    timeout_env: str = "FASTFLOW_AUTH_TIMEOUT",
    poll_interval_env: str = "FASTFLOW_AUTH_POLL_INTERVAL",
    public_key_cache_file_env: str = "FASTFLOW_AUTH_PUBLIC_KEY_FILE",
    expected_audience: str = "fastflow",
    expected_issuer: str = "fastflow-auth",
    tag_prefix: str = "user"
):
    """Cria um hook de identidade que autentica o usuário via servidor JWT.

    Implementa um fluxo completo de autenticação baseado em tokens JWT
    com as seguintes etapas:

    1. **Cache de chave pública:** carrega a chave pública PEM do cache
       local ou a busca no servidor de autenticação (``/auth/public-key``).
    2. **Token cacheado:** tenta utilizar um token JWT previamente salvo
       no disco, validando sua assinatura e expiração.
    3. **Login interativo:** caso não haja token válido, cria um ticket
       no servidor (``/auth/ticket``), abre o navegador para login e
       faz polling (``/auth/poll``) até receber o token autenticado.
    4. **Injeção no estado:** adiciona a tag ``{tag_prefix}:{email}``
       e popula ``state["context"]["user_email"]``.

    O hook também lida com rotação de chaves, refazendo o cache da chave
    pública quando detecta assinatura inválida.

    Args:
        auth_server_url_env: Variável de ambiente com a URL do servidor
            de autenticação. Padrão: ``"FASTFLOW_AUTH_SERVER_URL"``.
        token_dir_env: Variável de ambiente com o diretório de cache
            de tokens. Padrão: ``"FASTFLOW_AUTH_TOKEN_DIR"``.
        token_file_env: Variável de ambiente com o nome do arquivo de
            token. Padrão: ``"FASTFLOW_AUTH_TOKEN_FILE"``.
        require_env: Variável de ambiente que indica se a autenticação
            é obrigatória. Padrão: ``"FASTFLOW_AUTH_REQUIRE"``.
        timeout_env: Variável de ambiente com o timeout (em segundos)
            para polling. Padrão: ``"FASTFLOW_AUTH_TIMEOUT"``.
        poll_interval_env: Variável de ambiente com o intervalo de
            polling em segundos. Padrão: ``"FASTFLOW_AUTH_POLL_INTERVAL"``.
        public_key_cache_file_env: Variável de ambiente com o nome do
            arquivo de cache da chave pública. Padrão:
            ``"FASTFLOW_AUTH_PUBLIC_KEY_FILE"``.
        expected_audience: Audiência esperada no token JWT. Padrão:
            ``"fastflow"``.
        expected_issuer: Emissor esperado no token JWT. Padrão:
            ``"fastflow-auth"``.
        tag_prefix: Prefixo da tag de identidade. Padrão: ``"user"``.

    Returns:
        Função hook que recebe ``state`` e realiza autenticação JWT.

    Raises:
        RuntimeError: Se autenticação for obrigatória e a URL do servidor
            não estiver definida, ou se o timeout for atingido.
    """
    def hook(state: dict) -> None:
        require = os.getenv(require_env, "1").strip().lower() in ("1", "true", "yes", "y", "on")
        auth_url = os.getenv(auth_server_url_env, "").rstrip("/")

        if not auth_url:
            if require:
                raise RuntimeError(
                    f"Undefined {auth_server_url_env} (auth server URL). "
                    f"Set it to enable server identity tagging."
                )
            return

        token_dir = os.getenv(token_dir_env, "~/.fastflow/tokens")
        token_file = os.getenv(token_file_env, "fastflow_jwt.json")
        token_path = _expand(token_dir) / token_file

        # Cache da chave pública no mesmo diretório de token por padrão
        pubkey_file = os.getenv(public_key_cache_file_env, "fastflow_auth_public_key.pem")
        pubkey_path = _expand(token_dir) / pubkey_file

        # 0) garantir que temos a public key (cache ou server)
        public_key_pem = _load_cached_public_key(pubkey_path)
        if public_key_pem is None:
            public_key_pem, _, _ = _get_public_key_from_server(auth_url)
            _save_cached_public_key(pubkey_path, public_key_pem)
            print("Fetched and cached public key from auth server.")

        # 1) tentar usar token cacheado (com verificação de assinatura)
        token = _load_cached_token(token_path)
        if token:
            try:
                email = _decode_email_verified(
                    token,
                    public_key_pem,
                    expected_audience=expected_audience,
                    expected_issuer=expected_issuer,
                    algorithms=("RS256",),
                )
                state["tags"].append(f"{tag_prefix}:{email}")
                state["context"]["user_email"] = email
                print(f"Cached token valid. User email: {email}")
                return
            except jwt.ExpiredSignatureError:
                # expirou -> apaga token e segue pra login
                print("Cached token expired.")
                try:
                    token_path.unlink(missing_ok=True)
                except Exception:
                    pass
            except jwt.InvalidSignatureError:
                print("Cached token has invalid signature. Possible key rotation or token tampering.")
                # chave rotacionou ou token adulterado -> refaz cache de chave e tenta 1x
                try:
                    pubkey_path.unlink(missing_ok=True)
                except Exception:
                    pass
                public_key_pem, _, _ = _get_public_key_from_server(auth_url)
                _save_cached_public_key(pubkey_path, public_key_pem)
                try:
                    email = _decode_email_verified(
                        token,
                        public_key_pem,
                        expected_audience=expected_audience,
                        expected_issuer=expected_issuer,
                        algorithms=("RS256",),
                    )
                    state["tags"].append(f"{tag_prefix}:{email}")
                    state["context"]["user_email"] = email
                    return
                except Exception:
                    # token realmente inválido -> remove e segue pra login
                    try:
                        token_path.unlink(missing_ok=True)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error validating cached token: {e}")
                # qualquer outro erro de token -> remove e segue pra login
                try:
                    token_path.unlink(missing_ok=True)
                except Exception:
                    pass

        # 2) criar ticket
        r = requests.post(f"{auth_url}/auth/ticket", timeout=15)
        r.raise_for_status()
        ticket_id = r.json()["ticket_id"]
        login_url = r.json()["login_url"]

        print(
            "Please, log in to the auth server using the browser window that will open shortly. "
            f"If it doesn't open, access: {login_url}"
        )

        # 3) abrir browser
        webbrowser.open(login_url)

        # 4) polling até receber token
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
                # time.sleep(2)

                # garantir chave pública atualizada (pode ter rotacionado)
                public_key_pem = _load_cached_public_key(pubkey_path)
                if public_key_pem is None:
                    public_key_pem, _, _ = _get_public_key_from_server(auth_url)
                    _save_cached_public_key(pubkey_path, public_key_pem)
                # time.sleep(2)

                # validar token recém-recebido
                email = _decode_email_verified(
                    token,
                    public_key_pem,
                    expected_audience=expected_audience,
                    expected_issuer=expected_issuer,
                    algorithms=("RS256",),
                )
                state["tags"].append(f"{tag_prefix}:{email}")
                state["context"]["user_email"] = email
                return

            time.sleep(interval)

        raise RuntimeError("Timeout reached while waiting for authentication.")

    return hook