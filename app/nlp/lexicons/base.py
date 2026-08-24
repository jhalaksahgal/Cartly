"""The shape of a language pack.

Adding a language means adding one module that builds a :class:`Lexicon` and
registering it - no changes to the parser itself. That separation is what makes
the multilingual claim real rather than a dropdown that only swaps the speech
recogniser's locale.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field


#: Token boundaries expressed as whitespace lookaround. ``\b`` is defined in
#: terms of ``\w``, which excludes Devanagari combining marks, so it fires in
#: the middle of Hindi words. These behave identically for Latin scripts and
#: correctly for Indic ones.
WORD_START = r"(?:(?<=^)|(?<=\s))"
WORD_END = r"(?=\s|$)"


# eq=False keeps the identity-based __hash__ from object. A generated __eq__
# would hash the dict fields and fail, and these packs are module-level
# singletons, so identity is exactly the right comparison.
@dataclass(frozen=True, eq=False)
class Lexicon:
    """Everything the parser needs to know about one language.

    Intent cues are regex fragments matched anywhere in the normalized
    utterance. Matching anywhere (rather than anchoring at the start) is what
    lets the same pipeline handle subject-verb-object languages like English
    and Spanish alongside subject-object-verb languages like Hindi, where the
    verb arrives last: "दूध डालो" and "add milk" both reduce to the cue plus
    the payload "milk".
    """

    code: str
    label: str
    #: BCP-47 tags this pack should be used for, e.g. ("en-US", "en-GB").
    locales: tuple[str, ...]
    #: Speech-recognition locale offered in the UI language picker.
    default_locale: str

    add_cues: tuple[str, ...] = ()
    remove_cues: tuple[str, ...] = ()
    update_cues: tuple[str, ...] = ()
    complete_cues: tuple[str, ...] = ()
    search_cues: tuple[str, ...] = ()
    show_cues: tuple[str, ...] = ()
    clear_cues: tuple[str, ...] = ()

    confirm_words: frozenset[str] = frozenset()
    cancel_words: frozenset[str] = frozenset()

    #: Spelled-out numerals, e.g. {"five": 5}.
    number_words: dict[str, float] = field(default_factory=dict)
    #: Tens that combine with a following unit word ("twenty five" -> 25).
    tens_words: dict[str, float] = field(default_factory=dict)
    #: Literal phrase meaning "+0.5", e.g. "and a half". These are surface
    #: forms, not regex fragments - normalization guarantees single spaces.
    half_cues: tuple[str, ...] = ()

    #: Surface form -> canonical unit, e.g. {"litres": "litre", "l": "litre"}.
    units: dict[str, str] = field(default_factory=dict)
    #: Units that also imply a count of twelve ("a dozen eggs").
    dozen_words: frozenset[str] = frozenset()

    #: Where a price cue sits relative to its number. English puts it before
    #: ("under $5"); Hindi puts it after ("5 डॉलर से कम"). "both" tries either.
    price_cue_position: str = "prefix"
    #: Regex fragments introducing an upper price bound ("under", "below").
    max_price_cues: tuple[str, ...] = ()
    #: Regex fragments introducing a lower price bound ("over", "above").
    min_price_cues: tuple[str, ...] = ()
    #: Regex fragment introducing a range ("between").
    range_cues: tuple[str, ...] = ()
    #: Word joining the two ends of a range ("and", "y", "से").
    range_join: tuple[str, ...] = ("and",)
    #: Spoken currency names, stripped after a price is read.
    currency_words: tuple[str, ...] = ()

    #: Surface adjective -> canonical English tag, so a Hindi or Spanish
    #: utterance can filter an English-tagged catalog.
    attributes: dict[str, str] = field(default_factory=dict)

    #: Common grocery nouns mapped to their English catalog term, so a Hindi
    #: or Spanish utterance can search an English catalog. The user's own
    #: wording is still what gets displayed; this only drives lookup.
    item_aliases: dict[str, str] = field(default_factory=dict)

    #: Tokens trimmed from the edges of an extracted item name.
    stopwords: frozenset[str] = frozenset()
    #: Words separating an update's target from its replacement ("to").
    replacement_cues: tuple[str, ...] = ()

    #: Shown in the UI as tappable example commands.
    examples: tuple[str, ...] = ()

    def matches_locale(self, locale: str) -> bool:
        """True when ``locale`` (a BCP-47 tag) belongs to this pack."""
        if not locale:
            return False
        lowered = locale.lower()
        if lowered in {tag.lower() for tag in self.locales}:
            return True
        return lowered.split("-")[0] == self.code


def compile_cues(cues: tuple[str, ...]) -> list[re.Pattern[str]]:
    """Compile intent cue fragments into whole-token-aware patterns."""
    return [
        re.compile(rf"{WORD_START}(?:{cue}){WORD_END}") for cue in cues
    ]


def alternation(surfaces: Iterable[str]) -> str:
    """Build a regex alternation from surface forms, longest first.

    Longest-first ordering matters because Python's ``|`` is first-match, not
    longest-match: without it "litre" would win over "litres" and leave a
    stray "s" behind.
    """
    escaped = sorted({str(item) for item in surfaces}, key=len, reverse=True)
    return "|".join(re.escape(surface) for surface in escaped) or r"(?!)"
