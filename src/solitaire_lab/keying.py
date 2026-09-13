"""Ways of putting the deck into its starting state -- that is, of keying it.

The deck's starting order *is* the key.  Everything from "leave it in bridge
order" (no key at all, useful only for test vectors) to a shared passphrase
lives here.
"""

from __future__ import annotations

import random
import secrets

from .cards import letter_to_value
from .codec import normalize
from .deck import ORDERED_DECK, Deck, parse_deck, validate_deck
from .steps import count_cut, move_joker_a, move_joker_b, triple_cut
from .trace.events import Trace, TraceEvent

__all__ = ["ordered_deck", "explicit_deck", "shuffled_deck", "passphrase_deck"]


def ordered_deck() -> Deck:
    """The unkeyed deck, in bridge order.  Not a key -- a test fixture."""
    return ORDERED_DECK


def explicit_deck(text: str) -> Deck:
    """A deck given literally as 54 card codes."""
    return parse_deck(text)


def shuffled_deck(seed: int | None = None) -> Deck:
    """A randomly shuffled deck.

    With no ``seed`` the shuffle comes from the operating system's CSPRNG.
    ``seed`` makes a shuffle reproducible for teaching and testing -- and is
    emphatically not a secure way to key a real message: the seed becomes the
    key, and it is far smaller than the deck it stands for.
    """
    cards = list(ORDERED_DECK)
    rng = secrets.SystemRandom() if seed is None else random.Random(seed)
    rng.shuffle(cards)
    return validate_deck(cards)


def passphrase_deck(
    passphrase: str, *, deck: Deck | None = None, trace: bool = False
) -> tuple[Deck, Trace | None]:
    """Key the deck with a passphrase, one letter at a time.

    For each letter: run the four deck-shuffling steps as usual, then perform an
    *extra* count cut using that letter's value (A=1 .. Z=26) instead of the
    bottom card's.  The output step is not used -- keying produces no keystream.

    Returns the keyed deck and, optionally, a trace of the keying itself, so a
    learner can watch the passphrase being absorbed.
    """
    current = deck if deck is not None else ORDERED_DECK
    validate_deck(current)
    letters = normalize(passphrase)
    if not letters:
        raise ValueError("passphrase must contain at least one letter A-Z")

    events: list[TraceEvent] = []
    initial = current
    for round_number, letter in enumerate(letters, start=1):
        for step in (move_joker_a, move_joker_b, triple_cut, count_cut):
            result = step(current)
            current = result.deck
            if trace:
                events.append(
                    TraceEvent(
                        round=round_number,
                        phase=result.phase,
                        after=current,
                        affected=result.affected,
                        meta=result.metadata,
                    )
                )
        result = count_cut(current, letter_to_value(letter))
        current = result.deck
        if trace:
            meta = dict(result.metadata, letter=letter)
            events.append(
                TraceEvent(
                    round=round_number,
                    phase=result.phase,
                    after=current,
                    affected=result.affected,
                    meta=meta,
                )
            )

    return current, (Trace(initial_deck=initial, events=tuple(events)) if trace else None)
