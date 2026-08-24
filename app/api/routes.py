"""API routes.

The server is stateless. The browser owns the shopping list (in localStorage)
and sends whatever context a request needs. That means no database, no session
store, no accounts, and no personal data at rest - which is both the simplest
thing that works and the easiest thing to deploy.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.catalog.data import all_products, known_brands, known_categories
from app.catalog.search import search as run_search
from app.models import (
    Category,
    Intent,
    ParseRequest,
    ParseResponse,
    Product,
    SearchQuery,
    SearchResponse,
    SubstitutesResponse,
    SuggestionsRequest,
    SuggestionsResponse,
)
from app.nlp import llm
from app.nlp.lexicons import get_lexicon, supported_languages
from app.nlp.parser import parse as parse_command
from app.recommend.engine import recommend, substitutes_for_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _query_from_command(command) -> SearchQuery:
    """Build a catalog query from a parsed SEARCH_PRODUCT command."""
    return SearchQuery(
        text=command.canonical_item or command.item or "",
        brand=command.brand,
        category=command.category,
        attributes=command.attributes,
        min_price=command.min_price,
        max_price=command.max_price,
    )


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "products": len(all_products()),
        "languages": [language["code"] for language in supported_languages()],
        # Reports whether the fallback is configured, never the key itself.
        "llm_fallback": llm.is_enabled(),
    }


@router.get("/languages", summary="Languages the parser and UI support")
def languages() -> dict[str, object]:
    """Language options, each with example commands in that language."""
    return {
        "languages": [
            {
                **language,
                "examples": list(get_lexicon(language["locale"]).examples),
            }
            for language in supported_languages()
        ]
    }


@router.post("/parse", response_model=ParseResponse, summary="Interpret an utterance")
def parse(request: ParseRequest) -> ParseResponse:
    """Turn a transcript into a structured command.

    When the command is a product search the results are included in the same
    response, so voice search costs one round trip rather than two.
    """
    transcript = request.transcript.strip()
    command = parse_command(transcript, request.language)

    # Rules first, always. The optional LLM fallback runs only when the
    # deterministic parser found nothing, and only if a key is configured -
    # so the common path stays offline, free and reproducible.
    if command.intent is Intent.UNKNOWN and llm.is_enabled():
        guess = llm.interpret(transcript, request.language)
        if guess is not None:
            command = guess

    search_response: SearchResponse | None = None
    if command.intent is Intent.SEARCH_PRODUCT:
        try:
            search_response = run_search(_query_from_command(command))
        except Exception:
            # A search failure should not lose the interpretation, which is
            # still useful to show the user.
            logger.exception("catalog search failed for %r", transcript)

    return ParseResponse(
        command=command,
        summary=command.summary(),
        search=search_response,
    )


@router.get("/search", response_model=SearchResponse, summary="Search the catalog")
def search(
    q: str = Query(default="", max_length=120, description="Free-text keywords"),
    brand: str | None = Query(default=None, max_length=60),
    category: Category | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0, le=10_000),
    max_price: float | None = Query(default=None, ge=0, le=10_000),
    attributes: list[str] = Query(default_factory=list),
    in_stock_only: bool = Query(default=False),
    limit: int = Query(default=12, ge=1, le=100),
) -> SearchResponse:
    """Typed/manual search. The same engine the voice path uses."""
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    return run_search(
        SearchQuery(
            text=q,
            brand=brand,
            category=category,
            attributes=[attribute for attribute in attributes if attribute.strip()],
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock_only,
            limit=limit,
        )
    )


@router.post(
    "/suggestions",
    response_model=SuggestionsResponse,
    summary="Recommendations with explanations",
)
def suggestions(request: SuggestionsRequest) -> SuggestionsResponse:
    from datetime import date

    month = request.month or date.today().month
    results = recommend(
        request.history,
        request.current_items,
        limit=request.limit,
        month=month,
    )
    return SuggestionsResponse(suggestions=results, month=month)


@router.get(
    "/substitutes",
    response_model=SubstitutesResponse,
    summary="Alternatives for a product",
)
def substitutes(
    name: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=3, ge=1, le=10),
) -> SubstitutesResponse:
    product, alternatives = substitutes_for_name(name, limit=limit)
    return SubstitutesResponse(query=name, product=product, alternatives=alternatives)


@router.get("/products", response_model=list[Product], summary="Browse the catalog")
def products(
    category: Category | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Product]:
    items = all_products()
    if category is not None:
        items = tuple(item for item in items if item.category == category)
    return list(items[:limit])


@router.get("/products/{product_id}", response_model=Product, summary="One product")
def product_detail(product_id: str) -> Product:
    from app.catalog.data import get_product

    product = get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/meta", summary="Brands and categories, for the filter UI")
def meta() -> dict[str, object]:
    return {
        "brands": sorted(known_brands()),
        "categories": [category.value for category in known_categories()],
    }
