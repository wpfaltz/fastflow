from __future__ import annotations

import platform


def os_hook(prefix: str = "os"):
    """
    Adiciona uma tag indicando o sistema operacional da máquina onde o flow rodou.

    Exemplos:
      os:windows-11
      os:windows-10
      os:linux-ubuntu-22.04
      os:macos-14
    """
    def _sanitize(s: str) -> str:
        s = s.strip().lower()
        # tags melhores sem espaços
        s = s.replace(" ", "-").replace("_", "-")
        # reduz repetições de hífen
        while "--" in s:
            s = s.replace("--", "-")
        return s

    def hook(state: dict) -> None:
        sys = platform.system()   # Windows, Linux, Darwin
        rel = platform.release()  # 10, 11, 5.15.0-..., etc.

        if sys.lower() == "darwin":
            sys = "macos"

        # opcional: distro para linux (stdlib não dá distro; deixo simples)
        tag_value = _sanitize(f"{sys}-{rel}")

        state["tags"].append(f"{prefix}:{tag_value}")
        state["context"]["os_system"] = sys
        state["context"]["os_release"] = rel

    return hook
