#!/usr/bin/env bash
# Lançador do Dr. Código para Linux e Mac.
# Uso: dê permissão uma vez com  chmod +x start.sh  e rode  ./start.sh
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    exec python3 start.py
fi

echo "============================================================"
echo "  O Python 3 nao esta instalado (o Dr. Codigo precisa dele)."
echo "============================================================"
echo ""
if command -v apt >/dev/null 2>&1; then
    echo "Instale com:"
    echo "  sudo apt update && sudo apt install -y python3 python3-venv"
elif command -v dnf >/dev/null 2>&1; then
    echo "Instale com:  sudo dnf install -y python3"
elif command -v pacman >/dev/null 2>&1; then
    echo "Instale com:  sudo pacman -S python"
elif command -v brew >/dev/null 2>&1; then
    echo "Instale com:  brew install python"
else
    echo "Instale o Python 3 pelo gerenciador de pacotes do seu sistema."
fi
echo ""
echo "Depois rode de novo:  ./start.sh"
read -r -p "Pressione Enter para sair..."
