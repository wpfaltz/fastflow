from __future__ import annotations

import platform


def os_hook(prefix: str = "os"):
    """Cria um hook que adiciona uma tag com o sistema operacional ao flow.

    Detecta o sistema operacional e a versão da máquina onde o flow está
    sendo executado utilizando o módulo ``platform``, e adiciona uma tag
    no formato ``{prefix}:{sistema}-{versão}`` (ex.: ``os:windows-11``,
    ``os:linux-5.15.0``, ``os:macos-14``).

    Além da tag, popula ``state["context"]`` com as chaves ``os_system``
    e ``os_release`` para acesso programático.

    Args:
        prefix: Prefixo da tag de sistema operacional. Padrão: ``"os"``.

    Returns:
        Função hook que recebe ``state`` e adiciona a tag de SO e dados
        de contexto.
    """
    def _sanitize(s: str) -> str:
        """Sanitiza uma string para uso como valor de tag.

        Converte para minúsculas, substitui espaços e underscores por
        hífens e remove hífens duplicados.

        Args:
            s: String a ser sanitizada.

        Returns:
            String normalizada e segura para uso como tag.
        """
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
