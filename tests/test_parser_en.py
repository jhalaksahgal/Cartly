"""English command parsing.

These cases are the contract for the parser: every phrasing listed in the
project brief appears here, alongside the near-miss variants that a
string-matching implementation would get wrong.
"""

from __future__ import annotations

import pytest

from app.models import Intent
from app.nlp.parser import parse


@pytest.mark.parametrize(
    ("utterance", "item"),
    [
        ("Add milk", "milk"),
        ("add milk", "milk"),
        ("I need apples", "apples"),
        ("I want to buy bananas", "bananas"),
        ("Put eggs on my shopping list", "eggs"),
        ("Please add some bread", "bread"),
        ("Grab a bag of rice", "rice"),
        ("Don't forget the coffee", "coffee"),
        ("We need cheese", "cheese"),
        ("Pick up tomatoes", "tomatoes"),
        ("add milk to my list", "milk"),
        ("I would like to order chicken", "chicken"),
    ],
)
def test_add_phrasings(utterance: str, item: str) -> None:
    """A range of natural phrasings all reach ADD_ITEM with the right noun."""
    command = parse(utterance)
    assert command.intent is Intent.ADD_ITEM
    assert command.item == item


@pytest.mark.parametrize(
    ("utterance", "quantity", "unit", "item"),
    [
        ("I need 2 litres of milk", 2, "litre", "milk"),
        ("Add 2 bottles of water", 2, "bottle", "water"),
        ("Buy 5 oranges", 5, None, "oranges"),
        ("Please add five apples", 5, None, "apples"),
        ("Add 1.5 kg of chicken", 1.5, "kg", "chicken"),
        ("Add a dozen eggs", 1, "dozen", "eggs"),
        ("Get 3 packets of pasta", 3, "packet", "pasta"),
        ("Add twenty five bananas", 25, None, "bananas"),
        ("Add a bottle of olive oil", 1, "bottle", "olive oil"),
        ("Add two and a half kg of potatoes", 2.5, "kg", "potatoes"),
    ],
)
def test_quantity_and_unit(
    utterance: str, quantity: float, unit: str | None, item: str
) -> None:
    command = parse(utterance)
    assert command.intent is Intent.ADD_ITEM
    assert command.quantity == quantity
    assert command.unit == unit
    assert command.item == item


@pytest.mark.parametrize(
    ("utterance", "item"),
    [
        ("Remove milk from my list", "milk"),
        ("remove milk", "milk"),
        ("Delete the bread", "bread"),
        ("Take eggs off my list", "eggs"),
        ("Get rid of the chips", "chips"),
        ("I don't need cheese", "cheese"),
    ],
)
def test_remove_phrasings(utterance: str, item: str) -> None:
    command = parse(utterance)
    assert command.intent is Intent.REMOVE_ITEM
    assert command.item == item


def test_update_to_replacement() -> None:
    """"Change X to Y" yields the target and its replacement separately."""
    command = parse("Change milk to almond milk")
    assert command.intent is Intent.UPDATE_ITEM
    assert command.item == "milk"
    assert command.replacement == "almond milk"
    assert command.quantity is None


def test_update_to_quantity() -> None:
    """The same cue with a measurement is a quantity change, not a swap."""
    command = parse("Change milk to 2 litres")
    assert command.intent is Intent.UPDATE_ITEM
    assert command.item == "milk"
    assert command.quantity == 2
    assert command.unit == "litre"
    assert command.replacement is None


def test_update_to_quantity_and_replacement() -> None:
    command = parse("Change milk to 2 litres of almond milk")
    assert command.intent is Intent.UPDATE_ITEM
    assert command.item == "milk"
    assert command.quantity == 2
    assert command.unit == "litre"
    assert command.replacement == "almond milk"


@pytest.mark.parametrize(
    ("utterance", "item", "attributes"),
    [
        ("Find organic apples", "apples", ["organic"]),
        ("Search for gluten free bread", "bread", ["gluten-free"]),
        ("Look for whole grain pasta", "pasta", ["whole-grain"]),
        ("Find frozen peas", "peas", ["frozen"]),
    ],
)
def test_search_with_attributes(
    utterance: str, item: str, attributes: list[str]
) -> None:
    command = parse(utterance)
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.item == item
    assert command.attributes == attributes


@pytest.mark.parametrize(
    ("utterance", "min_price", "max_price"),
    [
        ("Find toothpaste under $5", None, 5),
        ("Find toothpaste below 10 dollars", None, 10),
        ("Find toothpaste less than five", None, 5),
        ("Find bread cheaper than $3", None, 3),
        ("Find cheese over $10", 10, None),
        ("Find cheese more than 4 dollars", 4, None),
        ("Show me milk between $3 and $6", 3, 6),
        ("Find snacks between 2 and 5 dollars", 2, 5),
        ("Find coffee up to $9", None, 9),
        ("Find wine at least 15 dollars", 15, None),
    ],
)
def test_price_filters(
    utterance: str, min_price: float | None, max_price: float | None
) -> None:
    command = parse(utterance)
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.min_price == min_price
    assert command.max_price == max_price


def test_price_number_is_not_taken_as_quantity() -> None:
    """The 5 in "under $5" belongs to the price, not to the toothpaste."""
    command = parse("Find toothpaste under $5")
    assert command.max_price == 5
    assert command.quantity is None
    assert command.item == "toothpaste"


def test_brand_extraction() -> None:
    command = parse("Show me Colgate under $5")
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.brand == "Colgate"
    assert command.max_price == 5


def test_brand_and_item_together() -> None:
    command = parse("Find Colgate toothpaste")
    assert command.brand == "Colgate"
    assert command.item == "toothpaste"


