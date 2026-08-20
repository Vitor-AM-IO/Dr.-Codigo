"""Interface de linha de comando do Code Doctor."""

from __future__ import annotations

import argparse
import difflib
import sys
from datetime import datetime
from pathlib import Path

from . import __version__, analyzer, cache as cache_mod, config, providers

_USE_COLOR = sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


_SEV_COLOR = {"critical": "1;31", "high": "31", "medium": "33", "low": "36"}
_SEV_LABEL = {"critical": "CRÍTICO", "high": "ALTO", "medium": "MÉDIO", "low": "BAIXO"}
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _print_review_human(review: analyzer.Review) -> None:
    tag = _c(" (memória)", "90") if review.from_cache else ""
    header = _c(f"● {review.path}", "1") + tag
    if not review.ok:
        print(f"{header}  {_c('[falhou]', '1;31')} {review.error}")
        return

    if not review.issues:
        print(f"{header}  {_c('✓ nenhum problema encontrado', '32')}")
        if review.summary:
            print(f"    {review.summary}")
        return

    print(f"{header}  {_c(f'{len(review.issues)} problema(s)', '33')}")
    if review.summary:
        print(f"    {review.summary}")
    for issue in sorted(review.issues, key=lambda i: _SEV_ORDER.get(i.severity, 9)):
        color = _SEV_COLOR.get(issue.severity, "0")
        label = _SEV_LABEL.get(issue.severity, issue.severity.upper())
        loc = f"linha {issue.line}" if issue.line else "geral"
        print(f"    {_c(f'[{label}]', color)} ({loc}) {_c(issue.title, '1')}")
        if issue.description:
            print(f"        {issue.description}")
        if issue.suggestion:
            print(f"        {_c('→ correção:', '32')} {issue.suggestion}")


def _print_diff(original: str, corrected: str, path: Path) -> None:
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        corrected.splitlines(keepends=True),
        fromfile=f"{path} (original)",
        tofile=f"{path} (corrigido)",
    )
    printed = False
    for line in diff:
        printed = True
        if line.startswith("+") and not line.startswith("+++"):
            sys.stdout.write(_c(line, "32"))
        elif line.startswith("-") and not line.startswith("---"):
            sys.stdout.write(_c(line, "31"))
        elif line.startswith("@@"):
            sys.stdout.write(_c(line, "36"))
        else:
            sys.stdout.write(line)
    if printed:
        sys.stdout.write("\n")


def _backup(path: Path, original: str) -> Path:
    """Salva o original em .code-doctor/backups/ com data/hora. Automático."""
    backups = cache_mod.state_dir() / "backups"
    backups.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = str(path).replace("/", "_").replace("\\", "_").lstrip("_")
    dest = backups / f"{safe}.{stamp}.bak"
    dest.write_text(original, encoding="utf-8")
    return dest


def _apply_fix(review: analyzer.Review) -> None:
    original = review.path.read_text(encoding="utf-8")
    backup_path = _backup(review.path, original)
    review.path.write_text(review.corrected_code, encoding="utf-8")
    print(f"    {_c('✎ correções aplicadas', '32')} "
          f"{_c(f'(backup: {backup_path})', '90')}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="code-doctor",
        description="Revisor de código com IA (API da Anthropic): aponta falhas, "
                    "sugere e aplica correções — com memória e backup automáticos.",
    )
    p.add_argument("path", nargs="?", help="arquivo ou pasta a analisar")
    p.add_argument("--apply", action="store_true",
                   help="aplica as correções (backup automático em .code-doctor/backups)")
    p.add_argument("--diff", action="store_true",
                   help="mostra o diff das correções propostas")
    p.add_argument("--provider", default=None,
                   help="provedor: anthropic, openai, openrouter, groq, together, "
                        "deepseek, mistral, ollama, lmstudio, custom "
                        "(padrão: anthropic ou CODE_DOCTOR_PROVIDER)")
    p.add_argument("--model", default=None,
                   help=f"modelo a usar (padrão do anthropic: {config.DEFAULT_MODEL})")
    p.add_argument("--ext", default=None,
                   help="extensões extras separadas por vírgula, ex: .toml,.cfg")
    p.add_argument("--no-cache", action="store_true",
                   help="ignora a memória e reanalisa tudo (gasta mais tokens)")
    p.add_argument("--clear-cache", action="store_true",
                   help="apaga a memória de revisões e sai")
    p.add_argument("--fail-on", choices=["critical", "high", "medium", "low"],
                   default=None,
                   help="sai com erro se houver problema neste nível ou pior (CI)")
    p.add_argument("--version", action="version", version=f"code-doctor {__version__}")
    return p


