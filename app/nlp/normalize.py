"""Text normalization shared by every language.

Speech recognition output is messy in predictable ways: inconsistent casing,
stray punctuation, smart quotes, spelled-out currency, and (for Hindi) digits
in Devanagari. Normalizing all of that once, up front, keeps the intent and
entity patterns simple and readable.
"""

from __future__ import annotations

import re
import unicodedata

#: Digits that speech engines emit for non-Latin locales, mapped to ASCII.
_NON_ASCII_DIGITS = {
    # Devanagari (Hindi)
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
    # Tamil
    "௦": "0", "௧": "1", "௨": "2", "௩": "3", "௪": "4",
    "௫": "5", "௬": "6", "௭": "7", "௮": "8", "௯": "9",
    # Arabic-Indic
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}

#: Currency symbols are normalized to a single marker so one price pattern
#: covers every locale the app supports.
CURRENCY_MARKER = "$"
_CURRENCY_SYMBOLS = ("$", "₹", "€", "£", "¥")

_CONTRACTIONS = {
    "i'd": "i would",
    "i'm": "i am",
    "i've": "i have",
    "i'll": "i will",
    "we're": "we are",
    "we've": "we have",
    "we'll": "we will",
    "you're": "you are",
    "they're": "they are",
    "it's": "it is",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "can't": "can not",
    "won't": "will not",
    "let's": "let us",
    "that's": "that is",
    "what's": "what is",
    "whats": "what is",
    "there's": "there is",
    "theres": "there is",
    "how's": "how is",
    "hows": "how is",
}

_SMART_QUOTES = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
    "—": "-",
})

# Decimal points, hyphens (low-fat, gluten-free), slashes and the currency
# marker carry meaning; everything else punctuation-happy speech engines emit
# is noise.
_KEEP_PUNCT = frozenset({".", "-", "/", "%", CURRENCY_MARKER})

_MULTI_SPACE = re.compile(r"\s+")
# A period only survives if it sits between two digits (1.5 litres).
_TRAILING_DOTS = re.compile(r"(?<!\d)\.|\.(?!\d)")


def _strip_punctuation(text: str) -> str:
    """Replace punctuation and symbols with spaces, preserving all letters.

    This deliberately works on Unicode *categories* rather than a ``\\w``
    character class. Python's ``\\w`` excludes combining marks (categories Mn
    and Mc), which would quietly mangle Devanagari - "मुझे" becomes "म झ" -
    and break Hindi parsing while leaving English untouched.
    """
    out: list[str] = []
    for char in text:
        if char.isspace() or char in _KEEP_PUNCT:
            out.append(char)
            continue
        category = unicodedata.category(char)
        # L* letters, M* combining marks and N* numbers are content; P*
        # punctuation, S* symbols and C* control characters are not.
        out.append(" " if category[0] in ("P", "S", "C") else char)
    return "".join(out)


def _fold_digits(text: str) -> str:
    return "".join(_NON_ASCII_DIGITS.get(char, char) for char in text)


def _fold_currency(text: str) -> str:
    for symbol in _CURRENCY_SYMBOLS:
        text = text.replace(symbol, f" {CURRENCY_MARKER} ")
    return text


def _expand_contractions(text: str) -> str:
    for contraction, expansion in _CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(contraction)}\b", expansion, text)
    return text


def normalize(text: str) -> str:
    """Return a canonical lowercase form of ``text`` for pattern matching.

    The result keeps word order and the currency marker intact, so spans found
    in the normalized string can still be removed positionally when the parser
    peels entities off the utterance.
    """
    if not text:
        return ""

    # NFKC folds full-width and compatibility characters onto their plain
    # equivalents without stripping Devanagari or accented Latin letters.
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_SMART_QUOTES)
    text = text.lower()
    text = _expand_contractions(text)
    text = _fold_digits(text)
    text = _fold_currency(text)
    text = _strip_punctuation(text)
    text = _TRAILING_DOTS.sub(" ", text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


def strip_words(text: str, words: frozenset[str]) -> str:
    """Drop every token in ``words`` from ``text``, preserving order."""
    kept = [token for token in text.split() if token not in words]
    return " ".join(kept)


def trim_edges(text: str, words: frozenset[str]) -> str:
    """Trim tokens in ``words`` from both ends of ``text``.

    Used for item names: "of milk from my list" should become "milk", but an
    interior stopword in a real product name ("bottle of water" as a literal
    product) must survive, so only the edges are trimmed.
    """
    tokens = text.split()
    while tokens and tokens[0] in words:
        tokens.pop(0)
    while tokens and tokens[-1] in words:
        tokens.pop()
    return " ".join(tokens)


def remove_span(text: str, span: tuple[int, int]) -> str:
    """Cut ``span`` out of ``text`` and tidy the resulting whitespace."""
    start, end = span
    return _MULTI_SPACE.sub(" ", text[:start] + " " + text[end:]).strip()


def singularize(word: str) -> str:
    """Crude English singularizer, used only for catalog/category lookup.

    Display names always keep the user's original wording; this exists so that
    "apples" and "apple" resolve to the same catalog entry.
    """
    if len(word) <= 3:
        return word
    for suffix, replacement in (("ies", "y"), ("ches", "ch"), ("shes", "sh"),
                                ("sses", "ss"), ("oes", "o")):
        if word.endswith(suffix):
            return word[: -len(suffix)] + replacement
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def singularize_phrase(phrase: str) -> str:
    """Singularize every token of ``phrase``."""
    return " ".join(singularize(token) for token in phrase.split())
