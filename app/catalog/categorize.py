"""Automatic categorization of free-text item names.

Two passes, cheapest first:

1. Keyword dictionary - explicit, reviewable, and covers items that are not in
   the catalog at all ("nappies" is Baby even if we stock no nappies).
2. Catalog lookup - anything the catalog knows about inherits its category.

Anything unmatched falls back to ``Category.OTHER``. This is deliberately not a
machine-learning problem: a dictionary is faster, debuggable, and correct for
the long tail of a grocery list.
"""

from __future__ import annotations

from functools import lru_cache

from app.catalog.data import all_products
from app.models import Category
from app.nlp.normalize import singularize_phrase

#: Keyword -> category. Keys are matched against singularized item tokens, so
#: "apples" and "apple" both hit the "apple" key.
_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.PRODUCE: (
        "apple", "banana", "orange", "mandarin", "clementine", "pear", "peach",
        "plum", "grape", "strawberry", "blueberry", "raspberry", "blackberry",
        "berry", "melon", "watermelon", "mango", "pineapple", "kiwi", "lemon",
        "lime", "avocado", "tomato", "potato", "onion", "garlic", "carrot",
        "lettuce", "spinach", "kale", "cabbage", "broccoli", "cauliflower",
        "cucumber", "pepper", "capsicum", "celery", "mushroom", "courgette",
        "zucchini", "aubergine", "eggplant", "pumpkin", "squash", "ginger",
        "chilli", "chili", "herb", "coriander", "parsley", "basil", "salad",
        "fruit", "vegetable", "veg", "produce", "greens", "sprout", "leek",
        "beetroot", "radish", "corn", "peas fresh",
    ),
    Category.DAIRY: (
        # Plant milks live in the dairy aisle; without these, "almond milk"
        # would match the "almond" nut keyword and land in Pantry.
        "almond milk", "cashew milk", "rice milk", "plant milk",
        "milk", "cheese", "cheddar", "mozzarella", "parmesan", "feta", "brie",
        "yogurt", "yoghurt", "butter", "margarine", "cream", "creme",
        "egg", "custard", "ghee", "curd", "paneer", "buttermilk", "kefir",
    ),
    Category.BAKERY: (
        "garlic bread",
        "bread", "loaf", "bun", "roll", "bagel", "baguette", "croissant",
        "muffin", "pastry", "cake", "tortilla", "pita", "naan", "brioche",
        "sourdough", "doughnut", "donut", "scone", "crumpet",
    ),
    Category.MEAT_SEAFOOD: (
        "chicken", "beef", "pork", "lamb", "turkey", "duck", "mince",
        "steak", "bacon", "sausage", "ham", "salami", "meat", "fish",
        "salmon", "tuna", "cod", "haddock", "prawn", "shrimp", "crab",
        "lobster", "seafood", "fillet", "wing", "thigh", "drumstick",
    ),
    Category.PANTRY: (
        # Beat "tomato" (Produce) and "chicken"/"beef" (Meat).
        "tomato sauce", "tomato paste", "canned tomatoes",
        "chopped tomatoes", "chicken stock", "beef stock",
        "vegetable stock",
        "pasta", "spaghetti", "penne", "fusilli", "noodle", "rice", "quinoa",
        "couscous", "flour", "sugar", "salt", "pepper", "spice", "cinnamon",
        "cumin", "turmeric", "paprika", "oil", "olive oil", "vinegar",
        "sauce", "ketchup", "mayonnaise", "mayo", "mustard", "soy sauce",
        "honey", "jam", "preserve", "peanut butter", "nutella", "cereal",
        "oat", "granola", "muesli", "bean", "lentil", "chickpea", "pulse",
        "tin", "can", "canned", "stock", "broth", "gravy", "baking",
        "yeast", "syrup", "tofu", "seed", "nut", "almond", "walnut",
        "cashew", "raisin", "date", "pesto", "curry paste",
    ),
    Category.FROZEN: (
        "frozen", "ice cream", "icecream", "sorbet", "gelato", "lolly",
        "pizza", "lasagne", "lasagna", "ready meal", "chips frozen",
        "fish finger", "waffle",
    ),
    Category.BEVERAGES: (
        # Beat the fruit and "greens" keywords in Produce.
        "apple juice", "orange juice", "fruit juice", "green tea",
        "black tea", "herbal tea", "iced tea", "coffee beans",
        "ground coffee", "instant coffee",
        "water", "juice", "soda", "cola", "coke", "pepsi", "lemonade",
        "drink", "beverage", "coffee", "tea", "beer", "wine", "cider",
        "smoothie", "squash", "kombucha", "energy drink", "milkshake",
    ),
    Category.SNACKS: (
        # Beat "potato" (Produce) and "tortilla" (Bakery).
        "potato chips", "corn chips", "tortilla chips", "veggie chips",
        "potato crisps",
        "chip", "crisp", "cracker", "biscuit", "cookie", "pretzel",
        "popcorn", "chocolate", "candy", "sweet", "snack", "bar",
        "granola bar", "nuts", "trail mix", "dip", "salsa", "hummus",
        "guacamole", "wafer", "gum",
    ),
    Category.PERSONAL_CARE: (
        "toothpaste", "toothbrush", "mouthwash", "floss", "shampoo",
        "conditioner", "soap", "body wash", "shower gel", "deodorant",
        "antiperspirant", "razor", "shaving", "lotion", "moisturiser",
        "moisturizer", "sunscreen", "cotton", "tissue facial", "makeup",
        "perfume", "sanitary", "tampon", "pad", "vitamin", "medicine",
        "painkiller", "plaster", "bandage",
    ),
    Category.HOUSEHOLD: (
        "detergent", "washing powder", "fabric softener", "bleach",
        "dish soap", "washing up", "dishwasher", "sponge", "scourer",
        "cleaner", "disinfectant", "toilet paper", "kitchen roll",
        "paper towel", "bin bag", "bin liner", "trash bag", "foil",
        "cling film", "plastic wrap", "battery", "bulb", "candle",
        "matches", "sanitiser", "sanitizer", "air freshener", "mop",
        "broom", "duster",
    ),
    Category.BABY: (
        "nappy", "diaper", "baby wipe", "formula", "baby food", "dummy",
        "pacifier", "baby", "infant", "toddler",
    ),
}


