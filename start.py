#!/usr/bin/env python3
"""Atalho para iniciantes: abre o Code Doctor no navegador.

Como usar (sem saber terminal):
  1) instale o Python 3.10+  (python.org)
  2) coloque sua chave num arquivo .env  (copie o .env.example)
  3) dê dois cliques neste arquivo, ou rode:  python start.py

Ele instala o necessário na primeira vez e abre a página automaticamente.
"""

import subprocess
import sys


def _ensure_deps() -> None:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        print("Instalando dependências (só na primeira vez)…")
        subprocess.run([sys.executable, "-m", "pip", "install", "anthropic"],
                       check=False)


def main() -> None:
    _ensure_deps()
    # roda como módulo para não depender de instalação prévia do pacote
    from code_doctor import web
    from code_doctor import config
    try:
        config.get_api_key()
    except SystemExit as e:
        print(e)
        input("\nPressione Enter para sair…")
        return
    web.serve()


if __name__ == "__main__":
    main()
