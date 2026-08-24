"""Hindi, Tamil and Spanish command parsing.

These tests exist to keep the multilingual claim honest. The language picker is
not a decoration: each language has its own cue set, numerals, units, price
grammar and grocery vocabulary, and this file exercises all of them.
"""

from __future__ import annotations

import pytest

from app.models import Intent
from app.nlp.lexicons import get_lexicon, supported_languages
from app.nlp.parser import parse

HINDI = "hi-IN"
TAMIL = "ta-IN"
SPANISH = "es-ES"


# --------------------------------------------------------------------------
# Hindi
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "intent", "item"),
    [
        ("दूध डालो", Intent.ADD_ITEM, "दूध"),
        ("मुझे सेब चाहिए", Intent.ADD_ITEM, "सेब"),
        ("ब्रेड जोड़ो", Intent.ADD_ITEM, "ब्रेड"),
        ("सूची से दूध हटाओ", Intent.REMOVE_ITEM, "दूध"),
        ("अंडे निकालो", Intent.REMOVE_ITEM, "अंडे"),
        ("टूथपेस्ट ढूंढो", Intent.SEARCH_PRODUCT, "टूथपेस्ट"),
        ("चावल खोजो", Intent.SEARCH_PRODUCT, "चावल"),
    ],
)
def test_hindi_intents(utterance: str, intent: Intent, item: str) -> None:
    """Hindi is verb-final; the cue arrives last and must still be found."""
    command = parse(utterance, HINDI)
    assert command.intent is intent
    assert command.item == item


@pytest.mark.parametrize(
    ("utterance", "quantity", "unit", "item"),
    [
        ("मुझे दो लीटर दूध चाहिए", 2, "litre", "दूध"),
        ("पांच सेब जोड़ो", 5, None, "सेब"),
        ("2 बोतल पानी जोड़ो", 2, "bottle", "पानी"),
        ("दस अंडे चाहिए", 10, None, "अंडे"),
        ("एक किलो आलू डालो", 1, "kg", "आलू"),
    ],
)
def test_hindi_quantities(
    utterance: str, quantity: float, unit: str | None, item: str
) -> None:
    command = parse(utterance, HINDI)
    assert command.intent is Intent.ADD_ITEM
    assert command.quantity == quantity
    assert command.unit == unit
    assert command.item == item


def test_hindi_devanagari_digits() -> None:
    """Speech engines emit Devanagari numerals for hi-IN."""
    command = parse("५ सेब जोड़ो", HINDI)
    assert command.quantity == 5
    assert command.item == "सेब"


def test_hindi_postpositional_price() -> None:
    """"5 डॉलर से कम" is literally "5 dollars from less" - the cue trails."""
    command = parse("टूथपेस्ट 5 डॉलर से कम ढूंढो", HINDI)
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.max_price == 5
    assert command.item == "टूथपेस्ट"


def test_hindi_minimum_price() -> None:
    command = parse("पनीर 10 डॉलर से ज्यादा ढूंढो", HINDI)
    assert command.min_price == 10


@pytest.mark.parametrize(
    ("utterance", "intent"),
    [
        ("सूची दिखाओ", Intent.SHOW_LIST),
        ("मेरी सूची", Intent.SHOW_LIST),
        ("सूची खाली करो", Intent.CLEAR_LIST),
        ("सब कुछ हटाओ", Intent.CLEAR_LIST),
    ],
)
def test_hindi_list_intents(utterance: str, intent: Intent) -> None:
    assert parse(utterance, HINDI).intent is intent


def test_hindi_attributes_map_to_english_tags() -> None:
    """A Hindi adjective has to filter an English-tagged catalog."""
    command = parse("ऑर्गेनिक सेब ढूंढो", HINDI)
    assert command.attributes == ["organic"]


def test_hindi_item_is_canonicalised_for_lookup() -> None:
    """The user sees their own word; search and categorization see English."""
    command = parse("मुझे दूध चाहिए", HINDI)
    assert command.item == "दूध"
    assert command.canonical_item == "milk"
    assert command.category.value == "Dairy"


def test_hindi_combining_marks_survive_normalization() -> None:
    """Regression: a \\w-based strip would turn "मुझे" into "म झ"."""
    command = parse("मुझे टूथपेस्ट चाहिए", HINDI)
    assert command.item == "टूथपेस्ट"


