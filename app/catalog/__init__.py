"""Product catalog: sample data, loading, categorization and search."""

from app.catalog.categorize import categorize
from app.catalog.data import (
    all_products,
    alternatives_for,
    get_product,
    known_brands,
    resolve_brand,
)
from app.catalog.search import search

__all__ = [
    "all_products",
    "alternatives_for",
    "categorize",
    "get_product",
    "known_brands",
    "resolve_brand",
    "search",
]
