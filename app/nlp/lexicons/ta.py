"""Tamil language pack.

Tamil shares Hindi's two structural challenges and adds a third:

* **Verb-final.** "பால் சேர்" is literally *milk add*. Cues are matched
  anywhere and removed, so word order needs no special handling.
* **Postpositional price cues.** "5 டாலருக்கு கீழ்" is *5 to-dollars below*,
  hence ``price_cue_position="both"``.
* **Agglutination.** Tamil fuses case markers onto the noun, so "dollar"
  appears as டாலருக்கு ("to the dollar") rather than as a separate token.
  Both the bare and the case-marked forms are registered as currency words so
  the amount pattern consumes them and leaves the comparative behind.

Tamil vowel signs and the pulli are combining marks (Unicode Mc/Mn), which is
exactly what the category-based normalizer preserves and a ``\\w`` class would
have destroyed.

**Romanized Tamil is supported alongside the script.** A great many Tamil
speakers type "ennaku oru muttai vendum" rather than switching keyboards, and
an app that only accepts Tamil script rejects most of what they actually write.
Romanized forms live in the same dictionaries as their Tamil-script
equivalents, so the parser needs no special case. Transliteration is not
standardised, so the common spelling variants are simply listed.

Because romanized Tamil is Latin script, no script test can identify it:
:func:`app.nlp.parser.parse` finds it by trying this pack when the selected
language yields nothing.
"""

from __future__ import annotations

from app.nlp.lexicons.base import Lexicon

_NUMBER_WORDS: dict[str, float] = {
    "பூஜ்யம்": 0,
    "ஒன்று": 1, "ஒரு": 1, "ஓர்": 1,
    "இரண்டு": 2, "இரு": 2,
    "மூன்று": 3, "மூணு": 3,
    "நான்கு": 4, "நாலு": 4,
    "ஐந்து": 5, "அஞ்சு": 5,
    "ஆறு": 6, "ஏழு": 7, "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10,
    "பதினொன்று": 11, "பன்னிரண்டு": 12, "பன்னிரெண்டு": 12,
    "பதிமூன்று": 13, "பதினான்கு": 14, "பதினைந்து": 15,
    "இருபது": 20, "முப்பது": 30, "நாற்பது": 40, "ஐம்பது": 50,
    "நூறு": 100,
    "அரை": 0.5, "கால்": 0.25, "முக்கால்": 0.75,
    "ஒன்றரை": 1.5, "இரண்டரை": 2.5,
    "டஜன்": 12,
    # Romanized. Several spellings per numeral, because transliteration is not
    # standardised and speech-to-text output varies.
    "onnu": 1, "ondru": 1, "oru": 1,
    "rendu": 2, "irandu": 2, "irendu": 2,
    "moonu": 3, "moondru": 3, "muunu": 3,
    "naalu": 4, "nangu": 4, "naangu": 4,
    "anju": 5, "ainthu": 5, "ainju": 5,
    "aaru": 6, "ezhu": 7, "elu": 7, "ettu": 8,
    "onbathu": 9, "onbadhu": 9,
    "pathu": 10, "paththu": 10, "pannirendu": 12,
    "irubathu": 20, "muppathu": 30,
    "arai": 0.5, "kaal": 0.25,
    "dozen": 12,
}

_UNITS: dict[str, str] = {
    "லிட்டர்": "litre", "லிட்டர்கள்": "litre", "லிட்டருக்கு": "litre",
    "மில்லி": "ml", "மில்லிலிட்டர்": "ml",
    "கிலோ": "kg", "கிலோகிராம்": "kg", "கிலோவுக்கு": "kg",
    "கிராம்": "g",
    "பாட்டில்": "bottle", "பாட்டில்கள்": "bottle", "புட்டி": "bottle",
    "பாக்கெட்": "packet", "பாக்கெட்டுகள்": "packet",
    "பொட்டலம்": "packet",
    "டப்பா": "box", "பெட்டி": "box", "பாக்ஸ்": "box",
    "கேன்": "can", "டின்": "tin",
    "பை": "bag", "கவர்": "bag",
    "டஜன்": "dozen",
    "துண்டு": "piece", "துண்டுகள்": "piece",
    "கட்டு": "bunch", "கொத்து": "bunch",
    # Romanized, plus the English unit words Tamil speakers routinely mix in.
    "litre": "litre", "litres": "litre", "liter": "litre", "liters": "litre",
    "kilo": "kg", "kilos": "kg", "kg": "kg",
    "gram": "g", "grams": "g", "ml": "ml",
    "bottle": "bottle", "bottles": "bottle",
    "packet": "packet", "packets": "packet", "pack": "pack",
    "dabba": "box", "box": "box", "petti": "box",
    "can": "can", "tin": "tin",
    "pai": "bag", "bag": "bag", "kavar": "bag",
    "thundu": "piece", "piece": "piece",
    "kattu": "bunch", "koththu": "bunch",
}

