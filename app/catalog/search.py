"""Catalog search: keyword relevance plus brand, price, category and
attribute filters.

Scoring is a small weighted sum rather than anything statistical. With a
catalog this size that is both sufficient and explainable - every result can be
justified by pointing at the terms that matched.
"""

from __future__ import annotations

from app.catalog.categorize import categorize
from app.catalog.data import all_products, alternatives_for
from app.models import Category, Product, SearchHit, SearchQuery, SearchResponse
from app.nlp.normalize import normalize, singularize_phrase

# Relevance weights, highest signal first.
_EXACT_NAME = 12.0
_NAME_PHRASE = 8.0
_TAG_EXACT = 6.0
_NAME_TOKEN = 3.0
_TAG_TOKEN = 2.0
_BRAND_TOKEN = 2.0
_CATEGORY_TOKEN = 1.0
#: Awarded when the query's own inferred category matches the product's. This
#: is what keeps "find milk" from returning Milk Chocolate Bar first: both
#: contain the word "milk", but only one of them is Dairy.
_CATEGORY_AFFINITY = 3.0
_IN_STOCK_BONUS = 0.5


def _tokens(text: str) -> list[str]:
    return [token for token in singularize_phrase(normalize(text)).split() if token]


def _score(
    product: Product,
    terms: list[str],
    phrase: str,
    query_category: Category | None = None,
) -> float:
    """Relevance of one product against the query terms. 0 means no match."""
    name = singularize_phrase(product.name.lower())
    tags = {singularize_phrase(tag.lower()) for tag in product.tags}
    brand = (product.brand or "").lower()
    category = product.category.value.lower()

    score = 0.0
    if phrase:
        if name == phrase:
            score += _EXACT_NAME
        # Whole-word containment, not raw substring: "ham" must not match
        # "c-ham-omile".
        elif f" {phrase} " in f" {name} ":
            score += _NAME_PHRASE
        if phrase in tags:
            score += _TAG_EXACT

    name_tokens = set(name.split())
    brand_tokens = set(brand.split())
    category_tokens = set(category.split())
    tag_tokens = {token for tag in tags for token in tag.split()}

    for term in terms:
        if term in name_tokens:
            score += _NAME_TOKEN
        if term in tag_tokens:
            score += _TAG_TOKEN
        if term in brand_tokens:
            score += _BRAND_TOKEN
        if term in category_tokens:
            score += _CATEGORY_TOKEN

    if score > 0 and query_category is not None and product.category is query_category:
        score += _CATEGORY_AFFINITY
    if score > 0 and product.in_stock:
        score += _IN_STOCK_BONUS
    return score


def _infer_category(phrase: str) -> Category | None:
    """The category a query phrase implies, or None if it implies nothing."""
    if not phrase:
        return None
    inferred = categorize(phrase)
    return inferred if inferred is not Category.OTHER else None


def _passes_filters(product: Product, query: SearchQuery) -> bool:
    """Hard filters. Unlike relevance these are all-or-nothing."""
    if query.brand and (product.brand or "").lower() != query.brand.lower():
        return False
    if query.category and product.category != query.category:
        return False
    if query.min_price is not None and product.price < query.min_price:
        return False
    if query.max_price is not None and product.price > query.max_price:
        return False
    if query.in_stock_only and not product.in_stock:
        return False

    if query.attributes:
        haystack = {tag.lower() for tag in product.tags}
        haystack.update(product.name.lower().split())
        for attribute in query.attributes:
            needle = attribute.lower()
            if needle not in haystack and needle not in product.name.lower():
                return False
    return True


def search(query: SearchQuery) -> SearchResponse:
    """Run ``query`` against the catalog.

    A query with filters but no keywords is valid - "show me anything under
    $2" is a reasonable thing to ask - and returns everything that passes the
    filters, cheapest first.
    """
    terms = _tokens(query.text)
    phrase = " ".join(terms)
    query_category = query.category or (
        _infer_category(phrase) if phrase else None
    )

    candidates = [
        product for product in all_products() if _passes_filters(product, query)
    ]

    scored: list[tuple[float, Product]] = []
    for product in candidates:
        if not terms:
            # No keywords: rank by price so the answer is at least ordered.
            scored.append((0.0, product))
            continue
        score = _score(product, terms, phrase, query_category)
        if score > 0:
            scored.append((score, product))

    if terms:
        scored.sort(key=lambda pair: (-pair[0], pair[1].price))
    else:
        scored.sort(key=lambda pair: pair[1].price)

    total = len(scored)
    hits = [
        SearchHit(
            product=product,
            score=round(score, 2),
            # Substitutes are only interesting when the item cannot be bought.
            alternatives=alternatives_for(product) if not product.in_stock else [],
        )
        for score, product in scored[: query.limit]
    ]

    return SearchResponse(
        query=query,
        filters=query.describe(),
        hits=hits,
        total=total,
        suggestions=_fallbacks(query, terms) if total == 0 else [],
    )


def _fallbacks(query: SearchQuery, terms: list[str]) -> list[Product]:
    """Something useful to show when a query matches nothing.

    Relaxes the filters one at a time, most-likely-to-be-wrong first: price
    caps are the usual culprit, then brand, then the attribute list.
    """
    if not terms:
        # Nothing to rank a relaxed result set by, so there is no useful
        # "closest match" to offer.
        return []

    for relaxed in (
        query.model_copy(update={"min_price": None, "max_price": None}),
        query.model_copy(update={"brand": None}),
        query.model_copy(update={"attributes": []}),
        query.model_copy(
            update={
                "min_price": None,
                "max_price": None,
                "brand": None,
                "attributes": [],
            }
        ),
    ):
        candidates = [
            product for product in all_products() if _passes_filters(product, relaxed)
        ]
        query_category = _infer_category(" ".join(terms))
        scored = [
            (_score(product, terms, " ".join(terms), query_category), product)
            for product in candidates
        ]
        matches = sorted(
            ((score, product) for score, product in scored if score > 0),
            key=lambda pair: (-pair[0], pair[1].price),
        )
        if matches:
            return [product for _, product in matches[:3]]
    return []


def best_match(name: str, *, min_score: float = 3.0) -> Product | None:
    """The single catalog product a free-text name most likely refers to.

    Used by the recommendation engine to resolve list and history entries onto
    catalog ids. Returns None below ``min_score`` so that a vague name does not
    silently bind to an unrelated product.
    """
    if not name or not name.strip():
        return None
    terms = _tokens(name)
    if not terms:
        return None
    phrase = " ".join(terms)

    query_category = _infer_category(phrase)
    best: tuple[float, Product] | None = None
    for product in all_products():
        score = _score(product, terms, phrase, query_category)
        if score >= min_score and (best is None or score > best[0]):
            best = (score, product)
    return best[1] if best else None


def phrase_names_a_product(phrase: str) -> bool:
    """Whether phrase matches a single catalog product name or tag well enough to avoid splitting."""
    if not phrase or not phrase.strip():
        return False
    phrase_clean = phrase.strip().lower()
    for product in all_products():
        name = product.name.lower()
        if name == phrase_clean or f" {phrase_clean} " in f" {name} ":
            return True
        if phrase_clean in [t.lower() for t in product.tags]:
            return True
    return False

