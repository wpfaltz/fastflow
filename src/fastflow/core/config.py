from __future__ import annotations
import os
from typing import Optional

def env(key: str, default: Optional[str] = None) -> str:
    val = os.getenv(key, default)
    if val is None:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {key}")
    return val

def env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")

def env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    return int(raw)