def test_packaging_word_is_not_the_item() -> None:
    """"a 1 litre bottle of milk" is milk, not "bottle of milk"."""
    command = parse("Find a 1 litre bottle of milk")
    assert command.intent is Intent.SEARCH_PRODUCT
    assert command.quantity == 1
    assert command.unit == "litre"
    assert command.item == "milk"


@pytest.mark.parametrize(
    "utterance",
    ["Show my list", "show me my shopping list", "What do I need", "my list"],
)
def test_show_list(utterance: str) -> None:
    assert parse(utterance).intent is Intent.SHOW_LIST


@pytest.mark.parametrize(
    "utterance",
    ["Clear my list", "empty my cart", "remove everything", "start over"],
)
def test_clear_list_requires_confirmation(utterance: str) -> None:
    command = parse(utterance)
    assert command.intent is Intent.CLEAR_LIST
    assert command.requires_confirmation is True


def test_add_to_my_list_is_not_show_list() -> None:
    """The words "my list" appear in both; the ADD cue must still win."""
    command = parse("add milk to my list")
    assert command.intent is Intent.ADD_ITEM
    assert command.item == "milk"


def test_remove_everything_is_clear_not_remove() -> None:
    """Longest-cue-wins keeps this from removing an item called "everything"."""
    assert parse("remove everything").intent is Intent.CLEAR_LIST


@pytest.mark.parametrize("utterance", ["yes", "confirm", "go ahead", "okay"])
def test_confirm_words(utterance: str) -> None:
    assert parse(utterance).intent is Intent.CONFIRM


@pytest.mark.parametrize("utterance", ["no", "cancel", "stop", "never mind"])
def test_cancel_words(utterance: str) -> None:
    assert parse(utterance).intent is Intent.CANCEL


def test_cancel_word_with_an_item_is_a_removal() -> None:
    """"cancel" alone is an answer; "cancel milk" is an instruction."""
    command = parse("cancel milk")
    assert command.intent is Intent.REMOVE_ITEM
    assert command.item == "milk"


@pytest.mark.parametrize("utterance", ["", "   ", "asdfgh qwerty zxcvb"])
def test_unparseable_input_is_unknown(utterance: str) -> None:
    command = parse(utterance)
    assert command.intent is Intent.UNKNOWN
    assert command.confidence == 0.0


def test_bare_product_name_is_a_low_confidence_add() -> None:
    """Saying just "milk" adds it, but flagged for confirmation."""
    command = parse("milk")
    assert command.intent is Intent.ADD_ITEM
    assert command.item == "milk"
    assert command.confidence < 0.5
    assert command.needs_clarification is True


@pytest.mark.parametrize(
    "utterance",
    [
        "we are running low on that sourdough",
        "the bread situation in this house is dire",
        "the kids finished all the cereal",
        "nothing left in the pantry",
        "my teeth need something cheap",
    ],
)
def test_long_phrases_are_not_treated_as_bare_item_names(utterance: str) -> None:
    """Regression: the bare-name fallback used to swallow whole sentences.

    Each of these contains a word the categorizer recognises, so an unbounded
    fallback turned the entire phrase into an item literally called
    "running low on that sourdough". Staying UNKNOWN is more honest, and is
    exactly the case the optional LLM fallback exists to pick up.
    """
    assert parse(utterance).intent is Intent.UNKNOWN


@pytest.mark.parametrize(
    "utterance", ["milk", "almond milk", "whole wheat bread", "organic milk"]
)
def test_short_bare_names_still_work(utterance: str) -> None:
    assert parse(utterance).intent is Intent.ADD_ITEM


def test_contractions_are_expanded_before_parsing() -> None:
    """"we're out of eggs" is a request for eggs, not for "out of eggs"."""
    command = parse("we're out of eggs")
    assert command.intent is Intent.ADD_ITEM
    assert command.item == "eggs"


def test_confident_commands_do_not_need_clarification() -> None:
    for utterance in ["add milk", "I need 2 litres of milk", "remove milk"]:
        assert parse(utterance).needs_clarification is False


def test_unknown_does_not_ask_for_clarification() -> None:
    """There is nothing to confirm when nothing was understood."""
    assert parse("asdfgh qwerty").needs_clarification is False


def test_destructive_commands_confirm_rather_than_clarify() -> None:
    """CLEAR_LIST has its own confirmation step; it must not do both."""
    command = parse("clear my list")
    assert command.requires_confirmation is True
    assert command.needs_clarification is False


def test_categorization_is_attached() -> None:
    assert parse("add milk").category.value == "Dairy"
    assert parse("add apples").category.value == "Produce"
    assert parse("add toothpaste").category.value == "Personal Care"


def test_punctuation_and_casing_are_ignored() -> None:
    a = parse("Add 2 litres of milk.")
    b = parse("add   2 LITRES of milk!!")
    assert (a.intent, a.item, a.quantity) == (b.intent, b.item, b.quantity)


def test_confidence_is_higher_with_more_detail() -> None:
    assert parse("add milk").confidence < parse("add 2 litres of milk").confidence


def test_summary_is_human_readable() -> None:
    assert parse("Find toothpaste under $5").summary() == "toothpaste under $5"
    assert parse("I need 2 litres of milk").summary() == "2 litre milk"


def test_parse_never_raises_on_hostile_input() -> None:
    """The parser is the first thing to see untrusted speech output."""
    for utterance in ["<script>alert(1)</script>", "$$$ ((( ***", "\x00\x01", "🎉🎉🎉", "a" * 500]:
        assert parse(utterance) is not None
