"""Numeral reading: digits and spelled-out numbers, in any supported language.

Kept separate from quantity and price extraction because both need it and
neither should own it.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.nlp.lexicons.base import WORD_END, WORD_START, Lexicon, alternation

_DIGITS = re.compile(r"^\d+(?:\.\d+)?$")


@lru_cache(maxsize=32)
def number_pattern(lexicon: Lexicon) -> str:
    """Regex fragment matching one number, written in digits or in words."""
    words = alternation(lexicon.number_words.keys())
    return rf"(?:\d+(?:\.\d+)?|{words})"


@lru_cache(maxsize=32)
def _compound_pattern(lexicon: Lexicon) -> re.Pattern[str] | None:
    """Matches "twenty five"-style compounds, if the language has any."""
    if not lexicon.tens_words:
        return None
    tens = alternation(lexicon.tens_words.keys())
    ones = alternation(
        word for word, value in lexicon.number_words.items()
        if 1 <= value <= 9 and float(value).is_integer()
    )
    return re.compile(rf"{WORD_START}({tens})\s+({ones}){WORD_END}")


def parse_number(token: str, lexicon: Lexicon) -> float | None:
    """Read a single numeric token, or return None if it is not a number."""
    token = token.strip()
    if not token:
        return None
    if _DIGITS.match(token):
        try:
            return float(token)
        except ValueError:  # pragma: no cover - guarded by the regex
            return None
    return lexicon.number_words.get(token)


def read_number(text: str, lexicon: Lexicon) -> float | None:
    """Read a number from a short phrase such as "twenty five" or "1.5"."""
    text = text.strip()
    if not text:
        return None

    compound = _compound_pattern(lexicon)
    if compound is not None:
        match = compound.fullmatch(text)
        if match:
            return lexicon.tens_words[match.group(1)] + (
                lexicon.number_words[match.group(2)]
            )
    return parse_number(text, lexicon)


def collapse_compounds(text: str, lexicon: Lexicon) -> str:
    """Rewrite spelled compounds as digits so downstream patterns stay simple.

    "add twenty five apples" becomes "add 25 apples".
    """
    compound = _compound_pattern(lexicon)
    if compound is None:
        return text

    def _replace(match: re.Match[str]) -> str:
        total = lexicon.tens_words[match.group(1)] + (
            lexicon.number_words[match.group(2)]
        )
        return f"{total:g}"

    return compound.sub(_replace, text)
