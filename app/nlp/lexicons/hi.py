"""Hindi language pack.

Two structural differences from English drive the design here:

* Hindi is verb-final, so the intent cue usually arrives at the *end* of the
  utterance ("दूध डालो" = milk add). The parser matches cues anywhere and
  removes the matched span, so word order needs no special handling.
* Price comparatives are postpositional: "5 डॉलर से कम" is literally
  "5 dollars from less". Hence ``price_cue_position="both"``.

Attribute surface forms map onto the same canonical English tags used by the
catalog, so a Hindi utterance filters an English-tagged product list.
"""

from __future__ import annotations

from app.nlp.lexicons.base import Lexicon

_NUMBER_WORDS: dict[str, float] = {
    "शून्य": 0,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4,
    "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "छे": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15,
    "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19, "बीस": 20,
    "तीस": 30, "चालीस": 40, "पचास": 50, "सौ": 100,
    "आधा": 0.5, "आधी": 0.5, "डेढ़": 1.5, "डेढ": 1.5,
    "ढाई": 2.5, "पौना": 0.75,
    "दर्जन": 12,
}

_UNITS: dict[str, str] = {
    "लीटर": "litre", "लिटर": "litre",
    "मिलीलीटर": "ml", "मिली": "ml",
    "किलो": "kg", "किलोग्राम": "kg", "किग्रा": "kg",
    "ग्राम": "g",
    "बोतल": "bottle", "बोतलें": "bottle", "बोतलों": "bottle",
    "पैकेट": "packet", "पैक": "pack",
    "डिब्बा": "box", "डिब्बे": "box", "डब्बा": "box",
    "कैन": "can", "टिन": "tin",
    "थैला": "bag", "थैली": "bag",
    "दर्जन": "dozen",
    "टुकड़ा": "piece", "टुकड़े": "piece",
    "गुच्छा": "bunch",
}

_ATTRIBUTES: dict[str, str] = {
    "ऑर्गेनिक": "organic", "जैविक": "organic", "आर्गेनिक": "organic",
    "ताजा": "fresh", "ताज़ा": "fresh",
    "जमा": "frozen", "फ्रोजन": "frozen",
    "मलाई": "whole", "फुल": "whole",
    "टोंड": "low-fat", "कम": "low-fat",
    "साबुत": "whole-grain", "आटा": "whole-grain",
    "भूरा": "brown", "सफेद": "white", "सफ़ेद": "white",
    "मीठा": "sweet",
    "बिना": "sugar-free",
}

_ITEM_ALIASES: dict[str, str] = {
    # Everyday grocery vocabulary, mapped to the catalog's English terms.
    "दूध": "milk", "बादाम दूध": "almond milk", "सोया दूध": "soy milk",
    "दही": "yogurt", "पनीर": "cheese", "मक्खन": "butter", "अंडा": "eggs",
    "अंडे": "eggs", "ब्रेड": "bread", "रोटी": "bread", "डबलरोटी": "bread",
    "चावल": "rice", "आटा": "flour", "मैदा": "flour", "चीनी": "sugar",
    "नमक": "salt", "तेल": "oil", "जैतून तेल": "olive oil", "घी": "butter",
    "चाय": "tea", "कॉफी": "coffee", "कॉफ़ी": "coffee", "पानी": "water",
    "जूस": "juice", "रस": "juice",
    "सेब": "apple", "केला": "banana", "केले": "banana", "संतरा": "orange",
    "संतरे": "orange", "आम": "mango", "अंगूर": "grapes", "नींबू": "lemon",
    "स्ट्रॉबेरी": "strawberries", "तरबूज": "watermelon", "नाशपाती": "pear",
    "टमाटर": "tomatoes", "आलू": "potatoes", "प्याज": "onions",
    "लहसुन": "garlic", "गाजर": "carrots", "पालक": "spinach",
    "खीरा": "cucumber", "सलाद": "lettuce", "कद्दू": "pumpkin",
    "मटर": "peas", "दाल": "lentils", "छोले": "chickpeas", "राजमा": "beans",
    "चिकन": "chicken", "मुर्गा": "chicken", "मछली": "fish", "मांस": "meat",
    "पास्ता": "pasta", "नूडल्स": "noodles", "अनाज": "cereal", "ओट्स": "oats",
    "शहद": "honey", "जैम": "jam", "चॉकलेट": "chocolate", "बिस्किट": "crackers",
    "चिप्स": "chips", "आइसक्रीम": "ice cream", "पॉपकॉर्न": "popcorn",
    "टूथपेस्ट": "toothpaste", "टूथब्रश": "toothbrush", "शैम्पू": "shampoo",
    "साबुन": "soap", "कंडीशनर": "conditioner",
    "डिटर्जेंट": "detergent", "सर्फ": "detergent",
    "टॉयलेट पेपर": "toilet paper", "टिशू": "tissue",
    "डायपर": "diapers", "नैपी": "diapers",
}

_STOPWORDS: frozenset[str] = frozenset({
    "से", "को", "में", "पर", "का", "की", "के", "ने", "भी", "और",
    "मेरी", "मेरा", "मेरे", "मुझे", "हमें", "हमारी",
    "है", "हैं", "हूं", "हूँ", "था", "थी", "करो", "कर", "दो", "दें",
    "सूची", "लिस्ट", "फेहरिस्त", "सामान",
    "कृपया", "जरा", "ज़रा", "थोड़ा", "थोड़ी",
    "यह", "वह", "ये", "वे", "कुछ", "एक",
})

