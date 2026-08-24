"""Price-constraint extraction.

Runs before quantity extraction, because a price phrase contains a number that
would otherwise be mistaken for a quantity: in "find toothpaste under $5" the
5 belongs to the price, not to the toothpaste.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.nlp.lexicons.base import WORD_END, WORD_START, Lexicon, alternation
from app.nlp.normalize import remove_span
from app.nlp.numbers import read_number


class PriceConstraint:
    """Result of scanning an utterance for price bounds."""

    __slots__ = ("min_price", "max_price", "text")

    def __init__(
        self,
        text: str,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> None:
        self.text = text
        self.min_price = min_price
        self.max_price = max_price

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"PriceConstraint(min={self.min_price!r}, "
            f"max={self.max_price!r}, text={self.text!r})"
        )


@lru_cache(maxsize=32)
def _amount_fragment(lexicon: Lexicon) -> str:
    """Regex for one money amount: optional symbol, number, optional currency."""
    numbers = alternation(lexicon.number_words.keys())
    currency = alternation(lexicon.currency_words) if lexicon.currency_words else r"(?!)"
    return (
        r"(?:\$\s*)?"
        rf"(?:\d+(?:\.\d+)?|{numbers})"
        rf"(?:\s*(?:{currency}))?"
    )


@lru_cache(maxsize=32)
def _compiled(lexicon: Lexicon) -> dict[str, list[re.Pattern[str]]]:
    """Build every price pattern for a language, once."""
    amount = _amount_fragment(lexicon)
    joins = alternation(lexicon.range_join)

    def prefix(cues: tuple[str, ...]) -> list[re.Pattern[str]]:
        return [
            re.compile(rf"{WORD_START}(?:{cue})\s+(?P<amount>{amount}){WORD_END}")
            for cue in cues
        ]

    def postfix(cues: tuple[str, ...]) -> list[re.Pattern[str]]:
        return [
            re.compile(rf"{WORD_START}(?P<amount>{amount})\s+(?:{cue}){WORD_END}")
            for cue in cues
        ]

    position = lexicon.price_cue_position
    max_patterns: list[re.Pattern[str]] = []
    min_patterns: list[re.Pattern[str]] = []
    if position in ("prefix", "both"):
        max_patterns += prefix(lexicon.max_price_cues)
        min_patterns += prefix(lexicon.min_price_cues)
    if position in ("postfix", "both"):
        max_patterns += postfix(lexicon.max_price_cues)
        min_patterns += postfix(lexicon.min_price_cues)

    range_patterns = [
        re.compile(
            rf"{WORD_START}(?:{cue})\s+(?P<low>{amount})\s+(?:{joins})\s+"
            rf"(?P<high>{amount}){WORD_END}"
        )
        for cue in lexicon.range_cues
    ]
    # Hindi wraps the range: "5 और 15 डॉलर के बीच".
    if position in ("postfix", "both"):
        range_patterns += [
            re.compile(
                rf"{WORD_START}(?P<low>{amount})\s+(?:{joins})\s+"
                rf"(?P<high>{amount})\s+(?:{cue}){WORD_END}"
            )
            for cue in lexicon.range_cues
        ]

    return {"range": range_patterns, "max": max_patterns, "min": min_patterns}


@lru_cache(maxsize=32)
def _amount_cleaner(lexicon: Lexicon) -> re.Pattern[str]:
    """Strips the currency symbol and currency word off a captured amount."""
    currency = alternation(lexicon.currency_words) if lexicon.currency_words else r"(?!)"
    return re.compile(rf"\$|\s*(?:{currency})\s*$")


def _to_amount(raw: str, lexicon: Lexicon) -> float | None:
    cleaned = _amount_cleaner(lexicon).sub(" ", raw).strip()
    return read_number(cleaned, lexicon)


def extract_price(text: str, lexicon: Lexicon) -> PriceConstraint:
    """Pull price bounds out of ``text`` and return them with the text removed.

    A range wins over a bare bound, so "between $5 and $15" is not misread as
    a minimum of 5 by a stray "from" cue.
    """
    patterns = _compiled(lexicon)

    for pattern in patterns["range"]:
        match = pattern.search(text)
        if not match:
            continue
        low = _to_amount(match.group("low"), lexicon)
        high = _to_amount(match.group("high"), lexicon)
        if low is None or high is None:
            continue
        if low > high:
            low, high = high, low
        return PriceConstraint(remove_span(text, match.span()), low, high)

    min_price: float | None = None
    max_price: float | None = None

    for key, patterns_for_key in (("max", patterns["max"]), ("min", patterns["min"])):
        for pattern in patterns_for_key:
            match = pattern.search(text)
            if not match:
                continue
            amount = _to_amount(match.group("amount"), lexicon)
            if amount is None:
                continue
            if key == "max":
                max_price = amount
            else:
                min_price = amount
            text = remove_span(text, match.span())
            break

    return PriceConstraint(text, min_price, max_price)
