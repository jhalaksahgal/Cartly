"""Language detection.

The picker sets the speech-recognition locale, which is a different question
from what the user actually typed or said. These tests cover both directions:
an utterance in the wrong-language pack must still be understood, and an
ordinary English command must never be relabelled as something else.

Both cases here were reported from real use: Tamil script typed with the picker
left on English, and romanized Tamil ("ennaku oru muttai vendum"), which no
script test can identify.
"""

from __future__ import annotations

import pytest

from app.models import Intent
from app.nlp.detect import detect_script_language
from app.nlp.parser import parse


# --------------------------------------------------------------------------
# Script detection
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("எனக்கு ஒரு முட்டை வேண்டும்", "ta"),
        ("பால் சேர்", "ta"),
        ("मुझे दो लीटर दूध चाहिए", "hi"),
        ("दूध डालो", "hi"),
    ],
)
def test_script_identifies_indic_languages(text: str, expected: str) -> None:
    assert detect_script_language(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "add milk",
        "ennaku oru muttai vendum",  # romanized Tamil is Latin script
        "Añade 5 manzanas",
        "",
        "12345",
        "$5",
    ],
)
def test_latin_script_is_not_guessed(text: str) -> None:
    """Returning None is correct: cue matching handles Latin-script input."""
    assert detect_script_language(text) is None


def test_a_stray_indic_character_does_not_flip_the_language() -> None:
    """One character out of a long English sentence is below the threshold."""
    assert detect_script_language("add milk and bread and eggs ब") is None


# --------------------------------------------------------------------------
# Wrong-language script, right result
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "intent", "item", "locale"),
    [
        ("எனக்கு ஒரு முட்டை வேண்டும்.", Intent.ADD_ITEM, "முட்டை", "ta-IN"),
        ("பட்டியலிலிருந்து பால் நீக்கு", Intent.REMOVE_ITEM, "பால்", "ta-IN"),
        ("मुझे दो लीटर दूध चाहिए", Intent.ADD_ITEM, "दूध", "hi-IN"),
        ("Añade 5 manzanas", Intent.ADD_ITEM, "manzanas", "es-ES"),
    ],
)
def test_understood_despite_the_wrong_picker(
    utterance: str, intent: Intent, item: str, locale: str
) -> None:
    """Reported bug: Tamil typed with the picker on English said "didn't
    understand" instead of noticing the script."""
    command = parse(utterance, "en-US")
    assert command.intent is intent
    assert command.item == item
    assert command.detected_language == locale


def test_detected_language_is_none_when_the_picker_was_right() -> None:
    command = parse("எனக்கு ஒரு முட்டை வேண்டும்", "ta-IN")
    assert command.intent is Intent.ADD_ITEM
    assert command.detected_language is None


# --------------------------------------------------------------------------
# Romanized Tamil ("Tanglish")
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "intent", "canonical"),
    [
        ("ennaku oru muttai vendum", Intent.ADD_ITEM, "eggs"),
        ("rendu litre paal vendum", Intent.ADD_ITEM, "milk"),
        ("paal vendaam", Intent.REMOVE_ITEM, "milk"),
        ("list la irundhu paal neekku", Intent.REMOVE_ITEM, "milk"),
        ("thakkali thedu", Intent.SEARCH_PRODUCT, "tomatoes"),
        ("moonu bottle thanni podu", Intent.ADD_ITEM, "water"),
        ("anju apple ser", Intent.ADD_ITEM, "apple"),
    ],
)
def test_romanized_tamil(utterance: str, intent: Intent, canonical: str) -> None:
    """Latin script, so only cue matching can find it."""
    command = parse(utterance, "en-US")
    assert command.intent is intent
    assert command.canonical_item == canonical
    assert command.detected_language == "ta-IN"


def test_romanized_tamil_quantities_and_units() -> None:
    command = parse("rendu litre paal vendum", "en-US")
    assert command.quantity == 2
    assert command.unit == "litre"


def test_romanized_tamil_postpositional_price() -> None:
    command = parse("parpasai 5 dollarukku keezh thedu", "en-US")
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.canonical_item == "toothpaste"
    assert command.max_price == 5


@pytest.mark.parametrize(
    ("utterance", "intent"),
    [
        ("list kaattu", Intent.SHOW_LIST),
        ("ellam neekku", Intent.CLEAR_LIST),
    ],
)
def test_romanized_tamil_list_intents(utterance: str, intent: Intent) -> None:
    assert parse(utterance, "en-US").intent is intent


def test_vendum_and_vendaam_are_opposites() -> None:
    """One syllable apart, and they mean add versus remove."""
    assert parse("paal vendum", "ta-IN").intent is Intent.ADD_ITEM
    assert parse("paal vendaam", "ta-IN").intent is Intent.REMOVE_ITEM


# --------------------------------------------------------------------------
# English must never be relabelled
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "utterance",
    [
        "add milk",
        "milk",
        "almond milk",
        "organic milk",
        "whole wheat bread",
        "chocolate",
        "bread",
        "Find toothpaste under $5",
        "remove milk from my list",
        "clear my list",
        "we're out of eggs",
        "Add 2 bottles of water",
        "Change milk to almond milk",
    ],
)
def test_english_is_never_relabelled(utterance: str) -> None:
    """Every pack reads a bare "milk" the same way.

    Another language has to be strictly *more* confident to take over, so a
    tie leaves the selected language in place.
    """
    command = parse(utterance, "en-US")
    assert command.detected_language is None
    assert command.intent is not Intent.UNKNOWN


def test_genuine_nonsense_is_still_unknown() -> None:
    """Trying four packs must not turn gibberish into a false positive."""
    for utterance in ["asdfgh qwerty zxcvb", "the fridge is empty again", "zzz"]:
        command = parse(utterance, "en-US")
        assert command.intent is Intent.UNKNOWN
        assert command.detected_language is None