# --------------------------------------------------------------------------
# Tamil
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "intent", "item"),
    [
        ("பால் சேர்", Intent.ADD_ITEM, "பால்"),
        ("எனக்கு முட்டை வேண்டும்", Intent.ADD_ITEM, "முட்டை"),
        ("ரொட்டி போடு", Intent.ADD_ITEM, "ரொட்டி"),
        ("பட்டியலிலிருந்து பால் நீக்கு", Intent.REMOVE_ITEM, "பால்"),
        ("முட்டை வேண்டாம்", Intent.REMOVE_ITEM, "முட்டை"),
        ("அரிசி தேடு", Intent.SEARCH_PRODUCT, "அரிசி"),
        ("பற்பசை கண்டுபிடி", Intent.SEARCH_PRODUCT, "பற்பசை"),
    ],
)
def test_tamil_intents(utterance: str, intent: Intent, item: str) -> None:
    """Tamil is verb-final; the cue arrives last and must still be found."""
    command = parse(utterance, TAMIL)
    assert command.intent is intent
    assert command.item == item


def test_tamil_add_and_remove_are_distinguished() -> None:
    """வேண்டும் (want) and வேண்டாம் (don't want) differ by one syllable."""
    assert parse("பால் வேண்டும்", TAMIL).intent is Intent.ADD_ITEM
    assert parse("பால் வேண்டாம்", TAMIL).intent is Intent.REMOVE_ITEM


@pytest.mark.parametrize(
    ("utterance", "quantity", "unit", "item"),
    [
        ("எனக்கு இரண்டு லிட்டர் பால் வேண்டும்", 2, "litre", "பால்"),
        ("ஐந்து ஆப்பிள் சேர்", 5, None, "ஆப்பிள்"),
        ("மூன்று பாட்டில் தண்ணீர் சேர்", 3, "bottle", "தண்ணீர்"),
        ("ஒரு கிலோ தக்காளி சேர்", 1, "kg", "தக்காளி"),
        ("பத்து முட்டை வேண்டும்", 10, None, "முட்டை"),
    ],
)
def test_tamil_quantities(
    utterance: str, quantity: float, unit: str | None, item: str
) -> None:
    command = parse(utterance, TAMIL)
    assert command.intent is Intent.ADD_ITEM
    assert command.quantity == quantity
    assert command.unit == unit
    assert command.item == item


def test_tamil_numerals() -> None:
    """Speech engines emit Tamil digits for ta-IN."""
    command = parse("௫ ஆப்பிள் சேர்", TAMIL)
    assert command.quantity == 5
    assert command.item == "ஆப்பிள்"


def test_tamil_agglutinated_postpositional_price() -> None:
    """"5 டாலருக்கு கீழ்" fuses the case marker onto "dollar"."""
    command = parse("பற்பசை 5 டாலருக்கு கீழ் தேடு", TAMIL)
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.max_price == 5
    assert command.item == "பற்பசை"


def test_tamil_minimum_price() -> None:
    command = parse("பாலாடைக்கட்டி 10 டாலருக்கு மேல் தேடு", TAMIL)
    assert command.min_price == 10


@pytest.mark.parametrize(
    ("utterance", "intent"),
    [
        ("பட்டியல் காட்டு", Intent.SHOW_LIST),
        ("என் பட்டியல்", Intent.SHOW_LIST),
        ("பட்டியல் அழி", Intent.CLEAR_LIST),
        ("எல்லாம் நீக்கு", Intent.CLEAR_LIST),
    ],
)
def test_tamil_list_intents(utterance: str, intent: Intent) -> None:
    assert parse(utterance, TAMIL).intent is intent


def test_tamil_attributes_map_to_english_tags() -> None:
    command = parse("ஆர்கானிக் ஆப்பிள் தேடு", TAMIL)
    assert command.attributes == ["organic"]


def test_tamil_item_is_canonicalised_for_lookup() -> None:
    command = parse("எனக்கு பால் வேண்டும்", TAMIL)
    assert command.item == "பால்"
    assert command.canonical_item == "milk"
    assert command.category.value == "Dairy"


def test_tamil_combining_marks_survive_normalization() -> None:
    r"""Tamil vowel signs are Mc/Mn, exactly what a ``\w`` strip would delete."""
    command = parse("உருளைக்கிழங்கு சேர்", TAMIL)
    assert command.item == "உருளைக்கிழங்கு"
    assert command.canonical_item == "potatoes"


@pytest.mark.parametrize("utterance", ["ஆம்", "சரி", "ஓகே"])
def test_tamil_confirm(utterance: str) -> None:
    assert parse(utterance, TAMIL).intent is Intent.CONFIRM


@pytest.mark.parametrize("utterance", ["இல்லை", "நிறுத்து", "ரத்து"])
def test_tamil_cancel(utterance: str) -> None:
    assert parse(utterance, TAMIL).intent is Intent.CANCEL



