from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Contexto atual do FastFlow durante execução do flow
_fastflow_ctx: ContextVar[dict[str, Any] | None] = ContextVar("_fastflow_ctx", default=None)


def set_context(ctx: dict[str, Any]) -> Any:
    """Define o contexto FastFlow para a execução corrente.

    Armazena o dicionário de contexto na ``ContextVar`` interna, tornando-o
    acessível durante toda a execução do flow e suas tasks via ``get_context``.
    Retorna um token que deve ser passado a ``reset_context`` para restaurar
    o estado anterior.

    Args:
        ctx: Dicionário contendo dados de contexto do flow (ex.: secrets,
            email do usuário, informações do ambiente).

    Returns:
        Token opaco que pode ser utilizado em ``reset_context`` para
        restaurar o valor anterior da ``ContextVar``.
    """
    return _fastflow_ctx.set(ctx)


def reset_context(token: Any) -> None:
    """Restaura o contexto FastFlow para o estado anterior.

    Utiliza o token retornado por ``set_context`` para reverter a
    ``ContextVar`` ao valor que possuía antes da última chamada a
    ``set_context``. Deve ser invocado em um bloco ``finally`` para
    garantir a limpeza adequada do contexto.

    Args:
        token: Token opaco retornado por ``set_context``.
    """
    _fastflow_ctx.reset(token)


def get_context() -> dict[str, Any]:
    """Recupera o contexto FastFlow da execução corrente.

    Retorna o dicionário de contexto previamente definido por ``set_context``.
    Este método só pode ser chamado dentro de uma execução de flow FastFlow;
    caso contrário, levanta ``RuntimeError``.

    Returns:
        Dicionário de contexto contendo dados como secrets, identidade do
        usuário e informações do ambiente.

    Raises:
        RuntimeError: Se o contexto não estiver disponível (chamada fora
            de um flow FastFlow).
    """
    ctx = _fastflow_ctx.get()
    if ctx is None:
        raise RuntimeError("FastFlow context is not available. Are you inside an ff_flow execution?")
    return ctx


def get_secrets() -> dict[str, str]:
    """Recupera todos os secrets carregados no contexto FastFlow.

    Obtém o dicionário de secrets armazenado sob a chave ``"secrets"`` no
    contexto de execução do flow. Tipicamente populado pelo
    ``keyvault_hook``.

    Returns:
        Dicionário mapeando nomes de secrets para seus valores.

    Raises:
        RuntimeError: Se o contexto FastFlow não estiver disponível.
    """
    ctx = get_context()
    return ctx.get("secrets", {})


def get_secret(name: str) -> str:
    """Recupera um secret específico do contexto FastFlow.

    Busca o valor do secret identificado por ``name`` no dicionário de
    secrets do contexto de execução. Levanta ``KeyError`` se o secret
    não tiver sido carregado.

    Args:
        name: Nome (identificador) do secret desejado.

    Returns:
        Valor do secret como string.

    Raises:
        KeyError: Se o secret ``name`` não estiver presente no contexto.
        RuntimeError: Se o contexto FastFlow não estiver disponível.
    """
    secrets = get_secrets()
    if name not in secrets:
        raise KeyError(f"Secret not loaded in context: {name}")
    return secrets[name]