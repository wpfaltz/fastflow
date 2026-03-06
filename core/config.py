from __future__ import annotations
import os
from typing import Optional

def env(key: str, default: Optional[str] = None) -> str:
    """Obtém o valor de uma variável de ambiente, com suporte a valor padrão.

    Busca a variável de ambiente identificada por ``key`` utilizando ``os.getenv``.
    Caso a variável não esteja definida e nenhum valor padrão (``default``) tenha
    sido fornecido, levanta ``RuntimeError`` para sinalizar que uma configuração
    obrigatória está ausente.

    Args:
        key: Nome da variável de ambiente a ser consultada.
        default: Valor padrão retornado quando a variável não existe no
            ambiente. Se ``None`` (padrão) e a variável não existir, uma
            exceção será levantada.

    Returns:
        O valor da variável de ambiente como string.

    Raises:
        RuntimeError: Se a variável não estiver definida e ``default`` for
            ``None``.
    """
    val = os.getenv(key, default)
    if val is None:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {key}")
    return val

def env_bool(key: str, default: bool = False) -> bool:
    """Obtém o valor booleano de uma variável de ambiente.

    Lê a variável de ambiente ``key`` e interpreta seu conteúdo como um valor
    booleano. Os valores ``"1"``, ``"true"``, ``"yes"``, ``"y"`` e ``"on"``
    (case-insensitive, com espaços aparados) são considerados ``True``;
    qualquer outro valor é considerado ``False``. Se a variável não existir,
    retorna ``default``.

    Args:
        key: Nome da variável de ambiente.
        default: Valor booleano retornado quando a variável não está definida.
            Padrão é ``False``.

    Returns:
        ``True`` se o conteúdo da variável corresponder a um valor truthy,
        ``False`` caso contrário, ou ``default`` se a variável não existir.
    """
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")

def env_int(key: str, default: int) -> int:
    """Obtém o valor inteiro de uma variável de ambiente.

    Lê a variável de ambiente ``key`` e converte seu conteúdo para ``int``.
    Se a variável não estiver definida, retorna o valor ``default``.

    Args:
        key: Nome da variável de ambiente.
        default: Valor inteiro retornado quando a variável não está definida.

    Returns:
        O valor da variável convertido para inteiro, ou ``default`` se a
        variável não existir.

    Raises:
        ValueError: Se o conteúdo da variável não puder ser convertido para
            inteiro.
    """
    raw = os.getenv(key)
    if raw is None:
        return default
    return int(raw)
