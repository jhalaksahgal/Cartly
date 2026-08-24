"""Language pack registry.

To add a language: create a module exposing a :class:`Lexicon`, import it here
and append it to ``LEXICONS``. Nothing in the parser needs to change.
"""

from __future__ import annotations

from app.nlp.lexicons.base import Lexicon
from app.nlp.lexicons.en import ENGLISH
from app.nlp.lexicons.es import SPANISH
from app.nlp.lexicons.hi import HINDI
from app.nlp.lexicons.ta import TAMIL

LEXICONS: tuple[Lexicon, ...] = (ENGLISH, HINDI, TAMIL, SPANISH)

DEFAULT_LEXICON: Lexicon = ENGLISH

_BY_CODE: dict[str, Lexicon] = {lexicon.code: lexicon for lexicon in LEXICONS}


def get_lexicon(locale: str | None) -> Lexicon:
    """Resolve a BCP-47 tag (or bare language code) to a language pack.

    Unknown locales fall back to English rather than raising: an unsupported
    speech locale should degrade to best-effort parsing, not an error page.
    """
    if not locale:
        return DEFAULT_LEXICON
    for lexicon in LEXICONS:
        if lexicon.matches_locale(locale):
            return lexicon
    return DEFAULT_LEXICON


def supported_languages() -> list[dict[str, str]]:
    """Language options for the UI picker."""
    return [
        {
            "code": lexicon.code,
            "label": lexicon.label,
            "locale": lexicon.default_locale,
        }
        for lexicon in LEXICONS
    ]


__all__ = [
    "LEXICONS",
    "DEFAULT_LEXICON",
    "Lexicon",
    "get_lexicon",
    "supported_languages",
]
