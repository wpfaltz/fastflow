from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, overload, cast

from prefect import task as prefect_task
from prefect.context import FlowRunContext

F = TypeVar("F", bound=Callable[..., Any])


def _in_flow_run_context() -> bool:
    """Verifica se a execução atual está dentro de um FlowRunContext do Prefect.

    Utiliza ``FlowRunContext.get()`` para determinar se o código está sendo
    executado dentro de um flow Prefect ativo. Retorna ``True`` se houver
    um contexto de flow, ``False`` caso contrário.

    Returns:
        ``True`` se a execução estiver dentro de um flow Prefect, ``False``
        caso contrário (ex.: em scripts ou testes unitários).
    """
    # FlowRunContext.get() retorna None fora de uma execução de flow
    return FlowRunContext.get() is not None


@overload
def ff_task(fn: F, /, **prefect_kwargs: Any) -> F: ...
@overload
def ff_task(*, name: Optional[str] = None, **prefect_kwargs: Any) -> Callable[[F], F]: ...


def ff_task(fn: Optional[F] = None, /, name: Optional[str] = None, **prefect_kwargs: Any):
    """Decorator FastFlow para criar tasks compatíveis com Prefect.

    Transforma uma função Python em uma task que se adapta automaticamente
    ao contexto de execução:

    - **Dentro de um FlowRunContext (flow Prefect ativo):** executa a função
      como uma Prefect Task com tracking, retries e demais funcionalidades
      do Prefect.
    - **Fora de um FlowRunContext:** executa a função original diretamente,
      sem overhead do Prefect. Útil para scripts avulsos e testes unitários.

    O wrapper resultante expõe os métodos ergonômicos da Prefect Task
    (``submit``, ``map``, ``with_options``), além dos atributos ``fn``
    (função original) e ``__prefect_task__`` (instância da task Prefect)
    para fins de debug e inspeção.

    Pode ser usado com ou sem parênteses:
        - ``@ff_task`` (sem argumentos)
        - ``@ff_task(name="minha_task", retries=3)``

    Args:
        fn: Função a ser decorada. Preenchido automaticamente quando o
            decorator é usado sem parênteses.
        name: Nome da task no Prefect. Se ``None``, utiliza o nome da
            função decorada.
        **prefect_kwargs: Parâmetros adicionais repassados ao decorator
            ``prefect.task`` (ex.: ``retries``, ``retry_delay_seconds``,
            ``cache_key_fn``).

    Returns:
        A função decorada como wrapper FastFlow/Prefect, ou um decorator
        se ``fn`` não for fornecido.
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