_ATTRIBUTES: dict[str, str] = {
    "ஆர்கானிக்": "organic", "இயற்கை": "organic", "ஆர்கானிக்கான": "organic",
    "புதிய": "fresh", "ஃப்ரெஷ்": "fresh", "பிரெஷ்": "fresh",
    "உறைந்த": "frozen", "ஃப்ரோஸன்": "frozen",
    "முழு": "whole", "முழுமையான": "whole",
    "வெள்ளை": "white", "பழுப்பு": "brown", "கருப்பு": "dark",
    "சிவப்பு": "red",
    "பச்சை": "green",
    # Romanized
    "organic": "organic", "iyarkai": "organic",
    "puthiya": "fresh", "fresh": "fresh",
    "frozen": "frozen", "muzhu": "whole", "whole": "whole",
    "vellai": "white", "pazhuppu": "brown",
}

_ITEM_ALIASES: dict[str, str] = {
    # Everyday grocery vocabulary, mapped to the catalog's English terms.
    "பால்": "milk", "பாதாம் பால்": "almond milk", "சோயா பால்": "soy milk",
    "தயிர்": "yogurt", "மோர்": "buttermilk", "வெண்ணெய்": "butter",
    "நெய்": "butter", "பாலாடைக்கட்டி": "cheese", "சீஸ்": "cheese",
    "முட்டை": "eggs", "முட்டைகள்": "eggs",
    "ரொட்டி": "bread", "பிரெட்": "bread", "பாண்": "bread",
    "அரிசி": "rice", "மாவு": "flour", "கோதுமை": "wheat",
    "சர்க்கரை": "sugar", "உப்பு": "salt", "மிளகு": "pepper",
    "எண்ணெய்": "oil", "ஆலிவ் எண்ணெய்": "olive oil",
    "தேநீர்": "tea", "டீ": "tea", "காபி": "coffee", "கோப்பி": "coffee",
    "தண்ணீர்": "water", "தண்ணி": "water", "ஜூஸ்": "juice",
    "ஆப்பிள்": "apple", "வாழைப்பழம்": "banana", "வாழை": "banana",
    "ஆரஞ்சு": "orange", "எலுமிச்சை": "lemon", "மாம்பழம்": "mango",
    "திராட்சை": "grapes", "தர்பூசணி": "watermelon",
    "ஸ்ட்ராபெரி": "strawberries", "பழம்": "fruit",
    "தக்காளி": "tomatoes", "உருளைக்கிழங்கு": "potatoes",
    "வெங்காயம்": "onions", "பூண்டு": "garlic", "இஞ்சி": "ginger",
    "கேரட்": "carrots", "கீரை": "spinach", "வெள்ளரி": "cucumber",
    "முட்டைக்கோஸ்": "cabbage", "காளான்": "mushroom",
    "பட்டாணி": "peas", "பருப்பு": "lentils", "கடலை": "chickpeas",
    "காய்கறி": "vegetable",
    "கோழி": "chicken", "சிக்கன்": "chicken", "மட்டன்": "lamb",
    "மீன்": "fish", "இறால்": "shrimp", "இறைச்சி": "meat",
    "பாஸ்தா": "pasta", "நூடுல்ஸ்": "noodles", "ஓட்ஸ்": "oats",
    "தேன்": "honey", "ஜாம்": "jam", "சாக்லேட்": "chocolate",
    "பிஸ்கட்": "crackers", "சிப்ஸ்": "chips", "ஐஸ்கிரீம்": "ice cream",
    "பற்பசை": "toothpaste", "பல் துலக்கி": "toothbrush",
    "ஷாம்பு": "shampoo", "சோப்பு": "soap", "சவர்க்காரம்": "soap",
    "டிடர்ஜென்ட்": "detergent",
    "டாய்லெட் பேப்பர்": "toilet paper", "டிஷ்யூ": "tissue",
    "டயப்பர்": "diapers",
    # Romanized. These are the words that actually get typed.
    "paal": "milk", "pal": "milk", "paalu": "milk",
    "badam paal": "almond milk", "almond paal": "almond milk",
    "thayir": "yogurt", "thair": "yogurt", "mor": "buttermilk",
    "vennai": "butter", "nei": "butter", "ghee": "butter",
    "cheese": "cheese", "paneer": "cheese",
    "muttai": "eggs", "mutai": "eggs", "muttaigal": "eggs",
    "rotti": "bread", "roti": "bread", "bread": "bread",
    "arisi": "rice", "rice": "rice",
    "maavu": "flour", "kothumai": "wheat", "godhumai": "wheat",
    "sakkarai": "sugar", "sarkarai": "sugar", "sugar": "sugar",
    "uppu": "salt", "milagu": "pepper",
    "ennai": "oil", "oil": "oil",
    "kaapi": "coffee", "kapi": "coffee", "coffee": "coffee",
    "theneer": "tea", "tea": "tea",
    "thanni": "water", "thanneer": "water", "tanni": "water",
    "water": "water", "juice": "juice",
    "apple": "apple", "aappil": "apple",
    "vazhaipazham": "banana", "vazhai": "banana", "banana": "banana",
    "orange": "orange",
    "elumichai": "lemon", "elumichampazham": "lemon",
    "maampazham": "mango", "maanga": "mango", "mango": "mango",
    "thiratchai": "grapes", "grapes": "grapes",
    "pazham": "fruit", "pazhangal": "fruit",
    "thakkali": "tomatoes", "takkali": "tomatoes", "tomato": "tomatoes",
    "urulaikizhangu": "potatoes", "urulai": "potatoes", "potato": "potatoes",
    "vengayam": "onions", "onion": "onions",
    "poondu": "garlic", "garlic": "garlic", "inji": "ginger",
    "carrot": "carrots", "keerai": "spinach", "vellarikkai": "cucumber",
    "kaai": "vegetable", "kaaikari": "vegetable",
    "pattani": "peas", "paruppu": "lentils", "kadalai": "chickpeas",
    "kozhi": "chicken", "chicken": "chicken", "mutton": "lamb",
    "meen": "fish", "fish": "fish", "iraal": "shrimp",
    "pasta": "pasta", "oats": "oats", "then": "honey",
    "chocolate": "chocolate", "biscuit": "crackers", "chips": "chips",
    "parpasai": "toothpaste", "pal podi": "toothpaste",
    "pal paste": "toothpaste", "toothpaste": "toothpaste",
    "shampoo": "shampoo", "soap": "soap", "soappu": "soap",
    "savukaram": "soap", "detergent": "detergent",
}

