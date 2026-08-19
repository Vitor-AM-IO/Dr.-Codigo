"""Camuflador de código (reversível e divertido).

Transforma qualquer texto/código numa sequência de glifos de outro "idioma"
(runas, katakana, braille ou emoji) e revela de volta o original — sem perda.

Como funciona: o texto vira base64 e cada símbolo do base64 é trocado por um
glifo do alfabeto escolhido. Para revelar, detecta automaticamente o alfabeto
e desfaz a troca.

⚠ Isto é CAMUFLAGEM, não criptografia. Qualquer pessoa com esta ferramenta
reverte o resultado. Serve para disfarçar/brincar, não para proteger segredos.
"""

from __future__ import annotations

import base64
import string

# Alfabeto do base64 padrão (64 símbolos) + o caractere de preenchimento '='.
_SRC = string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/" + "="
assert len(_SRC) == 65


def _alphabet(start: int, n: int = 65) -> list[str]:
    """Gera n glifos consecutivos a partir de um ponto de código Unicode."""
    return [chr(start + i) for i in range(n)]


# Cada "idioma" é um conjunto de 65 glifos distintos, sem sobreposição entre eles.
STYLES: dict[str, list[str]] = {
    "runas":    _alphabet(0x16A0),   # ᚠᚡᚢ… parece escrita rúnica antiga
    "katakana": _alphabet(0x30A1),   # ァアィ… parece japonês
    "braille":  _alphabet(0x2800),   # ⠁⠂⠃… pontinhos secretos
    "emoji":    _alphabet(0x1F600),  # 😀😁😂… carinhas
}

DEFAULT_STYLE = "runas"


def styles() -> list[str]:
    return list(STYLES.keys())


def hide(text: str, style: str = DEFAULT_STYLE) -> str:
    """Camufla o texto no alfabeto escolhido."""
    if style not in STYLES:
        raise ValueError(f"estilo desconhecido: {style}. Opções: {', '.join(styles())}")
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    fwd = {_SRC[i]: STYLES[style][i] for i in range(65)}
    return "".join(fwd[c] for c in b64)


def reveal(camouflaged: str) -> tuple[str, str]:
    """Revela o texto original. Detecta o alfabeto automaticamente.

    Retorna (texto_original, estilo_detectado).
    """
    cleaned = "".join(camouflaged.split())  # ignora espaços/quebras de linha
    if not cleaned:
        raise ValueError("nada para revelar")

    for style, glyphs in STYLES.items():
        rev = {glyphs[i]: _SRC[i] for i in range(65)}
        if all(c in rev for c in cleaned):
            b64 = "".join(rev[c] for c in cleaned)
            try:
                original = base64.b64decode(b64).decode("utf-8")
                return original, style
            except (ValueError, UnicodeDecodeError):
                continue
    raise ValueError("não reconheci esse texto secreto "
                     "(alfabeto inválido ou texto corrompido)")
