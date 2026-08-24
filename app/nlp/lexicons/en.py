"""English language pack.

Cues are ordered loosely from most to least specific, but the parser scores by
matched-span length rather than declaration order, so "I want to buy" wins over
the bare "buy" it contains.
"""

from __future__ import annotations

from app.nlp.lexicons.base import Lexicon

_NUMBER_WORDS: dict[str, float] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100,
    "half": 0.5, "quarter": 0.25,
    "couple": 2, "pair": 2, "few": 3, "dozen": 12,
}

_TENS_WORDS: dict[str, float] = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_UNITS: dict[str, str] = {
    # Volume
    "litre": "litre", "litres": "litre", "liter": "litre", "liters": "litre",
    "l": "litre", "ltr": "litre", "ltrs": "litre",
    "ml": "ml", "millilitre": "ml", "millilitres": "ml",
    "milliliter": "ml", "milliliters": "ml",
    "gallon": "gallon", "gallons": "gallon",
    "pint": "pint", "pints": "pint",
    # Weight
    "kg": "kg", "kilo": "kg", "kilos": "kg",
    "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    # Containers and countables
    "bottle": "bottle", "bottles": "bottle",
    "packet": "packet", "packets": "packet",
    "pack": "pack", "packs": "pack",
    "box": "box", "boxes": "box",
    "can": "can", "cans": "can",
    "jar": "jar", "jars": "jar",
    "tin": "tin", "tins": "tin",
    "tube": "tube", "tubes": "tube",
    "bag": "bag", "bags": "bag",
    "carton": "carton", "cartons": "carton",
    "loaf": "loaf", "loaves": "loaf",
    "bunch": "bunch", "bunches": "bunch",
    "dozen": "dozen", "dozens": "dozen",
    "roll": "roll", "rolls": "roll",
    "piece": "piece", "pieces": "piece",
    "slice": "slice", "slices": "slice",
    "punnet": "punnet", "punnets": "punnet",
}

_ATTRIBUTES: dict[str, str] = {
    "organic": "organic",
    "fresh": "fresh",
    "frozen": "frozen",
    "whole": "whole",
    "skimmed": "low-fat", "skim": "low-fat",
    "low-fat": "low-fat", "lowfat": "low-fat", "low fat": "low-fat",
    "fat-free": "fat-free", "fat free": "fat-free",
    "gluten-free": "gluten-free", "gluten free": "gluten-free",
    "sugar-free": "sugar-free", "sugar free": "sugar-free",
    "unsweetened": "unsweetened",
    "greek": "greek",
    "wholemeal": "whole-grain", "wholegrain": "whole-grain",
    "whole-grain": "whole-grain", "whole grain": "whole-grain",
    "brown": "brown",
    "white": "white",
    "dark": "dark",
    "diet": "diet",
    "sparkling": "sparkling",
    "extra-virgin": "extra-virgin", "extra virgin": "extra-virgin",
    "free-range": "free-range", "free range": "free-range",
    "vegan": "vegan",
    "herbal": "herbal",
    "salted": "salted",
    "unsalted": "unsalted",
    "ripe": "fresh",
}

_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "some", "any", "of", "my", "our", "your", "please",
    "to", "from", "on", "off", "out", "in", "into", "for", "onto", "at", "and",
    "list", "lists", "cart", "basket", "shopping", "grocery", "groceries",
    "item", "items", "thing", "things", "me", "i", "we", "it", "that",
    "this", "these", "those", "get", "got", "also", "too", "up",
    "more", "another", "with", "want", "need", "like", "would", "can",
    "could", "let", "us", "there", "is", "are", "am", "be",
    "show", "give", "bring", "actually", "instead", "just", "oh", "well", "so", "now", "then",
})

