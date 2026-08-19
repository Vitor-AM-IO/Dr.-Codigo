"""Carrega configuração a partir de variáveis de ambiente (e de um .env, se existir)."""

import os
from pathlib import Path

# Modelo padrão. Pode ser trocado por variável de ambiente ou pela flag --model.
DEFAULT_MODEL = "claude-sonnet-5"

# Pasta de memória do projeto (cache de revisões + backups). Estilo ".git".
STATE_DIR = ".code-doctor"

# Arquivos maiores que isto são pulados por padrão (economia + evita estouro de tokens).
MAX_FILE_BYTES = 120_000

# Extensões de arquivo consideradas "código" por padrão.
DEFAULT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".rs", ".swift", ".kt", ".scala",
    ".sh", ".bash", ".sql", ".html", ".css", ".vue", ".svelte",
}

# Pastas ignoradas ao varrer diretórios.
IGNORED_DIRS = {
    ".git", ".code-doctor", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".mypy_cache", ".pytest_cache", "vendor", "target",
}


def _load_dotenv() -> None:
    """Lê um arquivo .env simples (KEY=VALUE) do diretório atual, sem dependências."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)  # não sobrescreve o ambiente real


def get_api_key() -> str:
    """Retorna a chave da API da Anthropic ou levanta um erro claro."""
    _load_dotenv()
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "\n[erro] Chave da API não encontrada.\n"
            "  Defina a variável ANTHROPIC_API_KEY ou crie um arquivo .env com:\n"
            "  ANTHROPIC_API_KEY=sua-chave-aqui\n"
            "  (copie o .env.example para .env e preencha)\n"
        )
    return key


def get_model(override: str | None = None) -> str:
    if override:
        return override
    return os.environ.get("CODE_DOCTOR_MODEL", DEFAULT_MODEL)


# Preços por milhão de tokens (USD), usados só para ESTIMAR custo na barra visual.
# Padrão: Claude Sonnet 5 ($2 entrada / $10 saída). Ajustáveis por ambiente.
def price_in_per_mtok() -> float:
    return float(os.environ.get("CODE_DOCTOR_PRICE_IN", "2.0"))


def price_out_per_mtok() -> float:
    return float(os.environ.get("CODE_DOCTOR_PRICE_OUT", "10.0"))
