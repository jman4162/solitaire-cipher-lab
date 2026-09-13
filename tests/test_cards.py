"""Card values, codes and the value-to-letter mapping."""

import pytest

from solitaire_lab.cards import JOKER_VALUE, Card, Joker, Suit, letter_to_value, value_to_letter
from solitaire_lab.deck import ORDERED_DECK, parse_deck, validate_deck


def test_bridge_order_values():
    assert Card.parse("AC").value == 1
    assert Card.parse("KC").value == 13
    assert Card.parse("AD").value == 14
    assert Card.parse("AH").value == 27
    assert Card.parse("AS").value == 40
    assert Card.parse("KS").value == 52


def test_both_jokers_share_a_value():
    assert Card.the_joker("A").value == Card.the_joker("B").value == JOKER_VALUE


def test_jokers_are_still_distinguishable():
    """They must differ as objects even though their values match."""
    assert Card.the_joker("A") != Card.the_joker("B")
    assert Card.the_joker("A").code == "JA"


def test_all_pip_values_are_unique_and_cover_one_to_fiftytwo():
    values = sorted(c.value for c in ORDERED_DECK if not c.is_joker)
    assert values == list(range(1, 53))


@pytest.mark.parametrize("code", ["AC", "2D", "9H", "TS", "JC", "QD", "KH", "JA", "JB"])
def test_code_round_trip(code):
    assert Card.parse(code).code == code


def test_parse_is_case_insensitive():
    assert Card.parse("ac") == Card.parse("AC")


@pytest.mark.parametrize("bad", ["", "X", "1C", "0C", "AX", "AAA", "10C"])
def test_bad_codes_are_rejected(bad):
    with pytest.raises(ValueError):
        Card.parse(bad)


def test_letter_value_round_trip():
    for i in range(1, 27):
        assert letter_to_value(value_to_letter(i)) == i


def test_values_above_26_wrap():
    assert value_to_letter(27) == "A"
    assert value_to_letter(52) == "Z"


def test_jokers_have_no_letter():
    with pytest.raises(ValueError, match="no keystream letter"):
        value_to_letter(JOKER_VALUE)


def test_card_construction_is_validated():
    with pytest.raises(ValueError):
        Card(rank=14, suit=Suit.CLUBS)
    with pytest.raises(ValueError):
        Card(rank=1)
    with pytest.raises(ValueError):
        Card(rank=1, suit=Suit.CLUBS, joker=Joker.A)


def test_deck_validation_catches_a_missing_card():
    with pytest.raises(ValueError, match="permutation"):
        validate_deck(ORDERED_DECK[:53] + (Card.parse("AC"),))


def test_parse_deck_accepts_commas_and_newlines():
    text = ",\n".join(c.code for c in ORDERED_DECK)
    assert parse_deck(text) == ORDERED_DECK