ENGLISH = Lexicon(
    code="en",
    label="English",
    locales=("en-US", "en-GB", "en-IN", "en-AU", "en-CA"),
    default_locale="en-US",
    add_cues=(
        r"i\s+would\s+like\s+to\s+(?:buy|get|order|purchase)",
        r"i\s+want\s+to\s+(?:buy|get|order|purchase)",
        r"i\s+would\s+like",
        r"i\s+have\s+to\s+(?:buy|get)",
        r"i\s+need\s+to\s+(?:buy|get)",
        r"we\s+need",
        r"i\s+need",
        r"i\s+want",
        r"put",
        r"add",
        r"buy",
        r"order",
        r"purchase",
        r"pick\s+up",
        r"grab",
        r"get",
        r"include",
        r"append",
        r"throw\s+in",
        r"do\s+not\s+forget",
    ),
    remove_cues=(
        r"take\s+(?:off|out)",
        r"take",
        r"(?:off|out\s+of)\s+(?:my|the)\s+(?:shopping\s+|grocery\s+)?(?:list|cart|basket)",
        r"do\s+not\s+need",
        r"remove",
        r"delete",
        r"drop",
        r"get\s+rid\s+of",
        r"take\s+away",
        r"cancel",
        r"erase",
        r"scratch",
    ),
    update_cues=(
        r"change",
        r"update",
        r"modify",
        r"replace",
        r"swap",
        r"make\s+(?:it|that)",
        r"set",
        r"switch",
    ),
    complete_cues=(
        r"mark\s+(?:off)?",
        r"check\s+off",
        r"tick\s+off",
        r"i\s+(?:have\s+)?(?:got|bought|picked\s+up)",
        r"done\s+with",
    ),
    search_cues=(
        r"search\s+for",
        r"look\s+for",
        r"find\s+me",
        r"show\s+me",
        r"do\s+you\s+have",
        r"is\s+there",
        r"how\s+much\s+(?:is|are|does)",
        r"what\s+is\s+the\s+price\s+of",
        r"find",
        r"search",
        r"browse",
    ),
    show_cues=(
        r"(?:show|read|tell|view|display)\s+(?:me\s+)?(?:my\s+)?(?:shopping\s+|grocery\s+)?"
        r"(?:list|cart|basket)",
        r"what\s+(?:is|are|'s)?\s+(?:on|in|inside)\s+(?:my\s+)?(?:the\s+)?(?:shopping\s+)?(?:list|cart|basket)",
        r"whats\s+(?:on|in|inside)\s+(?:my\s+)?(?:the\s+)?(?:shopping\s+)?(?:list|cart|basket)",
        r"what\s+do\s+i\s+(?:have|need)",
        r"open\s+(?:my\s+)?(?:shopping\s+)?list",
        # Anchored: a bare "my list" is a SHOW, but the same words inside
        # "add milk to my list" must not outrank the ADD cue.
        r"^my\s+(?:shopping\s+)?list$",
    ),
    clear_cues=(
        r"clear\s+(?:my\s+|the\s+)?(?:whole\s+|entire\s+)?"
        r"(?:shopping\s+|grocery\s+)?(?:list|cart|basket|everything)",
        r"empty\s+(?:my\s+|the\s+)?(?:shopping\s+)?(?:list|cart|basket)",
        r"delete\s+(?:my\s+|the\s+)?(?:whole\s+|entire\s+)?"
        r"(?:shopping\s+)?(?:list|cart)",
        r"remove\s+everything",
        r"start\s+(?:over|again|fresh)",
        r"wipe\s+(?:my\s+|the\s+)?(?:list|cart)",
    ),
    confirm_words=frozenset({
        "confirm", "yes", "yeah", "yep", "yup", "sure", "ok", "okay",
        "go ahead", "do it", "affirmative", "correct",
    }),
    cancel_words=frozenset({
        "cancel", "no", "nope", "stop", "nevermind", "never mind",
        "abort", "undo", "forget it",
    }),
    number_words=_NUMBER_WORDS,
    tens_words=_TENS_WORDS,
    half_cues=("and a half", "and half"),
    units=_UNITS,
    dozen_words=frozenset({"dozen", "dozens"}),
    max_price_cues=(
        r"under", r"below", r"less\s+than", r"cheaper\s+than",
        r"at\s+most", r"no\s+more\s+than", r"up\s+to", r"within",
        r"not\s+more\s+than", r"maximum", r"max",
    ),
    min_price_cues=(
        r"over", r"above", r"more\s+than", r"at\s+least",
        r"greater\s+than", r"starting\s+(?:at|from)", r"minimum", r"min",
    ),
    range_cues=(r"between", r"from"),
    range_join=("and", "to", "-"),
    currency_words=("dollars", "dollar", "bucks", "buck", "usd", "cents"),
    attributes=_ATTRIBUTES,
    stopwords=_STOPWORDS,
    replacement_cues=(r"to", r"into", r"with", r"for", r"instead\s+of"),
    examples=(
        "I need 2 litres of milk",
        "Add 2 bottles of water",
        "Remove milk from my list",
        "Find organic apples",
        "Find toothpaste under $5",
        "Change milk to almond milk",
    ),
)
