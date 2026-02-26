from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional

EnvMode = Literal["os", "dotenv", "auto"]

def configure_environment(
    mode: Optional[EnvMode] = None,
    dotenv_path: Optional[str] = None,
    override: bool = False,
) -> None:
    """Configura o ambiente de execução do FastFlow carregando variáveis de ambiente.

    Suporta três modos de configuração de variáveis de ambiente:

    - ``"os"`` (ou ``None``): Não realiza nenhuma ação adicional;
      utiliza apenas as variáveis de ambiente já definidas no SO.
    - ``"dotenv"``: Carrega as variáveis de um arquivo ``.env``
      utilizando ``python-dotenv``. Levanta erro se ``python-dotenv``
      não estiver instalado.
    - ``"auto"``: Carrega o arquivo ``.env`` apenas se ele existir no
      caminho especificado; caso contrário, opera como ``"os"``.

    Args:
        mode: Estratégia de carregamento das variáveis de ambiente.
            Valores aceitos: ``"os"``, ``"dotenv"``, ``"auto"`` ou
            ``None`` (equivalente a ``"os"``). Padrão: ``None``.
        dotenv_path: Caminho do arquivo ``.env`` a ser carregado. Se
            ``None``, utiliza ``".env"`` no diretório atual.
        override: Se ``True``, as variáveis do arquivo ``.env``
            sobrescrevem as já definidas no ambiente do SO. Padrão:
            ``False``.

    Raises:
        RuntimeError: Se ``mode`` for ``"dotenv"`` ou ``"auto"`` e o
            pacote ``python-dotenv`` não estiver instalado.
    """
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
