"""Small fixtures shared by a couple of test modules."""

from solitaire_lab.cards import Card, Joker
from solitaire_lab.deck import ORDERED_DECK, validate_deck


def deck_with_joker_on_bottom():
    """A valid deck whose bottom card is a joker (value 53)."""
    joker = Card.the_joker(Joker.B)
    rest = [c for c in ORDERED_DECK if c != joker]
    return validate_deck(rest + [joker])
