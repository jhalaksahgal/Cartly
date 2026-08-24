"""Heuristic recommendation engine.

This is not machine learning and does not claim to be. It is a weighted sum of
five signals, each of which can be stated in one sentence to the user:

    frequency      how often they have bought it
    recency        how recently they bought it
    seasonality    whether it is in season this month
    complementary  whether it pairs with something already on the list
    substitute     whether it replaces something on the list that is unavailable

Explainability is the point. A recommender a user can argue with is more useful
at this scale than one they cannot, and every card carries the reason it
appeared. A learned model would need purchase data this application does not
have and could not justify its output to the person reading it.
"""

from __future__ import annotations

import math
from datetime import date

from app.catalog.data import all_products, alternatives_for, get_product
from app.catalog.search import best_match
from app.models import HistoryEntry, Product, Suggestion, SuggestionReason
from app.nlp.normalize import normalize, singularize_phrase

# Signal weights. Tuned so that a strong single signal (a weekly staple, or a
# substitute for something unavailable) can outrank a weak combination.
_FREQUENCY_WEIGHT = 2.2
_FREQUENCY_CAP = 5.0
_RECENCY_WEIGHT = 3.0
#: Days after which a purchase contributes roughly a third of its recency
#: score. Groceries run on a weekly-ish cycle, so two weeks is a sensible knee.
_RECENCY_HALFLIFE = 14.0
_SEASONAL_WEIGHT = 2.6
_COMPLEMENT_WEIGHT = 3.0
_SUBSTITUTE_WEIGHT = 4.0
_STAPLE_WEIGHT = 1.0

#: Shown to a brand-new user who has no history yet, so the suggestions rail is
#: never empty on first load.
_STAPLE_IDS = (
    "milk-whole-2l",
    "bread-whole-wheat",
    "eggs-dozen",
    "fruit-bananas",
    "veg-tomatoes",
    "coffee-ground",
)


def _key(name: str) -> str:
    """Normalized comparison key for an item or product name."""
    return singularize_phrase(normalize(name))


def _resolve(name: str, product_id: str | None = None) -> Product | None:
    """Resolve a free-text name (or explicit id) onto a catalog product."""
    if product_id:
        product = get_product(product_id)
        if product is not None:
            return product
    return best_match(name)


class _Signal:
    """One scored reason for suggesting a product."""

    __slots__ = ("score", "reason", "explanation")

    def __init__(self, score: float, reason: SuggestionReason, explanation: str) -> None:
        self.score = score
        self.reason = reason
        self.explanation = explanation


def _frequency_signal(count: int, window_days: int) -> _Signal | None:
    if count < 2:
        return None
    score = min(float(count), _FREQUENCY_CAP) * _FREQUENCY_WEIGHT
    window = "month" if window_days <= 31 else f"{window_days} days"
    return _Signal(score, "frequent", f"Bought {count} times in the last {window}")


def _recency_signal(days_ago: int) -> _Signal | None:
    if days_ago > 45:
        return None
    # Exponential decay: today scores full weight, two weeks ago about a third.
    score = _RECENCY_WEIGHT * math.exp(-days_ago / _RECENCY_HALFLIFE)
    if score < 0.4:
        return None
    if days_ago == 0:
        text = "You bought this today"
    elif days_ago == 1:
        text = "You bought this yesterday"
    elif days_ago <= 10:
        text = f"You bought this {days_ago} days ago"
    else:
        text = "You bought this recently"
    return _Signal(score, "recent", text)


def _seasonal_signal(product: Product, month: int) -> _Signal | None:
    if month not in product.seasonal_months:
        return None
    return _Signal(_SEASONAL_WEIGHT, "seasonal", "In season right now")