# --------------------------------------------------------------------------
# Spanish
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "intent", "item"),
    [
        ("Añade leche", Intent.ADD_ITEM, "leche"),
        ("Agrega pan", Intent.ADD_ITEM, "pan"),
        ("Necesito huevos", Intent.ADD_ITEM, "huevos"),
        ("Quiero comprar manzanas", Intent.ADD_ITEM, "manzanas"),
        ("Quita la leche de mi lista", Intent.REMOVE_ITEM, "leche"),
        ("Elimina el pan", Intent.REMOVE_ITEM, "pan"),
        ("Busca arroz", Intent.SEARCH_PRODUCT, "arroz"),
        ("Encuentra queso", Intent.SEARCH_PRODUCT, "queso"),
    ],
)
def test_spanish_intents(utterance: str, intent: Intent, item: str) -> None:
    command = parse(utterance, SPANISH)
    assert command.intent is intent
    assert command.item == item


@pytest.mark.parametrize(
    ("utterance", "quantity", "unit", "item"),
    [
        ("Necesito dos litros de leche", 2, "litre", "leche"),
        ("Añade 5 manzanas", 5, None, "manzanas"),
        ("Compra 2 botellas de agua", 2, "bottle", "agua"),
        ("Agrega tres cajas de cereal", 3, "box", "cereal"),
        ("Añade medio kilo de queso", 0.5, "kg", "queso"),
    ],
)
def test_spanish_quantities(
    utterance: str, quantity: float, unit: str | None, item: str
) -> None:
    command = parse(utterance, SPANISH)
    assert command.intent is Intent.ADD_ITEM
    assert command.quantity == quantity
    assert command.unit == unit
    assert command.item == item


def test_spanish_price_filter() -> None:
    command = parse("Busca pasta de dientes menos de $5", SPANISH)
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.max_price == 5
    assert command.canonical_item == "toothpaste"


def test_spanish_price_range() -> None:
    command = parse("Busca queso entre 3 y 8 dólares", SPANISH)
    assert command.min_price == 3
    assert command.max_price == 8


def test_spanish_replacement() -> None:
    command = parse("Cambia leche por leche de almendras", SPANISH)
    assert command.intent is Intent.UPDATE_ITEM
    assert command.item == "leche"
    assert command.replacement == "leche de almendras"
    assert command.canonical_replacement == "almond milk"


def test_spanish_attributes() -> None:
    command = parse("Busca manzanas orgánicas", SPANISH)
    assert command.attributes == ["organic"]


def test_spanish_works_without_accents() -> None:
    """Dictated and typed text disagree about accents more than about spelling."""
    with_accent = parse("Busca manzanas orgánicas", SPANISH)
    without = parse("Busca manzanas organicas", SPANISH)
    assert with_accent.attributes == without.attributes
    assert with_accent.item == without.item


@pytest.mark.parametrize(
    ("utterance", "intent"),
    [
        ("Muestra mi lista", Intent.SHOW_LIST),
        ("mi lista", Intent.SHOW_LIST),
        ("Vacía mi lista", Intent.CLEAR_LIST),
        ("Borra todo", Intent.CLEAR_LIST),
    ],
)
def test_spanish_list_intents(utterance: str, intent: Intent) -> None:
    assert parse(utterance, SPANISH).intent is intent


# --------------------------------------------------------------------------
# Locale resolution
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("locale", "code"),
    [
        ("en-US", "en"), ("en-GB", "en"), ("en", "en"),
        ("hi-IN", "hi"), ("hi", "hi"),
        ("ta-IN", "ta"), ("ta-LK", "ta"), ("ta", "ta"),
        ("es-ES", "es"), ("es-MX", "es"), ("es", "es"),
    ],
)
def test_locale_resolution(locale: str, code: str) -> None:
    assert get_lexicon(locale).code == code


@pytest.mark.parametrize("locale", ["", None, "fr-FR", "zz", "garbage"])
def test_unknown_locale_falls_back_to_english(locale: str | None) -> None:
    """An unsupported locale degrades to best-effort English, never an error."""
    assert get_lexicon(locale).code == "en"


def test_every_language_advertises_working_examples() -> None:
    """The example chips in the UI must actually parse in their own language."""
    for language in supported_languages():
        lexicon = get_lexicon(language["locale"])
        assert lexicon.examples, f"{language['code']} has no examples"
        for example in lexicon.examples:
            command = parse(example, language["locale"])
            assert command.intent is not Intent.UNKNOWN, (
                f"{language['code']} example did not parse: {example!r}"
            )
