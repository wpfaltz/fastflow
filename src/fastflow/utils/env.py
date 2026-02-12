from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional

EnvMode = Literal["os", "dotenv", "auto"]

def configure_environment(
    mode: Optional[EnvMode] = None,
    dotenv_path: Optional[str] = None,
    override: bool = False,
) -> None:
    if mode is None or mode == "os":
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        raise RuntimeError("Instale python-dotenv para usar mode='dotenv' ou 'auto'.")

    path = Path(dotenv_path or ".env")

    if mode == "dotenv":
        load_dotenv(dotenv_path=path, override=override)
    elif mode == "auto" and path.exists():
        load_dotenv(dotenv_path=path, override=override)
