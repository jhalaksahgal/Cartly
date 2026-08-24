"""Catalog loading and lookup indexes.

The catalog is a static JSON file loaded once at import. That is the right
trade-off for an assessment: no database to provision, no network call on the
hot path, and the whole dataset is reviewable in the diff. Swapping this module
for a real retailer API would not change any caller, because everything above
it depends only on the functions exported here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models import Category, Product

_DATA_FILE = Path(__file__).with_name("products.json")


class CatalogError(RuntimeError):
    """Raised when the bundled catalog file is missing or malformed."""


@lru_cache(maxsize=1)
def _load() -> tuple[Product, ...]:
    try:
        raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - packaging error
        raise CatalogError(f"catalog file not found: {_DATA_FILE}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"catalog file is not valid JSON: {exc}") from exc

    entries = raw.get("products")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("catalog file contains no products")

    products: list[Product] = []
    seen: set[str] = set()
    for entry in entries:
        product = Product.model_validate(entry)
        if product.id in seen:
            raise CatalogError(f"duplicate product id: {product.id}")
        seen.add(product.id)
        products.append(product)
    return tuple(products)


def all_products() -> tuple[Product, ...]:
    """Every product in the catalog, in file order."""
    return _load()


@lru_cache(maxsize=1)
def _by_id() -> dict[str, Product]:
    return {product.id: product for product in _load()}


def get_product(product_id: str) -> Product | None:
    """Look up one product by id, or None if it does not exist."""
    return _by_id().get(product_id)


@lru_cache(maxsize=1)
def known_brands() -> tuple[str, ...]:
    """Distinct brand names, longest first so multi-word brands match first."""
    brands = {product.brand for product in _load() if product.brand}
    return tuple(sorted(brands, key=len, reverse=True))


@lru_cache(maxsize=1)
def _brand_lookup() -> dict[str, str]:
    return {brand.lower(): brand for brand in known_brands()}


def resolve_brand(name: str) -> str | None:
    """Map a lowercase brand mention back to its canonical spelling."""
    return _brand_lookup().get(name.strip().lower())


@lru_cache(maxsize=1)
def known_categories() -> tuple[Category, ...]:
    """Categories that actually appear in the catalog."""
    return tuple(dict.fromkeys(product.category for product in _load()))


def alternatives_for(
    product: Product, *, in_stock_only: bool = True, limit: int = 3
) -> list[Product]:
    """Substitutes for ``product``, best-effort and never raising.

    Falls back to same-category products at a similar price when the curated
    ``alternatives`` list is empty or entirely out of stock, so the substitute
    flow degrades gracefully instead of showing nothing.
    """
    picked: list[Product] = []
    for alternative_id in product.alternatives:
        alternative = get_product(alternative_id)
        if alternative is None or alternative.id == product.id:
            continue
        if in_stock_only and not alternative.in_stock:
            continue
        picked.append(alternative)
        if len(picked) >= limit:
            return picked

    if len(picked) < limit:
        chosen = {item.id for item in picked} | {product.id}
        same_category = [
            candidate
            for candidate in _load()
            if candidate.category == product.category
            and candidate.id not in chosen
            and (candidate.in_stock or not in_stock_only)
        ]
        same_category.sort(key=lambda item: abs(item.price - product.price))
        picked.extend(same_category[: limit - len(picked)])

    return picked


def complements_for(product: Product, *, limit: int = 3) -> list[Product]:
    """In-stock products commonly bought alongside ``product``."""
    found: list[Product] = []
    for complement_id in product.complements:
        complement = get_product(complement_id)
        if complement is not None and complement.in_stock:
            found.append(complement)
        if len(found) >= limit:
            break
    return found