HINDI = Lexicon(
    code="hi",
    label="हिन्दी (Hindi)",
    locales=("hi-IN",),
    default_locale="hi-IN",
    add_cues=(
        r"खरीदना\s+है",
        r"लेना\s+है",
        r"चाहिए",
        r"जोड़\s*(?:ो|ें|िए|ना)?",
        r"डाल\s*(?:ो|ें|िए|ना)?",
        r"ऐड\s*(?:करो|करें|कर)?",
        r"शामिल\s+कर\s*(?:ो|ें)?",
        r"खरीद\s*(?:ो|ें|ना)?",
        r"मंगवा\s*(?:ो|ें)?",
        r"लाना",
        r"चाहिये",
    ),
    remove_cues=(
        r"हटा\s*(?:ओ|ो|एं|दो|दीजिए|ना)?",
        r"निकाल\s*(?:ो|ें|िए|ना)?",
        r"मिटा\s*(?:ओ|ो|एं|दो)?",
        r"रिमूव\s*(?:करो|करें)?",
        r"डिलीट\s*(?:करो|करें)?",
        r"नहीं\s+चाहिए",
    ),
    update_cues=(
        r"बदल\s*(?:ो|ें|िए|कर|ना)?",
        r"बदलकर",
        r"अपडेट\s*(?:करो|करें)?",
        r"कर\s+दो",
    ),
    complete_cues=(
        r"खरीद\s+लिया",
        r"ले\s+लिया",
        r"हो\s+गया",
        r"मिल\s+गया",
    ),
    search_cues=(
        r"ढूंढ\s*(?:ो|ें|िए|ना)?",
        r"ढूँढ\s*(?:ो|ें|िए)?",
        r"खोज\s*(?:ो|ें|िए|ना)?",
        r"सर्च\s*(?:करो|करें|कर)?",
        r"तलाश\s+कर\s*(?:ो|ें)?",
        r"दाम\s+(?:क्या|बताओ|बता)",
        r"कीमत\s+(?:क्या|बताओ|बता)",
    ),
    show_cues=(
        r"(?:सूची|लिस्ट)\s+(?:दिखा|बता)\s*(?:ओ|ो|एं|िए)?",
        r"(?:दिखा|बता)\s*(?:ओ|ो|एं|िए)?\s+(?:मेरी\s+)?(?:सूची|लिस्ट)",
        r"क्या\s+क्या\s+चाहिए",
        r"^मेरी\s+(?:सूची|लिस्ट)$",
    ),
    clear_cues=(
        r"(?:सूची|लिस्ट)\s+(?:को\s+)?(?:खाली|साफ)\s+कर\s*(?:ो|ें|िए|दो)?",
        r"(?:सूची|लिस्ट)\s+(?:को\s+)?मिटा\s*(?:ओ|ो|दो|एं)?",
        r"सब\s+(?:कुछ\s+)?(?:हटा|मिटा)\s*(?:ओ|ो|दो|एं)?",
        r"सारा\s+सामान\s+हटा\s*(?:ओ|ो|दो)?",
        r"क्लियर\s*(?:करो|करें)?",
    ),
    confirm_words=frozenset({
        "हाँ", "हां", "जी", "ठीक", "सही", "पक्का", "करो", "बिल्कुल",
        "confirm", "yes", "ok",
    }),
    cancel_words=frozenset({
        "नहीं", "ना", "रुको", "रहने", "छोड़ो", "कैंसिल",
        "cancel", "no", "stop",
    }),
    number_words=_NUMBER_WORDS,
    tens_words={"बीस": 20, "तीस": 30, "चालीस": 40, "पचास": 50},
    units=_UNITS,
    dozen_words=frozenset({"दर्जन"}),
    price_cue_position="both",
    max_price_cues=(
        r"से\s+कम", r"से\s+नीचे", r"से\s+सस्ता", r"तक",
        r"के\s+अंदर", r"से\s+कम\s+कीमत",
        r"under", r"below",
    ),
    min_price_cues=(
        r"से\s+(?:ज्यादा|ज़्यादा|अधिक|ऊपर|महंगा)",
        r"से\s+बड़ा",
        r"over", r"above",
    ),
    range_cues=(r"के\s+बीच", r"between"),
    range_join=("और", "से", "to", "and"),
    currency_words=("डॉलर", "रुपये", "रुपए", "रुपया", "dollars", "rupees"),
    attributes=_ATTRIBUTES,
    item_aliases=_ITEM_ALIASES,
    stopwords=_STOPWORDS,
    replacement_cues=(r"की\s+जगह", r"के\s+बदले", r"में", r"को", r"से"),
    examples=(
        "मुझे दो लीटर दूध चाहिए",
        "पांच सेब जोड़ो",
        "सूची से दूध हटाओ",
        "ऑर्गेनिक सेब ढूंढो",
        "टूथपेस्ट 5 डॉलर से कम ढूंढो",
        "सूची दिखाओ",
    ),
)