_STOPWORDS: frozenset[str] = frozenset({
    "என்", "எனக்கு", "எங்கள்", "எங்களுக்கு", "நான்", "நாங்கள்",
    "இந்த", "அந்த", "இது", "அது", "இதை", "அதை",
    "இல்", "இல்லிருந்து", "இருந்து", "ல்", "க்கு", "ஐ", "ஆக",
    "பட்டியல்", "பட்டியலில்", "பட்டியலிலிருந்து", "பட்டியலை",
    "லிஸ்ட்", "லிஸ்ட்டில்", "கார்ட்",
    "தயவுசெய்து", "ப்ளீஸ்", "கொஞ்சம்", "சிறிது",
    "செய்", "செய்யவும்", "பண்ணு", "பண்ணவும்", "வும்",
    "மற்றும்", "உள்ளது", "இருக்கு",
    # Romanized
    "ennaku", "enakku", "enaku", "engaluku", "engalukku",
    "naan", "naanga", "en", "enga", "namma",
    "indha", "andha", "idhu", "adhu", "ithu", "athu",
    "la", "le", "il", "irundhu", "irunthu", "kku", "ku",
    "pattiyal", "pattiyalil", "list", "listla", "listil",
    "please", "konjam", "kudunga",
    "pannu", "pannunga", "sollunga",
})