def recommend(
    history: list[HistoryEntry],
    current_items: list[str],
    *,
    limit: int = 6,
    month: int | None = None,
) -> list[Suggestion]:
    """Rank catalog products for this user.

    ``history`` and ``current_items`` come from the browser, so the server keeps
    no per-user state. Items already on the list are never suggested back.
    """
    month = month or date.today().month
    on_list = {_key(item) for item in current_items if item and item.strip()}

    # Aggregate history by resolved product so that "milk" and "Whole Milk 1L"
    # reinforce each other instead of competing.
    counts: dict[str, int] = {}
    freshest: dict[str, int] = {}
    window = 0
    for entry in history:
        product = _resolve(entry.name, entry.product_id)
        if product is None:
            continue
        counts[product.id] = counts.get(product.id, 0) + entry.count
        freshest[product.id] = min(
            freshest.get(product.id, entry.days_ago), entry.days_ago
        )
        window = max(window, entry.days_ago)
    window = max(window, 1)

    # Products that pair with, or stand in for, what is already on the list.
    complements: dict[str, str] = {}
    substitutes: dict[str, str] = {}
    for item in current_items:
        product = _resolve(item)
        if product is None:
            continue
        for complement_id in product.complements:
            complements.setdefault(complement_id, product.name)
        if not product.in_stock:
            for alternative in alternatives_for(product):
                substitutes.setdefault(alternative.id, product.name)

    suggestions: list[Suggestion] = []
    for product in all_products():
        if not product.in_stock:
            continue
        if _key(product.name) in on_list:
            continue
        # Skip anything whose own name is on the list under a looser name,
        # e.g. list has "milk" and this is "Whole Milk 2L". Terms shorter than
        # three characters are too weak to match on and would exclude
        # everything.
        if any(len(term) >= 3 and term in _key(product.name) for term in on_list):
            continue

        signals: list[_Signal] = []
        count = counts.get(product.id, 0)
        if count:
            frequency = _frequency_signal(count, window)
            if frequency:
                signals.append(frequency)
            recency = _recency_signal(freshest[product.id])
            if recency:
                signals.append(recency)

        seasonal = _seasonal_signal(product, month)
        if seasonal:
            signals.append(seasonal)

        if product.id in complements:
            signals.append(
                _Signal(
                    _COMPLEMENT_WEIGHT,
                    "complementary",
                    f"Goes well with {complements[product.id]} on your list",
                )
            )
        if product.id in substitutes:
            signals.append(
                _Signal(
                    _SUBSTITUTE_WEIGHT,
                    "substitute",
                    f"{substitutes[product.id]} is unavailable - try this instead",
                )
            )

        if not signals:
            continue

        total = sum(signal.score for signal in signals)
        # The card shows the single strongest reason; the score is the sum, so
        # a product supported by several weak signals can still rank well.
        leading = max(signals, key=lambda signal: signal.score)
        suggestions.append(
            Suggestion(
                product=product,
                score=round(total, 2),
                reason=leading.reason,
                explanation=leading.explanation,
            )
        )

    suggestions.sort(key=lambda suggestion: (-suggestion.score, suggestion.product.name))

    if len(suggestions) < limit:
        suggestions.extend(
            _staples(
                limit - len(suggestions),
                on_list,
                {suggestion.product.id for suggestion in suggestions},
                month,
            )
        )

    return suggestions[:limit]


def _staples(
    needed: int, on_list: set[str], already: set[str], month: int
) -> list[Suggestion]:
    """Fill out a thin suggestion list for users with little or no history."""
    filled: list[Suggestion] = []
    for product_id in _STAPLE_IDS:
        if needed <= 0:
            break
        product = get_product(product_id)
        if product is None or not product.in_stock:
            continue
        if product.id in already or _key(product.name) in on_list:
            continue
        if any(len(term) >= 3 and term in _key(product.name) for term in on_list):
            continue
        seasonal = _seasonal_signal(product, month)
        filled.append(
            Suggestion(
                product=product,
                score=round(_STAPLE_WEIGHT + (seasonal.score if seasonal else 0), 2),
                reason=seasonal.reason if seasonal else "staple",
                explanation=(
                    seasonal.explanation if seasonal else "A popular weekly staple"
                ),
            )
        )
        needed -= 1
    return filled


def substitutes_for_name(name: str, *, limit: int = 3) -> tuple[Product | None, list[Product]]:
    """Find substitutes for a named product.

    Returns the matched product (or None) and its in-stock alternatives, so the
    UI can say "Milk isn't available - try these instead".
    """
    product = _resolve(name)
    if product is None:
        return None, []
    return product, alternatives_for(product, limit=limit)
