"""Núcleo: envia o código ao provedor de IA e interpreta a resposta.

Independente de provedor (Anthropic, OpenAI-compatível, etc.) — recebe um objeto
`provider` já pronto. Integra a memória (cache) e mede o uso de tokens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import cache as cache_mod
from . import config, prompts
from .providers import Usage, ProviderError

_LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript (React)",
    ".ts": "TypeScript", ".tsx": "TypeScript (React)", ".java": "Java",
    ".go": "Go", ".rb": "Ruby", ".php": "PHP", ".c": "C", ".h": "C",
    ".cpp": "C++", ".hpp": "C++", ".cs": "C#", ".rs": "Rust",
    ".swift": "Swift", ".kt": "Kotlin", ".scala": "Scala", ".sh": "Shell",
    ".bash": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
    ".vue": "Vue", ".svelte": "Svelte",
}


@dataclass
class Issue:
    line: int | None
    severity: str
    title: str
    description: str
    suggestion: str = ""


@dataclass
class Review:
    path: Path
    summary: str
    issues: list[Issue] = field(default_factory=list)
    corrected_code: str = ""
    changed: bool = False
    error: str | None = None
    from_cache: bool = False
    usage: Usage = field(default_factory=Usage)

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict:
        return {"summary": self.summary, "issues": [asdict(i) for i in self.issues],
                "corrected_code": self.corrected_code, "changed": self.changed}

    @classmethod
    def from_dict(cls, path: Path, data: dict) -> "Review":
        return cls(path=path, summary=data.get("summary", ""),
                   issues=[Issue(**i) for i in data.get("issues", [])],
                   corrected_code=data.get("corrected_code", ""),
                   changed=data.get("changed", False), from_cache=True)


def _language_for(path: Path) -> str:
    return _LANG_BY_EXT.get(path.suffix.lower(), "desconhecida")


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def _parse_review(path: Path, raw: str, code: str, usage: Usage) -> Review:
    try:
        data = json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError:
        return Review(path=path, summary="", usage=usage,
                      error="resposta do modelo não veio em JSON válido")
    issues = [
        Issue(line=i.get("line"), severity=str(i.get("severity", "medium")).lower(),
              title=i.get("title", "").strip(),
              description=i.get("description", "").strip(),
              suggestion=i.get("suggestion", "").strip())
        for i in data.get("issues", [])
    ]
    return Review(path=path, summary=data.get("summary", "").strip(), issues=issues,
                  corrected_code=data.get("corrected_code", code),
                  changed=bool(data.get("changed", False)), usage=usage)


def analyze_file(path: Path, provider, cache: dict | None = None,
                 use_cache: bool = True, max_tokens: int = 8000) -> Review:
    """Analisa um arquivo. Usa a memória (cache) quando o conteúdo não mudou."""
    try:
        code = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return Review(path=path, summary="", error=f"não foi possível ler: {exc}")

    if not code.strip():
        return Review(path=path, summary="arquivo vazio", corrected_code=code)
    if len(code.encode("utf-8")) > config.MAX_FILE_BYTES:
        return Review(path=path, summary="",
                      error=f"arquivo muito grande (>{config.MAX_FILE_BYTES} bytes); pulado.")

    content_hash = cache_mod.file_hash(code)
    cache_id = f"{provider.name}:{provider.model}"
    if use_cache and cache is not None:
        hit = cache_mod.get(cache, path, content_hash, cache_id)
        if hit is not None:
            return Review.from_dict(path, hit)

    user_msg = prompts.build_user_message(path.name, _language_for(path), code)
    try:
        raw, usage = provider.complete(prompts.SYSTEM_PROMPT, user_msg, max_tokens)
    except ProviderError as exc:
        return Review(path=path, summary="", error=f"erro no provedor: {exc}")

    review = _parse_review(path, raw, code, usage)
    if cache is not None and review.ok:
        cache_mod.put(cache, path, content_hash, cache_id, review.to_dict())
    return review


def review_text(code: str, filename: str, provider, max_tokens: int = 8000) -> Review:
    """Revisa um trecho de código colado (sem tocar em arquivos no disco)."""
    path = Path(filename or "trecho.txt")
    if not code.strip():
        return Review(path=path, summary="", error="cole algum código para revisar")
    if len(code.encode("utf-8")) > config.MAX_FILE_BYTES:
        return Review(path=path, summary="",
                      error=f"código muito grande (>{config.MAX_FILE_BYTES} bytes)")
    user_msg = prompts.build_user_message(path.name, _language_for(path), code)
    try:
        raw, usage = provider.complete(prompts.SYSTEM_PROMPT, user_msg, max_tokens)
    except ProviderError as exc:
        return Review(path=path, summary="", error=f"erro no provedor: {exc}")
    return _parse_review(path, raw, code, usage)


def ask(question: str, code: str, provider,
        max_tokens: int = 2000) -> tuple[str, Usage, str | None]:
    """Modo 'tirar dúvida': responde uma pergunta livre sobre o código (ou geral)."""
    system = ("Você é um programador sênior didático. Responda de forma clara, "
              "curta e prática, em português. Se houver código, explique com base "
              "nele. Use exemplos curtos só quando ajudarem.")
    content = question if not code.strip() else (
        f"Pergunta: {question}\n\nCódigo de referência:\n```\n{code}\n```")
    try:
        text, usage = provider.complete(system, content, max_tokens)
    except ProviderError as exc:
        return "", Usage(), f"erro no provedor: {exc}"
    return text.strip(), usage, None


def collect_files(target: Path, extensions: set[str]) -> list[Path]:
    """Retorna a lista de arquivos a analisar (um arquivo ou uma pasta inteira)."""
    if target.is_file():
        return [target]
    files: list[Path] = []
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        if any(part in config.IGNORED_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in extensions:
            files.append(p)
    return files
