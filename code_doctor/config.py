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


def usd_brl() -> float:
    """Cotação dólar→real para a estimativa em R$. Ajustável por ambiente."""
    try:
        return float(os.environ.get("CODE_DOCTOR_USD_BRL", "5.17"))
    except ValueError:
        return 5.17


# Limites para análise de projeto (.zip): evita custo alto e uploads gigantes.
MAX_ZIP_FILES = 20          # nº máximo de arquivos analisados por zip
ZIP_MAX_BYTES = 8_000_000   # tamanho máximo do zip enviado (8 MB)


# ---- Central de configuração na tela (igual ao Construtor) ----

PROVEDORES_UI = {
    "anthropic": {"nome": "Anthropic (Claude)", "chave": "ANTHROPIC_API_KEY",
                  "precisa_chave": True, "modelo_padrao": "claude-sonnet-5"},
    "groq":      {"nome": "Groq (grátis, nuvem)", "chave": "GROQ_API_KEY",
                  "precisa_chave": True, "modelo_padrao": "llama-3.3-70b-versatile"},
    "openai":    {"nome": "OpenAI", "chave": "OPENAI_API_KEY",
                  "precisa_chave": True, "modelo_padrao": "gpt-4o-mini"},
    "ollama":    {"nome": "Ollama (grátis, no seu PC)", "chave": None,
                  "precisa_chave": False, "modelo_padrao": "llama3.1"},
}

# Preços por 1M tokens (entrada, saída) — estimativa para a barrinha de custo.
MODEL_PRICES = {
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "gpt-4o-mini": (0.15, 0.60),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}


def precos_do_modelo(provider: str, model: str) -> tuple[float, float]:
    if provider in ("ollama", "lmstudio"):
        return (0.0, 0.0)
    return MODEL_PRICES.get(model, (price_in_per_mtok(), price_out_per_mtok()))


def ollama_rodando() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1):
            return True
    except Exception:
        return False


def mascarar_chave(valor: str) -> str:
    v = (valor or "").strip()
    if not v:
        return ""
    return v[0] + "…" if len(v) <= 8 else f"{v[:4]}…{v[-4:]}"


def _provider_atual() -> str:
    return os.environ.get("CODE_DOCTOR_PROVIDER", "anthropic").lower()


def estado_atual() -> dict:
    _load_dotenv()
    prov = _provider_atual()
    info = PROVEDORES_UI.get(prov, PROVEDORES_UI["anthropic"])
    model = os.environ.get("CODE_DOCTOR_MODEL", info["modelo_padrao"])
    chave = os.environ.get(info["chave"], "").strip() if info["chave"] else ""
    pin, pout = precos_do_modelo(prov, model)
    return {"provider": prov, "model": model, "tem_chave": bool(chave),
            "chave_mascarada": mascarar_chave(chave),
            "price_in": pin, "price_out": pout, "usd_brl": usd_brl()}


def salvar_config(provider: str, model: str, chave: str | None) -> tuple[bool, str]:
    provider = (provider or "").lower().strip()
    if provider not in PROVEDORES_UI:
        return False, "provedor desconhecido"
    info = PROVEDORES_UI[provider]
    model = (model or info["modelo_padrao"]).strip()

    env_path = Path.cwd() / ".env"
    linhas: dict[str, str] = {}
    if env_path.exists():
        for ln in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, _, v = ln.partition("=")
                linhas[k.strip()] = v.strip()

    linhas["CODE_DOCTOR_PROVIDER"] = provider
    linhas["CODE_DOCTOR_MODEL"] = model
    if info["precisa_chave"]:
        chave = (chave or "").strip()
        if chave:
            linhas[info["chave"]] = chave
        elif info["chave"] not in linhas:
            return False, f"o provedor {info['nome']} precisa de uma chave"

    env_path.write_text("\n".join(f"{k}={v}" for k, v in linhas.items()) + "\n",
                        encoding="utf-8")
    os.environ["CODE_DOCTOR_PROVIDER"] = provider
    os.environ["CODE_DOCTOR_MODEL"] = model
    if info["precisa_chave"] and chave:
        os.environ[info["chave"]] = chave
    return True, "configuração salva"
