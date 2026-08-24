"""Catalog search: keyword relevance and the four hard filters."""

from __future__ import annotations

import pytest

from app.catalog.search import best_match, search
from app.models import Category, SearchQuery


def names(response) -> list[str]:
    return [hit.product.name for hit in response.hits]


def test_keyword_search_finds_the_obvious_thing() -> None:
    response = search(SearchQuery(text="toothpaste"))
    assert response.total >= 3
    assert all("Toothpaste" in name for name in names(response))


def test_query_category_outranks_incidental_word_match() -> None:
    """Regression: "milk" used to return Milk Chocolate Bar first.

    Both contain the word "milk", but only one of them is Dairy.
    """
    response = search(SearchQuery(text="milk", limit=5))
    assert response.hits
    assert response.hits[0].product.category is Category.DAIRY
    top_five = names(response)
    assert "Milk Chocolate Bar 100g" not in top_five


def test_phrase_match_respects_word_boundaries() -> None:
    """Regression: substring matching made "ham" match "c-ham-omile"."""
    response = search(SearchQuery(text="ham"))
    assert "Chamomile Herbal Tea 20 Bags" not in names(response)


def test_brand_filter() -> None:
    response = search(SearchQuery(brand="Colgate"))
    assert response.total > 0
    assert all(hit.product.brand == "Colgate" for hit in response.hits)


def test_brand_filter_is_case_insensitive() -> None:
    assert search(SearchQuery(brand="colgate")).total == search(
        SearchQuery(brand="Colgate")
    ).total


def test_max_price_filter() -> None:
    response = search(SearchQuery(text="toothpaste", max_price=5))
    assert response.total > 0
    assert all(hit.product.price <= 5 for hit in response.hits)


def test_min_price_filter() -> None:
    response = search(SearchQuery(text="cheese", min_price=5))
    assert all(hit.product.price >= 5 for hit in response.hits)


def test_price_range_filter() -> None:
    response = search(SearchQuery(text="milk", min_price=3, max_price=4.5))
    assert response.total > 0
    assert all(3 <= hit.product.price <= 4.5 for hit in response.hits)


def test_attribute_filter() -> None:
    response = search(SearchQuery(text="apples", attributes=["organic"]))
    assert response.total > 0
    for hit in response.hits:
        assert "organic" in hit.product.tags


def test_category_filter() -> None:
    response = search(SearchQuery(category=Category.BAKERY, limit=50))
    assert response.total > 0
    assert all(hit.product.category is Category.BAKERY for hit in response.hits)


def test_combined_brand_and_price_filters() -> None:
    """The "show me Colgate under $5" case."""
    response = search(SearchQuery(brand="Colgate", max_price=5))
    assert response.total > 0
    for hit in response.hits:
        assert hit.product.brand == "Colgate"
        assert hit.product.price <= 5


def test_combined_keyword_attribute_and_price() -> None:
    response = search(
        SearchQuery(text="apples", attributes=["organic"], max_price=6)
    )
    assert response.total > 0
    for hit in response.hits:
        assert "organic" in hit.product.tags
        assert hit.product.price <= 6


def test_no_results_offers_fallbacks() -> None:
    """An impossible price cap still shows the closest real products."""
    response = search(SearchQuery(text="toothpaste", max_price=0.5))
    assert response.total == 0
    assert response.suggestions
    assert all("Toothpaste" in product.name for product in response.suggestions)


def test_no_results_and_no_fallbacks_is_not_an_error() -> None:
    response = search(SearchQuery(text="helicopter parts"))
    assert response.total == 0
    assert response.hits == []


def test_filters_are_described_for_the_user() -> None:
    """The UI shows these chips so the query is never a black box."""
    response = search(SearchQuery(text="toothpaste", brand="Colgate", max_price=5))
    assert "Searching for: toothpaste" in response.filters
    assert "Brand: Colgate" in response.filters
    assert "Max price: $5" in response.filters


def test_out_of_stock_item_carries_substitutes() -> None:
    response = search(SearchQuery(text="milk", limit=20))
    out_of_stock = [hit for hit in response.hits if not hit.product.in_stock]
    assert out_of_stock, "sample data should include an unavailable milk"
    assert out_of_stock[0].alternatives


def test_in_stock_only_filter() -> None:
    response = search(SearchQuery(text="milk", in_stock_only=True, limit=20))
    assert all(hit.product.in_stock for hit in response.hits)


def test_limit_is_respected_but_total_is_honest() -> None:
    response = search(SearchQuery(text="milk", limit=2))
    assert len(response.hits) == 2
    assert response.total > 2


def test_filter_only_query_returns_cheapest_first() -> None:
    """"Anything under $2" is a reasonable request with no keywords."""
    response = search(SearchQuery(max_price=2, limit=10))
    prices = [hit.product.price for hit in response.hits]
    assert prices == sorted(prices)
    assert all(price <= 2 for price in prices)


def test_results_are_ordered_by_relevance() -> None:
    response = search(SearchQuery(text="almond milk"))
    assert response.hits[0].product.name == "Almond Milk 1L"
    scores = [hit.score for hit in response.hits]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("apples", "apple"),
        ("apple", "apple"),
        ("oranges", "orange"),
        ("bananas", "banana"),
    ],
)
def test_singular_and_plural_match_the_same_products(query: str, expected: str) -> None:
    response = search(SearchQuery(text=query))
    assert response.total > 0
    assert any(expected in hit.product.name.lower() for hit in response.hits)


def test_empty_query_is_safe() -> None:
    response = search(SearchQuery(text=""))
    assert response.total > 0


def test_best_match_resolves_a_loose_name() -> None:
    assert best_match("milk") is not None
    assert best_match("almond milk").id == "milk-almond-1l"


def test_best_match_returns_none_for_nonsense() -> None:
    assert best_match("qwertyuiop") is None
    assert best_match("") is None
