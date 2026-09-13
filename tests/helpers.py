"""Shared test helpers."""

import random

from solitaire_lab.cards import Card, Joker
from solitaire_lab.deck import ORDERED_DECK, validate_deck

JA = Card.the_joker(Joker.A)
JB = Card.the_joker(Joker.B)


def random_decks(count: int, *, start_seed: int = 0):
    """Deterministic pseudo-random decks, for property tests."""
    for seed in range(start_seed, start_seed + count):
        cards = list(ORDERED_DECK)
        random.Random(seed).shuffle(cards)
        yield validate_deck(cards)


def deck_with_jokers_at(first: int, second: int):
    """Build a valid deck with joker A at ``first`` and joker B at ``second``."""
    pips = iter([c for c in ORDERED_DECK if not c.is_joker])
    cards: list[Card | None] = [None] * 54
    cards[first] = JA
    cards[second] = JB
    for i in range(54):
        if cards[i] is None:
            cards[i] = next(pips)
    return validate_deck(cards)
