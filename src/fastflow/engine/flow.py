from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from prefect import flow as prefect_flow
from prefect import tags as prefect_tags

F = TypeVar("F", bound=Callable[..., Any])

# def ff_flow(
#     fn: Optional[F] = None,
#     /,
#     *,
#     name: Optional[str] = None,
#     flow_id: Optional[str] = None,
#     secret_ids: Optional[list[str]] = None,
#     tags: Optional[list[str]] = None,
#     **prefect_kwargs: Any,
# ):
#     """
#     Decorator FastFlow para flow (Prefect por baixo), com pré/pós gancho.

#     Parâmetros FastFlow (iniciais):
#     - flow_id: identificador lógico do flow (vira tag, logging, etc.)
#     - secret_ids: lista de segredos necessários (gancho pro Key Vault)
#     - tags: tags adicionais (além das automáticas)

#     Qualquer outro parâmetro vai para o prefect.flow via **prefect_kwargs.
#     """
#     def decorator(func: F) -> F:
#         pf = prefect_flow(func, name=name, **prefect_kwargs)

#         @wraps(func)
#         def wrapper(*args: Any, **kwargs: Any):
#             cfg = _server_config()
#             hostname, username = _runner_identity()

#             is_server = (
#                 _norm(hostname) == _norm(cfg["server_host"])
#                 and _norm(username) == _norm(cfg["server_user"])
#             )

#             env_tag_value = cfg["env_prd"] if is_server else cfg["env_dev"]
#             host_tag_value = cfg["server_host_tag"] if is_server else hostname
#             user_tag_value = cfg["server_user_tag"] if is_server else username

#             run_tags: list[str] = [
#                 f"env:{env_tag_value}",
#                 f"host:{host_tag_value}",
#                 f"user:{user_tag_value}",
#             ]

#             if tags:
#                 run_tags.extend(tags)

#             # TODO(v0.2): secret loader (Key Vault)
#             # ex.: if secret_ids: load_secrets(secret_ids)

#             with prefect_tags(*run_tags):
#                 # TODO: load_secrets(secret_ids)
#                 return pf(*args, **kwargs)            

#             # try:
#             #     result = func(*args, **kwargs)
#             #     # --- POST (sucesso) ---
#             #     return result
#             # except Exception:
#             #     # --- POST (erro) ---
#             #     raise
#             # finally:
#             #     # TODO(v0.2): flush/upload logs
#             #     pass

#         setattr(wrapper, "__prefect_flow__", pf)
#         return cast(F, wrapper)

#     if fn is not None:
#         return decorator(fn)

#     return decorator

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

                # Executa hooks
                for hook in hooks:
                    hook(state)

                with prefect_tags(*state["tags"]):
                    return pf(*args, **kwargs)

            setattr(wrapper, "__prefect_flow__", pf)
            return cast(F, wrapper)

        if fn is not None:
            return decorator(fn)

        return decorator

    return flow_decorator