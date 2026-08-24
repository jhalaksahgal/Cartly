"""Catalog data integrity and automatic categorization.

The data-integrity tests matter because the catalog is hand-authored JSON: a
typo in an `alternatives` id would otherwise show up as a silently missing
substitute rather than as a failure.
"""

from __future__ import annotations

import pytest

from app.catalog.categorize import categorize
from app.catalog.data import (
    all_products,
    alternatives_for,
    complements_for,
    get_product,
    known_brands,
)
from app.models import Category


# --------------------------------------------------------------------------
# Data integrity
# --------------------------------------------------------------------------


def test_catalog_is_large_enough_to_demonstrate_search() -> None:
    assert len(all_products()) >= 30


def test_product_ids_are_unique() -> None:
    ids = [product.id for product in all_products()]
    assert len(ids) == len(set(ids))


def test_every_alternative_id_exists() -> None:
    for product in all_products():
        for alternative_id in product.alternatives:
            assert get_product(alternative_id) is not None, (
                f"{product.id} references missing alternative {alternative_id}"
            )


def test_every_complement_id_exists() -> None:
    for product in all_products():
        for complement_id in product.complements:
            assert get_product(complement_id) is not None, (
                f"{product.id} references missing complement {complement_id}"
            )


def test_no_product_lists_itself_as_its_own_alternative() -> None:
    for product in all_products():
        assert product.id not in product.alternatives


def test_prices_are_positive() -> None:
    assert all(product.price > 0 for product in all_products())


def test_seasonal_months_are_valid() -> None:
    for product in all_products():
        assert all(1 <= month <= 12 for month in product.seasonal_months)


def test_catalog_covers_every_category_the_ui_renders() -> None:
    present = {product.category for product in all_products()}
    # Every category except the OTHER fallback should have real products.
    missing = set(Category) - present - {Category.OTHER}
    assert not missing, f"no sample products for {missing}"


def test_catalog_includes_out_of_stock_items_for_the_substitute_flow() -> None:
    unavailable = [product for product in all_products() if not product.in_stock]
    assert unavailable, "sample data must exercise the substitute path"
    for product in unavailable:
        assert alternatives_for(product), f"{product.id} has no available substitute"


def test_brands_are_discoverable() -> None:
    brands = known_brands()
    assert "Colgate" in brands
    # Longest-first ordering lets multi-word brands match before their prefixes.
    assert list(brands) == sorted(brands, key=len, reverse=True)


def test_alternatives_are_in_stock_by_default() -> None:
    for product in all_products():
        assert all(
            alternative.in_stock for alternative in alternatives_for(product)
        )


def test_complements_resolve() -> None:
    pasta = get_product("pasta-penne")
    assert pasta is not None
    assert complements_for(pasta)


def test_get_product_returns_none_for_unknown_id() -> None:
    assert get_product("does-not-exist") is None


# --------------------------------------------------------------------------
# Categorization
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("item", "category"),
    [
        ("milk", Category.DAIRY),
        ("cheese", Category.DAIRY),
        ("eggs", Category.DAIRY),
        ("apples", Category.PRODUCE),
        ("bananas", Category.PRODUCE),
        ("tomatoes", Category.PRODUCE),
        ("bread", Category.BAKERY),
        ("bagels", Category.BAKERY),
        ("chicken", Category.MEAT_SEAFOOD),
        ("salmon", Category.MEAT_SEAFOOD),
        ("pasta", Category.PANTRY),
        ("rice", Category.PANTRY),
        ("chips", Category.SNACKS),
        ("chocolate", Category.SNACKS),
        ("toothpaste", Category.PERSONAL_CARE),
        ("shampoo", Category.PERSONAL_CARE),
        ("detergent", Category.HOUSEHOLD),
        ("toilet paper", Category.HOUSEHOLD),
        ("water", Category.BEVERAGES),
        ("coffee", Category.BEVERAGES),
        ("ice cream", Category.FROZEN),
        ("diapers", Category.BABY),
    ],
)
def test_categorization(item: str, category: Category) -> None:
    assert categorize(item) is category


def test_categorization_handles_plurals() -> None:
    assert categorize("apple") is categorize("apples")
    assert categorize("banana") is categorize("bananas")


def test_longer_keyword_wins() -> None:
    """"peanut butter" is Pantry even though "butter" alone is Dairy."""
    assert categorize("butter") is Category.DAIRY
    assert categorize("peanut butter") is Category.PANTRY


def test_word_boundaries_are_respected() -> None:
    """"chip" must not match inside "chipotle"."""
    assert categorize("chipotle paste") is not Category.SNACKS


@pytest.mark.parametrize(
    ("item", "category"),
    [
        # Each of these is a collision between two single-word keywords,
        # resolved by an explicit multi-word entry in the dictionary.
        ("potato chips", Category.SNACKS),      # vs "potato" -> Produce
        ("tortilla chips", Category.SNACKS),    # vs "tortilla" -> Bakery
        ("almond milk", Category.DAIRY),        # vs "almond" -> Pantry
        ("apple juice", Category.BEVERAGES),    # vs "apple" -> Produce
        ("orange juice", Category.BEVERAGES),   # vs "orange" -> Produce
        ("green tea", Category.BEVERAGES),      # vs "greens" -> Produce
        ("tomato sauce", Category.PANTRY),      # vs "tomato" -> Produce
        ("chicken stock", Category.PANTRY),     # vs "chicken" -> Meat
        ("garlic bread", Category.BAKERY),      # vs "garlic" -> Produce
        ("peanut butter", Category.PANTRY),     # vs "butter" -> Dairy
    ],
)
def test_ambiguous_compound_names(item: str, category: Category) -> None:
    assert categorize(item) is category


def test_compound_disambiguation_does_not_break_the_base_word() -> None:
    """Adding "potato chips" must not steal plain "potatoes" from Produce."""
    assert categorize("potatoes") is Category.PRODUCE
    assert categorize("tomatoes") is Category.PRODUCE
    assert categorize("chicken") is Category.MEAT_SEAFOOD
    assert categorize("coffee") is Category.BEVERAGES


def test_unknown_items_fall_back_to_other() -> None:
    assert categorize("qwertyuiop") is Category.OTHER
    assert categorize("") is Category.OTHER
    assert categorize("   ") is Category.OTHER


def test_categorization_is_case_insensitive() -> None:
    assert categorize("MILK") is categorize("milk")
