from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, overload, cast

from prefect import task as prefect_task
from prefect.context import FlowRunContext

F = TypeVar("F", bound=Callable[..., Any])


def _in_flow_run_context() -> bool:
    # FlowRunContext.get() retorna None fora de uma execução de flow
    return FlowRunContext.get() is not None


@overload
def ff_task(fn: F, /, **prefect_kwargs: Any) -> F: ...
@overload
def ff_task(*, name: Optional[str] = None, **prefect_kwargs: Any) -> Callable[[F], F]: ...


def ff_task(fn: Optional[F] = None, /, name: Optional[str] = None, **prefect_kwargs: Any):
    """
    Decorator FastFlow para task (Prefect por baixo).

    - Dentro de um FlowRunContext: chama como Prefect Task (track, retries, etc).
    - Fora de um FlowRunContext: executa como função normal (útil para scripts/testes).
    """
    def decorator(func: F) -> F:
        ptask = prefect_task(func, name=name, **prefect_kwargs)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            if _in_flow_run_context():
                return ptask(*args, **kwargs)
            return func(*args, **kwargs)

        # expor ergonomia do Prefect Task quando estiver em flow
        # (útil: .submit, .map, .with_options)
        for attr in ("submit", "map", "with_options"):
            if hasattr(ptask, attr):
                setattr(wrapper, attr, getattr(ptask, attr))

        # acesso à função original e à task Prefect (pra debug/inspeção)
        setattr(wrapper, "fn", func)
        setattr(wrapper, "__prefect_task__", ptask)

        return cast(F, wrapper)

    if fn is not None:
        return decorator(fn)

    return decorator