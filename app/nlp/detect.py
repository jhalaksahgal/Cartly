"""Working out which language an utterance is actually in.

The language picker sets the *speech recognition* locale, which is a different
question from what the user just typed or said. Someone can leave the picker on
English and type Tamil; someone can pick Tamil and paste English. Treating the
picker as the final word means answering "I didn't understand that" to a
perfectly clear command, which is the worst possible response.

Two signals, cheapest first:

1. **Script.** Tamil and Devanagari occupy their own Unicode blocks, so a
   non-Latin utterance identifies its language for free.
2. **Cue matching.** Romanized Tamil ("ennaku oru muttai vendum") is in the
   Latin block and cannot be told apart by script, so the parser simply tries
   the other language packs and keeps the best interpretation.
"""

from __future__ import annotations

#: Unicode blocks that identify a language on sight. Only scripts with a
#: language pack are listed; anything else falls through to cue matching.
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0900, 0x097F, "hi"),  # Devanagari
    (0x0B80, 0x0BFF, "ta"),  # Tamil
)

#: Proportion of letters that must belong to one script before we trust it.
#: A single stray character should not redirect an otherwise English command.
_SCRIPT_THRESHOLD = 0.3


def detect_script_language(text: str) -> str | None:
    """Language code implied by ``text``'s script, or None if it is Latin.

    Returns None for Latin-script input rather than guessing "en": romanized
    Tamil is Latin too, and cue matching is the right tool for that.
    """
    if not text:
        return None

    counts: dict[str, int] = {}
    letters = 0
    for char in text:
        if not char.isalpha():
            continue
        letters += 1
        code = ord(char)
        for start, end, language in _SCRIPT_RANGES:
            if start <= code <= end:
                counts[language] = counts.get(language, 0) + 1
                break

    if not letters or not counts:
        return None

    language, count = max(counts.items(), key=lambda pair: pair[1])
    return language if count / letters >= _SCRIPT_THRESHOLD else None
