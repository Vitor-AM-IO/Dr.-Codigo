"""Memória do projeto: cache de revisões por hash de arquivo, para economizar tokens.

Guarda um resumo do que já foi revisado em `.code-doctor/cache.json`. Se um
arquivo não mudou (mesmo hash) e o modelo é o mesmo, a revisão anterior é
reaproveitada e **nenhuma chamada à API é feita**.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import __version__, config

_CACHE_VERSION = 1


def state_dir() -> Path:
    """Pasta de estado do projeto (criada sob demanda no diretório atual)."""
    d = Path.cwd() / config.STATE_DIR
    d.mkdir(exist_ok=True)
    return d


def _cache_path() -> Path:
    return state_dir() / "cache.json"


def file_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load() -> dict:
    path = _cache_path()
    if not path.exists():
        return {"version": _CACHE_VERSION, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != _CACHE_VERSION:
            return {"version": _CACHE_VERSION, "entries": {}}
        return data
    except (json.JSONDecodeError, OSError):
        return {"version": _CACHE_VERSION, "entries": {}}


def save(cache: dict) -> None:
    try:
        _cache_path().write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass  # cache é best-effort; nunca deve quebrar a execução


def _key(path: Path) -> str:
    return str(path.resolve())


def get(cache: dict, path: Path, content_hash: str, model: str) -> dict | None:
    """Retorna a revisão salva se hash, modelo e versão do tool baterem."""
    entry = cache.get("entries", {}).get(_key(path))
    if not entry:
        return None
    if (entry.get("hash") == content_hash
            and entry.get("model") == model
            and entry.get("tool") == __version__):
        return entry.get("review")
    return None


def put(cache: dict, path: Path, content_hash: str, model: str,
        review_dict: dict) -> None:
    cache.setdefault("entries", {})[_key(path)] = {
        "hash": content_hash,
        "model": model,
        "tool": __version__,
        "review": review_dict,
    }


def clear() -> None:
    p = _cache_path()
    if p.exists():
        p.unlink()
