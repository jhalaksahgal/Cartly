"""Quantity and unit extraction.

Runs after price extraction so that price numbers are already gone, and before
item extraction so the leftover text is the item name.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.nlp.lexicons.base import WORD_END, WORD_START, Lexicon, alternation
from app.nlp.normalize import remove_span
from app.nlp.numbers import read_number


class Quantity:
    """Result of scanning an utterance for an amount and a unit."""

    __slots__ = ("value", "unit", "text")

    def __init__(
        self,
        text: str,
        value: float | None = None,
        unit: str | None = None,
    ) -> None:
        self.text = text
        self.value = value
        self.unit = unit

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Quantity(value={self.value!r}, unit={self.unit!r}, "
            f"text={self.text!r})"
        )


@lru_cache(maxsize=32)
def _patterns(lexicon: Lexicon) -> dict[str, re.Pattern[str]]:
    numbers = alternation(lexicon.number_words.keys())
    number = rf"(?:\d+(?:\.\d+)?|{numbers})"
    units = alternation(lexicon.units.keys())
    halves = alternation(lexicon.half_cues) if lexicon.half_cues else r"(?!)"
    # "a"/"an"/"una" style articles that imply a count of one. Taken from the
    # number words that equal 1 plus the language's own articles.
    articles = alternation(
        [word for word, value in lexicon.number_words.items() if value == 1]
        + ["a", "an"]
    )

    return {
        # "half a kilo", "half of a kilo", "quarter of a litre"
        "fractional_unit": re.compile(
            rf"{WORD_START}(?P<value>{numbers})\s+(?:of\s+)?(?:a|an)\s+(?P<unit>{units}){WORD_END}"
        ),
        # "2 litres", "two and a half litres", "1.5 kg"
        "number_unit": re.compile(
            rf"{WORD_START}(?P<value>{number})"
            rf"(?:\s+(?P<half>{halves}))?"
            rf"\s*(?P<unit>{units}){WORD_END}"
        ),
        # "a bottle of water"
        "article_unit": re.compile(
            rf"{WORD_START}(?:{articles})\s+(?P<unit>{units}){WORD_END}"
        ),
        # "5 oranges" - a bare count with no unit
        "number_only": re.compile(
            rf"{WORD_START}(?P<value>{number})"
            rf"(?:\s+(?P<half>{halves}))?{WORD_END}"
        ),
        # A packaging word left stranded at the front of the item name, as in
        # "1 litre bottle of milk" once "1 litre" has been consumed.
        "leading_unit": re.compile(rf"^(?:{units})\s+"),
    }


def _resolve(raw_value: str, half: str | None, lexicon: Lexicon) -> float | None:
    value = read_number(raw_value, lexicon)
    if value is None:
        return None
    if half:
        value += 0.5
    return value


def extract_quantity(text: str, lexicon: Lexicon) -> Quantity:
    """Pull an amount and unit out of ``text``, returning the remainder.

    Tried in order of specificity: a number with a unit, then an article with a
    unit, then a bare number. Only the first that matches is consumed.
    """
    patterns = _patterns(lexicon)

    match = patterns["fractional_unit"].search(text)
    if match:
        value = read_number(match.group("value"), lexicon)
        if value is not None:
            unit = lexicon.units.get(match.group("unit"))
            return Quantity(remove_span(text, match.span()), value, unit)

    match = patterns["number_unit"].search(text)
    if match:
        value = _resolve(match.group("value"), match.group("half"), lexicon)
        if value is not None:
            unit = lexicon.units.get(match.group("unit"))
            return Quantity(remove_span(text, match.span()), value, unit)

    match = patterns["article_unit"].search(text)
    if match:
        unit = lexicon.units.get(match.group("unit"))
        return Quantity(remove_span(text, match.span()), 1.0, unit)

    match = patterns["number_only"].search(text)
    if match:
        value = _resolve(match.group("value"), match.group("half"), lexicon)
        if value is not None:
            return Quantity(remove_span(text, match.span()), value, None)

    return Quantity(text)


def strip_leading_unit(text: str, lexicon: Lexicon) -> str:
    """Drop a packaging word stranded at the start of an item name.

    "find a 1 litre bottle of milk" leaves "bottle of milk" once the quantity
    is consumed; the item the user means is "milk".
    """
    return _patterns(lexicon)["leading_unit"].sub("", text, count=1).strip()
