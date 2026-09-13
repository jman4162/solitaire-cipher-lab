"""The deck: an immutable 54-card tuple, plus parsing and validation.

A deck is a plain ``tuple[Card, ...]``.  At 54 cards there is no performance
argument for a linked list, and a tuple is far easier to inspect, serialize,
diff, hash and display -- all of which this package does constantly.
"""

from __future__ import annotations

from collections.abc import Iterable

from .cards import Card, Joker, Suit

__all__ = [
    "Deck",
    "ORDERED_DECK",
    "make_ordered_deck",
    "validate_deck",
    "parse_deck",
    "format_deck",
    "joker_indices",
]

Deck = tuple[Card, ...]

DECK_SIZE = 54


def make_ordered_deck() -> Deck:
    """A new deck in bridge order: A♣..K♣, A♦..K♦, A♥..K♥, A♠..K♠, joker A, joker B.

    This is the conventional unkeyed starting state, and the one published test
    vectors are quoted against.
    """
    cards = [Card.pip(rank, suit) for suit in Suit for rank in range(1, 14)]
    cards.append(Card.the_joker(Joker.A))
    cards.append(Card.the_joker(Joker.B))
    return tuple(cards)


ORDERED_DECK: Deck = make_ordered_deck()


def validate_deck(deck: Iterable[Card]) -> Deck:
    """Check that ``deck`` is a genuine permutation of all 54 cards.

    Raises :class:`ValueError` otherwise.  Every operation in this package
    preserves the multiset of cards, so this doubles as an invariant check.
    """
    deck = tuple(deck)
    if len(deck) != DECK_SIZE:
        raise ValueError(f"deck must hold {DECK_SIZE} cards, got {len(deck)}")
    if set(deck) != set(ORDERED_DECK):
        missing = sorted(c.code for c in set(ORDERED_DECK) - set(deck))
        extra = sorted(c.code for c in set(deck) - set(ORDERED_DECK))
        raise ValueError(f"deck is not a permutation of 54 cards (missing {missing}, duplicated {extra})")
    return deck


def parse_deck(text: str) -> Deck:
    """Parse a whitespace- or comma-separated list of 54 card codes."""
    tokens = text.replace(",", " ").split()
    return validate_deck(Card.parse(token) for token in tokens)


def format_deck(deck: Deck, *, symbols: bool = False) -> str:
    """Render a deck as a space-separated line of card codes."""
    return " ".join(card.label if symbols else card.code for card in deck)


def joker_indices(deck: Deck) -> tuple[int, int]:
    """Return the positions of the two jokers, nearest the top first."""
    found = [i for i, card in enumerate(deck) if card.is_joker]
    if len(found) != 2:
        raise ValueError(f"expected exactly 2 jokers, found {len(found)}")
    return found[0], found[1]