@lru_cache(maxsize=1)
def _keyword_index() -> list[tuple[str, Category]]:
    """Keyword phrases sorted longest-first so "peanut butter" beats "butter"."""
    pairs: list[tuple[str, Category]] = []
    for category, keywords in _KEYWORDS.items():
        for keyword in keywords:
            pairs.append((singularize_phrase(keyword), category))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return pairs


@lru_cache(maxsize=1)
def _catalog_index() -> list[tuple[str, Category]]:
    """Catalog names and tags, longest-first, as a secondary category source."""
    pairs: list[tuple[str, Category]] = []
    for product in all_products():
        pairs.append((singularize_phrase(product.name.lower()), product.category))
        for tag in product.tags:
            pairs.append((singularize_phrase(tag.lower()), product.category))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return pairs


@lru_cache(maxsize=512)
def categorize(item: str) -> Category:
    """Best-guess category for a free-text item name.

    Matching is phrase-aware: the needle must appear as a whole word or words
    inside the item, so "chip" matches "potato chips" but not "chipotle".
    """
    if not item or not item.strip():
        return Category.OTHER

    haystack = f" {singularize_phrase(item.lower().strip())} "

    for needle, category in _keyword_index():
        if f" {needle} " in haystack:
            return category

    for needle, category in _catalog_index():
        if needle and (f" {needle} " in haystack or haystack.strip() in needle):
            return category

    return Category.OTHER
