"""Map an item name onto the catalog's vocabulary.

The catalog is authored in English. Rather than translating the catalog into
every supported language - which would be a much larger data problem - each
language pack carries a small dictionary of common grocery nouns.

The user's own wording is always what gets displayed. This only produces the
term used for catalog lookup and categorization, so a Hindi speaker sees
"दूध × 2 L" on their list while search and categorization still work.

Coverage is deliberately limited to everyday grocery vocabulary. Items outside
it fall through unchanged, which degrades to "no catalog match" rather than to
an error.
"""

from __future__ import annotations

from app.nlp.lexicons import Lexicon
from app.nlp.normalize import singularize_phrase


def canonicalize(item: str | None, lexicon: Lexicon) -> str | None:
    """Return the English catalog term for ``item``, or ``item`` unchanged.

    Tries the whole phrase first so multi-word entries ("pasta de dientes" ->
    "toothpaste") beat a token-by-token rendering, then falls back to mapping
    each token individually.
    """
    if not item:
        return item
    if not lexicon.item_aliases:
        return item

    needle = item.strip().lower()
    aliases = lexicon.item_aliases

    direct = aliases.get(needle) or aliases.get(singularize_phrase(needle))
    if direct:
        return direct

    tokens = needle.split()
    if len(tokens) < 2:
        return item

    mapped = [
        aliases.get(token) or aliases.get(singularize_phrase(token)) or token
        for token in tokens
    ]
    if mapped == tokens:
        return item
    return " ".join(mapped)
