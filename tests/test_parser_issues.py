"""Tests verifying fixes for user-reported NLP parsing & cart operation issues."""

import pytest
from app.models import Intent
from app.nlp.parser import parse


def test_remove_1_pizza():
    cmd = parse("remove 1 pizza")
    assert cmd.intent == Intent.REMOVE_ITEM
    assert cmd.item == "pizza"
    assert cmd.quantity == 1.0


def test_add_milk_and_eggs():
    cmd = parse("add milk and eggs")
    assert cmd.intent == Intent.ADD_ITEM
    assert len(cmd.items) == 2
    assert cmd.items[0].item == "milk"
    assert cmd.items[1].item == "eggs"


def test_add_half_a_kilo_of_tomatoes():
    cmd = parse("add half a kilo of tomatoes")
    assert cmd.intent == Intent.ADD_ITEM
    assert cmd.item == "tomatoes"
    assert cmd.quantity == 0.5
    assert cmd.unit == "kg"


def test_actually_make_that_three():
    cmd = parse("actually make that three")
    assert cmd.intent == Intent.UPDATE_ITEM
    assert cmd.item is None
    assert cmd.quantity == 3.0


def test_whats_on_my_list():
    cmd1 = parse("whats on my list")
    assert cmd1.intent == Intent.SHOW_LIST

    cmd2 = parse("what's on my list")
    assert cmd2.intent == Intent.SHOW_LIST

    cmd3 = parse("whats in my cart")
    assert cmd3.intent == Intent.SHOW_LIST


def test_remove_7_eggs_and_1_litre_of_milk():
    cmd = parse("remove 7 eggs and 1 litre of milk")
    assert cmd.intent == Intent.REMOVE_ITEM
    assert len(cmd.items) == 2
    assert cmd.items[0].item == "eggs"
    assert cmd.items[0].quantity == 7.0
    assert cmd.items[1].item == "milk"
    assert cmd.items[1].quantity == 1.0
    assert cmd.items[1].unit == "litre"


def test_remove_eggs_and_add_apple():
    cmd = parse("remove eggs and add apple")
    assert len(cmd.items) == 2
    assert cmd.items[0].item == "eggs"
    assert cmd.items[0].intent == Intent.REMOVE_ITEM
    assert cmd.items[1].item == "apple"
    assert cmd.items[1].intent == Intent.ADD_ITEM
    assert cmd.summary() == "Remove eggs, Add apple"