def _worst_severity(reviews: list[analyzer.Review]) -> int:
    worst = 9
    for r in reviews:
        for issue in r.issues:
            worst = min(worst, _SEV_ORDER.get(issue.severity, 9))
    return worst


def _camouflage_cmd(raw: list[str]) -> int:
    """Trata `code-doctor hide/reveal <arquivo>` — camuflagem local, sem API."""
    from . import camouflage
    op = "hide" if raw[0] in ("hide", "camuflar") else "reveal"
    rest = raw[1:]

    style = camouflage.DEFAULT_STYLE
    out_path = None
    positional = []
    i = 0
    while i < len(rest):
        if rest[i] == "--style" and i + 1 < len(rest):
            style = rest[i + 1]; i += 2
        elif rest[i] == "--out" and i + 1 < len(rest):
            out_path = rest[i + 1]; i += 2
        elif rest[i] == "--list-styles":
            print("Estilos:", ", ".join(camouflage.styles())); return 0
        else:
            positional.append(rest[i]); i += 1

    if not positional:
        print(f"[erro] uso: code-doctor {raw[0]} <arquivo> "
              f"[--style {'|'.join(camouflage.styles())}] [--out arquivo]",
              file=sys.stderr)
        return 2

    src = Path(positional[0])
    if not src.exists():
        print(f"[erro] arquivo não encontrado: {src}", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")

    try:
        if op == "hide":
            result = camouflage.hide(text, style)
        else:
            result, detected = camouflage.reveal(text)
    except ValueError as exc:
        print(f"[erro] {exc}", file=sys.stderr)
        return 2

    if out_path:
        Path(out_path).write_text(result, encoding="utf-8")
        extra = f" (idioma: {detected})" if op == "reveal" else f" (idioma: {style})"
        print(_c(f"✓ {'camuflado' if op == 'hide' else 'revelado'} em {out_path}{extra}",
                 "32"))
    else:
        if op == "reveal":
            print(_c(f"(idioma detectado: {detected})\n", "90"))
        sys.stdout.write(result + ("\n" if not result.endswith("\n") else ""))
    return 0


def _install_ollama() -> int:
    """Instala o Ollama (IA local e grátis), detectando o sistema operacional."""
    import platform
    import shutil
    import subprocess
    import webbrowser

    system = platform.system()
    print(_c("Instalar o Ollama — roda uma IA de graça no seu computador.\n", "1"))
    print(f"Sistema detectado: {system}\n")
    try:
        resp = input("Tentar instalar automaticamente agora? [s/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return 0

    if not resp.startswith("s"):
        print("Sem problema — abrindo a página de download oficial…")
        webbrowser.open("https://ollama.com/download")
        return 0

    ok = False
    if system == "Windows":
        if shutil.which("winget"):
            print("\nInstalando via winget… (pode pedir confirmação do Windows)\n")
            r = subprocess.run(["winget", "install", "--id", "Ollama.Ollama",
                                "-e", "--source", "winget"])
            ok = r.returncode == 0
        if not ok:
            print("\nNão deu pelo winget. Abrindo a página de download…")
            webbrowser.open("https://ollama.com/download")
            return 0
    elif system == "Darwin":
        if shutil.which("brew"):
            print("\nInstalando via Homebrew…\n")
            ok = subprocess.run(["brew", "install", "ollama"]).returncode == 0
        if not ok:
            print("\nAbrindo a página de download…")
            webbrowser.open("https://ollama.com/download")
            return 0
    else:  # Linux
        print("\nVou rodar o instalador oficial do Ollama:")
        print("  curl -fsSL https://ollama.com/install.sh | sh\n")
        c = input("Continuar? [s/n]: ").strip().lower()
        if not c.startswith("s"):
            return 0
        ok = subprocess.run("curl -fsSL https://ollama.com/install.sh | sh",
                            shell=True).returncode == 0

    if ok:
        print(_c("\n✓ Ollama instalado (ou já estava).", "32"))
        try:
            m = input("Baixar o modelo llama3.1 agora? [s/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            m = "n"
        if m.startswith("s") and shutil.which("ollama"):
            subprocess.run(["ollama", "pull", "llama3.1"])
        print("\nPronto! Deixe o Ollama aberto e escolha 'Grátis (Ollama)' na interface.")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if raw and raw[0] in ("--about", "about"):
        from . import SIGNATURE
        print(SIGNATURE)
        return 0
    # Instalador do Ollama (IA local e grátis).
    if raw and raw[0] in ("instalar-ollama", "ollama-install", "instalar_ollama"):
        return _install_ollama()

    # Subcomando: `code-doctor web` abre a interface no navegador.
    if raw and raw[0] == "web":
        from . import web
        port = 8765
        if "--port" in raw:
            try:
                port = int(raw[raw.index("--port") + 1])
            except (ValueError, IndexError):
                pass
        no_open = "--no-open" in raw
        # a interface web sobe mesmo sem chave (ela mostra um aviso amigável).
        web.serve(port=port, open_browser=not no_open)
        return 0

    # Subcomandos de camuflagem (local, sem API): esconder e revelar código.
    if raw and raw[0] in ("hide", "reveal", "camuflar", "revelar"):
        return _camouflage_cmd(raw)

    args = build_parser().parse_args(argv)

    if args.clear_cache:
        cache_mod.clear()
        print("Memória de revisões apagada.")
        return 0

    if not args.path:
        print("[erro] informe um arquivo ou pasta. Veja --help.", file=sys.stderr)
        return 2

    target = Path(args.path)
    if not target.exists():
        print(f"[erro] caminho não encontrado: {target}", file=sys.stderr)
        return 2

    extensions = set(config.DEFAULT_EXTENSIONS)
    if args.ext:
        extensions |= {e if e.startswith(".") else f".{e}"
                       for e in args.ext.split(",") if e.strip()}

    files = analyzer.collect_files(target, extensions)
    if not files:
        print("[erro] nenhum arquivo de código encontrado nesse caminho.",
              file=sys.stderr)
        return 2

    config._load_dotenv()  # garante que o .env seja lido antes de montar o provedor
    try:
        provider = providers.get_provider(args.provider, args.model)
    except providers.ProviderError as exc:
        print(f"\n[erro] {exc}\n", file=sys.stderr)
        return 2

    use_cache = not args.no_cache
    cache = cache_mod.load() if use_cache else None

    print(_c(f"Code Doctor — {len(files)} arquivo(s) · {provider.name}/{provider.model}"
             + ("" if use_cache else " · memória desligada") + "\n", "1"))

    reviews: list[analyzer.Review] = []
    total_usage = analyzer.Usage()
    for path in files:
        review = analyzer.analyze_file(path, provider, cache=cache,
                                       use_cache=use_cache)
        reviews.append(review)
        total_usage.add(review.usage)
        _print_review_human(review)

        if review.ok and review.changed and review.corrected_code:
            if args.diff:
                _print_diff(path.read_text(encoding="utf-8"),
                            review.corrected_code, path)
            if args.apply:
                _apply_fix(review)
        print()

    if cache is not None:
        cache_mod.save(cache)

    # ---- Resumo + relatório de economia (números reais da API) ----
    total_issues = sum(len(r.issues) for r in reviews)
    failed = [r for r in reviews if not r.ok]
    from_cache = sum(1 for r in reviews if r.from_cache)
    called = len(files) - from_cache

    print(_c("─" * 52, "90"))
    print(f"Resumo: {total_issues} problema(s) em {len(files)} arquivo(s)"
          + (f", {len(failed)} falha(s)" if failed else ""))
    print(_c(f"Economia: {from_cache} da memória (0 tokens) · "
             f"{called} analisado(s) via API", "90"))
    if called:
        print(_c(f"Tokens: {total_usage.input_tokens} entrada / "
                 f"{total_usage.output_tokens} saída"
                 + (f" · {total_usage.cache_read_tokens} lidos do cache de prompt"
                    if total_usage.cache_read_tokens else ""), "90"))
    if not args.apply and any(r.changed for r in reviews):
        print(_c("Use --diff para ver as mudanças e --apply para aplicá-las.", "90"))

    if args.fail_on and _worst_severity(reviews) <= _SEV_ORDER[args.fail_on]:
        print(_c(f"\n[CI] problemas de nível '{args.fail_on}' ou pior encontrados.",
                 "1;31"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