TAMIL = Lexicon(
    code="ta",
    label="தமிழ் (Tamil)",
    locales=("ta-IN", "ta-LK", "ta-SG"),
    default_locale="ta-IN",
    add_cues=(
        r"வாங்க\s*(?:வேண்டும்|ணும்)",
        r"சேர்க்க\s*(?:வும்|ணும்)?",
        r"சேர்த்து", r"சேர்", r"சேர்ப்பு",
        r"போட\s*(?:வும்|ு)?", r"போடு", r"போட்டு",
        r"வாங்க\s*(?:வும்|ு)?", r"வாங்கு",
        r"வேண்டும்", r"வேணும்", r"தேவை",
        r"ஆட்\s*(?:பண்ணு|செய்)",
        r"இணை\s*(?:க்க|வும்)?",
        # Romanized. "vendum"/"venum" (want) is the workhorse; it must not
        # collide with "vendaam"/"venaam" (don't want), which is a removal.
        r"vendum", r"venum", r"vanum", r"vendhum",
        r"serkka(?:vum)?", r"sernthu", r"ser", r"sera",
        r"podu", r"poda", r"podunga", r"pottu",
        r"vaangu", r"vaanga", r"vaangunga", r"vangu",
        r"thevai",
        r"add\s*(?:pannu|pannunga)?",
    ),
    remove_cues=(
        r"நீக்க\s*(?:வும்|ு)?", r"நீக்கு",
        r"எடுத்து\s*விடு", r"எடு\s*(?:க்கவும்)?",
        r"அகற்ற\s*(?:வும்|ு)?", r"அகற்று",
        r"வேண்டாம்", r"வேணாம்",
        r"ரிமூவ்\s*(?:பண்ணு)?", r"டெலீட்\s*(?:பண்ணு)?",
        # Romanized
        r"vendaam", r"venaam", r"vendam", r"vena",
        r"neeku(?:nga)?", r"neekku(?:nga)?", r"neeki",
        r"eduthu(?:\s*vidu)?", r"edu(?:nga)?",
        r"remove\s*(?:pannu|pannunga)?",
        r"delete\s*(?:pannu|pannunga)?",
    ),
    update_cues=(
        r"மாற்ற\s*(?:வும்|ு)?", r"மாற்று", r"மாற்றி", r"மாத்து",
        r"அப்டேட்\s*(?:பண்ணு)?",
        # Romanized
        r"maathu(?:nga)?", r"maatru", r"maathi", r"mathu",
        r"change\s*(?:pannu|pannunga)?",
    ),
    complete_cues=(
        r"வாங்கி\s*விட்டேன்", r"வாங்கிட்டேன்",
        r"கிடைத்து\s*விட்டது", r"முடிந்தது",
    ),
    search_cues=(
        r"தேட\s*(?:வும்|ு)?", r"தேடு",
        r"கண்டுபிடி\s*(?:க்கவும்)?",
        r"தேடிப்பார்",
        r"சர்ச்\s*(?:பண்ணு)?",
        r"விலை\s+என்ன",
        r"எவ்வளவு\s+விலை",
        # Romanized
        r"thedu(?:nga)?", r"thedi(?:\s*paaru)?", r"theda",
        r"kandupidi(?:nga|kka)?",
        r"search\s*(?:pannu|pannunga)?",
        r"vilai\s+enna", r"evvalavu\s+vilai",
    ),
    show_cues=(
        r"(?:பட்டியல்|பட்டியலை|லிஸ்ட்)\s+காட்ட\s*(?:வும்|ு)?",
        r"(?:பட்டியல்|பட்டியலை|லிஸ்ட்)\s+காட்டு",
        r"காட்டு\s+(?:என்\s+)?(?:பட்டியல்|லிஸ்ட்)",
        r"என்ன\s+வாங்க\s+வேண்டும்",
        r"^என்\s+(?:பட்டியல்|லிஸ்ட்)$",
        # Romanized
        r"(?:list|pattiyal)\s+(?:kaattu|kaatu|kaaminga|kaattunga)",
        r"(?:kaattu|kaatu|kaattunga)\s+(?:en\s+)?(?:list|pattiyal)",
        r"enna\s+vaanga\s+vendum",
        r"^en\s+(?:list|pattiyal)$",
    ),
    clear_cues=(
        r"(?:பட்டியல்|பட்டியலை|லிஸ்ட்)\s+(?:அழி|காலி\s+செய்)\s*(?:வும்|ு)?",
        r"(?:பட்டியலை|லிஸ்ட்டை)\s+காலி\s*(?:செய்|பண்ணு)?",
        r"எல்லாம்\s+(?:நீக்கு|அழி)\s*(?:வும்|ு)?",
        r"எல்லாவற்றையும்\s+நீக்கு",
        r"கிளியர்\s*(?:பண்ணு|செய்)?",
        # Romanized
        r"(?:list|pattiyal)\s+(?:azhi|azhinga|kaali\s*pannu|clear\s*pannu)",
        r"ellam\s+(?:neeku|neekku|azhi)(?:nga)?",
        r"ellathaiyum\s+neekku",
        r"clear\s*(?:pannu|pannunga)?",
    ),
    confirm_words=frozenset({
        "ஆம்", "ஆமாம்", "சரி", "ஓகே", "நிச்சயம்", "செய்",
        "confirm", "yes", "ok",
        "aamaam", "aama", "sari", "seri", "okay",
    }),
    cancel_words=frozenset({
        "இல்லை", "வேண்டாம்", "வேணாம்", "நிறுத்து", "ரத்து", "விடு",
        "cancel", "no", "stop",
        "illai", "illa", "vendaam", "venaam", "nirutthu",
    }),
    number_words=_NUMBER_WORDS,
    tens_words={"இருபது": 20, "முப்பது": 30, "நாற்பது": 40, "ஐம்பது": 50},
    units=_UNITS,
    dozen_words=frozenset({"டஜன்"}),
    price_cue_position="both",
    max_price_cues=(
        r"கீழ்", r"கீழே", r"குறைவாக", r"குறைவான", r"வரை",
        r"விட\s+குறைவு", r"மலிவான",
        r"under", r"below",
        r"keezh", r"keezhe", r"kammi(?:yaana|ya)?", r"varai",
        r"kuraivaana", r"kuraiva",
    ),
    min_price_cues=(
        r"மேல்", r"மேலே", r"அதிகமாக", r"அதிகமான",
        r"விட\s+அதிகம்",
        r"over", r"above",
        r"mela", r"mele", r"adhigamaana", r"adhigama",
    ),
    range_cues=(r"இடையே", r"இடையில்", r"between"),
    range_join=("மற்றும்", "முதல்", "to", "and"),
    # Tamil fuses case markers onto nouns, so the dative form of "dollar" is a
    # single token. Both forms are listed so the amount pattern absorbs them.
    currency_words=(
        "டாலருக்கு", "டாலர்", "டாலர்கள்",
        "ரூபாய்க்கு", "ரூபாய்", "ரூபாய்கள்",
        "dollars", "rupees",
        "dollar", "dollarukku", "rubaai", "rubaaikku", "rupaai",
    ),
    attributes=_ATTRIBUTES,
    item_aliases=_ITEM_ALIASES,
    stopwords=_STOPWORDS,
    replacement_cues=(r"பதிலாக", r"ஆக", r"க்கு", r"என"),
    examples=(
        "எனக்கு இரண்டு லிட்டர் பால் வேண்டும்",
        "ஐந்து ஆப்பிள் சேர்",
        "பட்டியலிலிருந்து பால் நீக்கு",
        "ஆர்கானிக் ஆப்பிள் தேடு",
        "பற்பசை 5 டாலருக்கு கீழ் தேடு",
        "பட்டியல் காட்டு",
        "ennaku oru muttai vendum",
        "rendu litre paal vendum",
        "list la irundhu paal neekku",
    ),
)
