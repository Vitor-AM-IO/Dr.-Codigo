#!/usr/bin/env python3
"""Atalho para iniciantes: abre o Dr. Código no navegador.

Na primeira vez, instala o necessário e pergunta a sua chave (salvando no .env,
sem enviar pra internet). Depois é só abrir. Funciona em Windows, Mac e Linux
(inclusive Debian/Ubuntu, que bloqueiam o pip do sistema).
"""

import os
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = "sua-chave-aqui"


def _pip_install(pkg: str) -> bool:
    """Instala um pacote tentando as formas que funcionam em cada sistema.

    No Windows/Mac (e Linux com permissão) o modo normal já resolve. No
    Debian/Ubuntu, o pip do sistema é 'externally managed', então usamos
    --user --break-system-packages, que instala na pasta do usuário sem mexer
    no sistema.
    """
    attempts = [
        [],                                      # normal (Windows/Mac/root)
        ["--user", "--break-system-packages"],   # Debian/Ubuntu (usuário comum)
    ]
    for extra in attempts:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, *extra],
                capture_output=True, text=True,
            )
        except Exception:
            continue
        if r.returncode == 0:
            return True
    return False


def _dep_help_and_exit() -> None:
    print("\n" + "=" * 60)
    print("  Não consegui instalar o necessário automaticamente.")
    print("=" * 60)
    print("\nNo Linux (Debian/Ubuntu), rode UMA destas opções no terminal:\n")
    print("  Opção A — simples:")
    print("    pip install --user --break-system-packages anthropic\n")
    print("  Opção B — ambiente isolado (recomendado):")
    print("    sudo apt install -y python3-venv")
    print("    python3 -m venv .venv")
    print("    source .venv/bin/activate")
    print("    pip install anthropic")
    print("    python start.py\n")
    print("Depois de instalar, rode de novo:  python3 start.py")
    try:
        input("\nPressione Enter para sair…")
    except (EOFError, KeyboardInterrupt):
        pass
    sys.exit(1)


def _ensure_deps() -> None:
    try:
        import anthropic  # noqa: F401
        return
    except ImportError:
        pass

    # Se já tentamos instalar e reiniciar uma vez e ainda falta, mostra ajuda.
    if os.environ.get("DRC_DEP_RETRY") == "1":
        _dep_help_and_exit()

    print("Instalando o necessário (só na primeira vez)… aguarde.\n")
    if _pip_install("anthropic"):
        # Reinicia o programa para carregar o pacote recém-instalado.
        os.environ["DRC_DEP_RETRY"] = "1"
        try:
            os.execv(sys.executable, [sys.executable, *sys.argv])
        except OSError:
            pass
    _dep_help_and_exit()


def _has_key() -> bool:
    from code_doctor import config
    config._load_dotenv()
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
                "GROQ_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
                "CODE_DOCTOR_API_KEY"):
        val = os.environ.get(var, "").strip()
        if val and val != PLACEHOLDER:
            return True
    if os.environ.get("CODE_DOCTOR_PROVIDER", "").lower() in ("ollama", "lmstudio"):
        return True
    return False


def _ask_and_save_key() -> bool:
    print("=" * 60)
    print("  Bem-vindo ao Dr. Código! 🩺")
    print("  Primeira vez por aqui — vamos guardar a sua chave.")
    print("=" * 60)
    print()
    print("  Pegue sua chave em:  https://platform.claude.com/settings/keys")
    print("  Ela começa com 'sk-ant-'. Copie e cole aqui embaixo.")
    print("  (para colar no terminal, clique com o botão direito do mouse)")
    print()
    try:
        key = input("  Cole sua chave e aperte Enter: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelado.")
        return False

    if not key or key == PLACEHOLDER:
        print("\n  Nenhuma chave digitada.")
        return False

    env_path = Path.cwd() / ".env"
    line = f"ANTHROPIC_API_KEY={key}\n"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        if "ANTHROPIC_API_KEY=" in content:
            print("\n  Já existe uma chave no .env — não vou sobrescrever.")
        else:
            env_path.write_text(content.rstrip("\n") + "\n" + line, encoding="utf-8")
            print("\n  ✓ Chave salva no arquivo .env (no seu computador).")
    else:
        env_path.write_text(line, encoding="utf-8")
        print("\n  ✓ Chave salva no arquivo .env (no seu computador).")

    os.environ["ANTHROPIC_API_KEY"] = key
    return True


def main() -> None:
    _ensure_deps()
    if not _has_key():
        if not _ask_and_save_key():
            input("\nPressione Enter para sair…")
            return
    print("\nAbrindo o Dr. Código no seu navegador… 🩺")
    from code_doctor import web
    web.serve()


if __name__ == "__main__":
    main()
