from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from prefect import flow as prefect_flow
from prefect import tags as prefect_tags
from .runtime import set_context, reset_context

F = TypeVar("F", bound=Callable[..., Any])

def build_flow(
    *,
    name: Optional[str] = None,
    flow_id: Optional[str] = None,
    secret_ids: Optional[list[str]] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    hooks: Optional[list[Callable[[dict[str, Any]], None]]] = None,
    **prefect_kwargs: Any,
):
    """Fábrica de decoradores para criar flows FastFlow baseados no Prefect.

    Retorna um decorator configurável que transforma uma função Python em um
    flow Prefect com suporte a hooks, tags, secrets e contexto FastFlow.

    O decorator gerado executa os seguintes passos ao ser chamado:
    1. Monta um dicionário de estado (``state``) contendo ``flow_id``,
       ``tags``, ``secret_ids``, argumentos e contexto.
    2. Executa sequencialmente cada hook registrado, permitindo que eles
       modifiquem o estado (ex.: adicionar tags, popular secrets).
    3. Define o contexto FastFlow via ``set_context`` (acessível durante
       a execução do flow e suas tasks).
    4. Executa o flow Prefect dentro de ``prefect_tags`` com as tags
       acumuladas.
    5. Restaura o contexto original após a execução.

    Args:
        name: Nome do flow no Prefect. Se ``None``, utiliza o nome da
            função decorada.
        flow_id: Identificador único do flow no FastFlow, acessível nos
            hooks e no contexto de execução.
        secret_ids: Lista de identificadores de secrets a serem carregados
            pelos hooks (ex.: ``keyvault_hook``).
        description: Descrição textual do flow.
        tags: Lista de tags Prefect iniciais a serem aplicadas ao flow.
        hooks: Lista de funções hook que recebem o dicionário ``state``
            e podem modificá-lo antes da execução do flow (ex.: carregar
            secrets, adicionar tags de ambiente).
        **prefect_kwargs: Parâmetros adicionais repassados diretamente
            ao decorator ``prefect.flow``.

    Returns:
        Um decorator que aceita uma função e retorna um wrapper com
        comportamento de flow FastFlow/Prefect.
    """
    hooks = hooks or []

    def flow_decorator(
        fn: Optional[F] = None,
        /,
        *,
        flow_id: Optional[str] = flow_id,
        tags: Optional[list[str]] = tags,
        secret_ids: Optional[list[str]] = secret_ids
    ):
        def decorator(func: F) -> F:
            pf = prefect_flow(func, name=name, **prefect_kwargs)
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any):
                state: dict[str, Any] = {
                    "flow_id": flow_id,
                    "tags": list(tags or []),
                    "secret_ids": list(secret_ids or []),
                    "args": args,
                    "kwargs": kwargs,
                    "context": {},
                }

                # Executa hooks (podem preencher state["context"], state["tags"], etc.)
                for hook in hooks:
                    hook(state)

                token = set_context(state["context"])
                try:
                    with prefect_tags(*state["tags"]):
                        return pf(*args, **kwargs)
                finally:
                    reset_context(token)

            setattr(wrapper, "__prefect_flow__", pf)
            return cast(F, wrapper)
        if fn is not None:
            return decorator(fn)

        return decorator

    return flow_decorator