"""Recommendation engine.

Every assertion here is about an explainable signal. The month is always passed
explicitly so seasonal behaviour is deterministic rather than depending on when
the suite happens to run.
"""

from __future__ import annotations

from app.models import HistoryEntry
from app.recommend.engine import recommend, substitutes_for_name

AUGUST = 8
OCTOBER = 10


def reasons(suggestions) -> list[str]:
    return [suggestion.reason for suggestion in suggestions]


def names(suggestions) -> list[str]:
    return [suggestion.product.name for suggestion in suggestions]


def test_frequent_purchases_rank_highly() -> None:
    history = [
        HistoryEntry(name="milk", days_ago=2, count=5),
        HistoryEntry(name="chocolate", days_ago=30, count=1),
    ]
    suggestions = recommend(history, [], limit=6, month=AUGUST)
    assert suggestions
    assert "frequent" in reasons(suggestions)
    top = suggestions[0]
    assert "Milk" in top.product.name
    assert "5 times" in top.explanation


def test_frequency_beats_a_single_recent_purchase() -> None:
    history = [
        HistoryEntry(name="bread", days_ago=10, count=6),
        HistoryEntry(name="quinoa", days_ago=0, count=1),
    ]
    suggestions = recommend(history, [], limit=6, month=AUGUST)
    bread = next(s for s in suggestions if "Loaf" in s.product.name)
    quinoa = next((s for s in suggestions if "Quinoa" in s.product.name), None)
    assert quinoa is None or bread.score > quinoa.score


def test_recency_decays() -> None:
    """The same purchase count scores lower the longer ago it happened."""
    recent = recommend(
        [HistoryEntry(name="bread", days_ago=1, count=3)], [], month=AUGUST
    )
    stale = recommend(
        [HistoryEntry(name="bread", days_ago=40, count=3)], [], month=AUGUST
    )
    recent_bread = next(s for s in recent if "Loaf" in s.product.name)
    stale_bread = next(s for s in stale if "Loaf" in s.product.name)
    assert recent_bread.score > stale_bread.score


def test_seasonal_products_surface_in_their_season() -> None:
    august = recommend([], [], limit=12, month=AUGUST)
    assert "seasonal" in reasons(august)
    seasonal = [s for s in august if s.reason == "seasonal"]
    assert all(AUGUST in s.product.seasonal_months for s in seasonal)


def test_seasonality_changes_with_the_month() -> None:
    august = set(names(recommend([], [], limit=12, month=AUGUST)))
    october = set(names(recommend([], [], limit=12, month=OCTOBER)))
    assert august != october


def test_pumpkin_is_autumn_only() -> None:
    october = names(recommend([], [], limit=12, month=OCTOBER))
    august = names(recommend([], [], limit=12, month=AUGUST))
    assert "Pumpkin Whole" in october
    assert "Pumpkin Whole" not in august


def test_complementary_products_follow_the_list() -> None:
    suggestions = recommend([], ["penne pasta"], limit=8, month=AUGUST)
    assert "complementary" in reasons(suggestions)
    complements = [s for s in suggestions if s.reason == "complementary"]
    assert any("Parmesan" in s.product.name or "Sauce" in s.product.name
               for s in complements)
    assert "pasta" in complements[0].explanation.lower()


def test_substitutes_are_offered_for_unavailable_list_items() -> None:
    """The brief's example: regular milk unavailable, suggest almond milk."""
    suggestions = recommend([], ["whole milk 1l"], limit=8, month=AUGUST)
    assert "substitute" in reasons(suggestions)
    substitutes = [s for s in suggestions if s.reason == "substitute"]
    assert any("Almond Milk" in s.product.name for s in substitutes)
    assert "unavailable" in substitutes[0].explanation


def test_items_already_on_the_list_are_not_suggested() -> None:
    history = [HistoryEntry(name="milk", days_ago=1, count=5)]
    suggestions = recommend(history, ["milk"], limit=8, month=AUGUST)
    assert not any("Milk" in name for name in names(suggestions))


def test_out_of_stock_products_are_never_suggested() -> None:
    suggestions = recommend([], [], limit=20, month=AUGUST)
    assert all(s.product.in_stock for s in suggestions)


def test_empty_history_still_returns_staples() -> None:
    """A first-time user must not see an empty suggestions rail."""
    suggestions = recommend([], [], limit=6, month=AUGUST)
    assert len(suggestions) == 6


def test_every_suggestion_carries_an_explanation() -> None:
    history = [HistoryEntry(name="milk", days_ago=2, count=4)]
    for suggestion in recommend(history, ["pasta"], limit=8, month=AUGUST):
        assert suggestion.explanation.strip()
        assert suggestion.reason in {
            "frequent", "recent", "seasonal",
            "complementary", "substitute", "staple",
        }


def test_limit_is_respected() -> None:
    assert len(recommend([], [], limit=3, month=AUGUST)) == 3


def test_scores_are_descending() -> None:
    history = [
        HistoryEntry(name="milk", days_ago=1, count=4),
        HistoryEntry(name="bread", days_ago=3, count=2),
    ]
    scores = [s.score for s in recommend(history, [], limit=6, month=AUGUST)]
    assert scores == sorted(scores, reverse=True)


def test_unrecognised_history_entries_are_ignored_not_fatal() -> None:
    history = [
        HistoryEntry(name="qwertyuiop", days_ago=1, count=9),
        HistoryEntry(name="milk", days_ago=1, count=3),
    ]
    suggestions = recommend(history, [], limit=6, month=AUGUST)
    assert suggestions
    assert any("Milk" in name for name in names(suggestions))


def test_substitutes_for_name_finds_alternatives() -> None:
    product, alternatives = substitutes_for_name("whole milk 1l")
    assert product is not None
    assert product.in_stock is False
    assert alternatives
    assert all(alternative.in_stock for alternative in alternatives)
    assert "Almond Milk 1L" in [alternative.name for alternative in alternatives]


def test_substitutes_for_unknown_name_is_empty_not_an_error() -> None:
    product, alternatives = substitutes_for_name("qwertyuiop")
    assert product is None
    assert alternatives == []


def test_substitutes_fall_back_to_same_category() -> None:
    """A product with no curated alternatives still offers something."""
    product, alternatives = substitutes_for_name("garlic")
    assert product is not None
    assert alternatives
