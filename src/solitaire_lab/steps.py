"""The five atomic transformations that make up one Solitaire round.

Each function takes a deck and returns a :class:`StepResult` holding the new
deck plus a structured description of what changed.  Nothing mutates; nothing
is hidden.  The renderers and the web player are driven entirely by the events
these functions emit, which is what keeps the pictures honest: a diagram cannot
drift from the implementation if it is generated from the implementation's own
account of what it did.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cards import JOKER_VALUE, Card, Joker, value_to_letter
from .deck import Deck, joker_indices

__all__ = [
    "Phase",
    "StepResult",
    "move_joker_a",
    "move_joker_b",
    "triple_cut",
    "count_cut",
    "output_card",
    "move_joker_down",
]


class Phase:
    """Names for the five steps, used as the ``phase`` tag on trace events."""

    MOVE_JOKER_A = "move_joker_a"
    MOVE_JOKER_B = "move_joker_b"
    TRIPLE_CUT = "triple_cut"
    COUNT_CUT = "count_cut"
    OUTPUT = "output"


@dataclass(frozen=True, slots=True)
class StepResult:
    """The deck after a step, plus structured facts about the transition.

    ``affected`` lists indices *in the resulting deck* that a renderer should
    highlight.  ``meta`` carries step-specific facts (which indices the jokers
    sat at, how long each triple-cut segment was, and so on) from which any
    renderer can compose its own explanation.  Deliberately there is no
    human-readable string here: wording is a rendering concern, and baking it
    into the trace would bloat the JSON and drag i18n into the core.
    """

    deck: Deck
    phase: str
    affected: tuple[int, ...] = ()
    meta: dict[str, Any] | None = None
    output: Card | None = None

    @property
    def metadata(self) -> dict[str, Any]:
        return self.meta or {}


def move_joker_down(deck: Deck, joker: Joker, count: int) -> StepResult:
    """Move ``joker`` down ``count`` positions, wrapping past the bottom.

    The wrap rule is the fiddly part: a joker at the bottom of the deck does not
    move to the top, it moves to *just below* the top card.  Equivalently, the
    deck is circular over positions 1..53 as far as a wrapping joker is
    concerned.  Moving down 2 is two single moves, each applying that rule, so a
    joker on the bottom ends up third from the top rather than second.
    """
    cards = list(deck)
    target = Card.the_joker(joker)
    index = cards.index(target)
    start = index
    wrapped = False
    for _ in range(count):
        if index == len(cards) - 1:
            cards.pop(index)
            cards.insert(1, target)
            index = 1
            wrapped = True
        else:
            cards[index], cards[index + 1] = cards[index + 1], cards[index]
            index += 1
    phase = Phase.MOVE_JOKER_A if joker is Joker.A else Phase.MOVE_JOKER_B
    return StepResult(
        deck=tuple(cards),
        phase=phase,
        affected=(index,),
        meta={
            "joker": joker.value,
            "positions": count,
            "from_index": start,
            "to_index": index,
            "wrapped": wrapped,
        },
    )


def move_joker_a(deck: Deck) -> StepResult:
    """Step 1: move joker A down one position."""
    return move_joker_down(deck, Joker.A, 1)


def move_joker_b(deck: Deck) -> StepResult:
    """Step 2: move joker B down two positions."""
    return move_joker_down(deck, Joker.B, 2)


def triple_cut(deck: Deck) -> StepResult:
    """Step 3: swap the cards above the first joker with those below the second.

    The jokers themselves, and everything between them, stay exactly where they
    are relative to each other.  Either outer segment may be empty.
    """
    first, second = joker_indices(deck)
    top = deck[:first]
    middle = deck[first : second + 1]
    bottom = deck[second + 1 :]
    new_deck = bottom + middle + top
    return StepResult(
        deck=new_deck,
        phase=Phase.TRIPLE_CUT,
        affected=tuple(range(len(bottom))) + tuple(range(len(bottom) + len(middle), len(new_deck))),
        meta={
            "first_joker_index": first,
            "second_joker_index": second,
            "top_len": len(top),
            "middle_len": len(middle),
            "bottom_len": len(bottom),
        },
    )


def count_cut(deck: Deck, count: int | None = None) -> StepResult:
    """Step 4: cut ``count`` cards from the top to just above the bottom card.

    ``count`` defaults to the value of the bottom card, which is the algorithm's
    own rule.  The bottom card never moves.  A joker on the bottom is worth 53,
    which moves all but the bottom card and therefore leaves the deck unchanged
    -- an identity case worth testing rather than special-casing.

    Passing ``count`` explicitly supports passphrase keying, where an extra
    count cut uses the value of a passphrase letter instead.
    """
    bottom = deck[-1]
    explicit = count is not None
    if count is None:
        count = bottom.value
    if not 0 <= count <= JOKER_VALUE:
        raise ValueError(f"count cut out of range: {count}")
    new_deck = deck[count:-1] + deck[:count] + (bottom,)
    return StepResult(
        deck=new_deck,
        phase=Phase.COUNT_CUT,
        affected=tuple(range(len(deck) - 1 - count, len(deck) - 1)),
        meta={
            "count": count,
            "bottom_card": bottom.code,
            "from_letter": explicit,
            "identity": count in (0, JOKER_VALUE),
        },
    )


def output_card(deck: Deck) -> StepResult:
    """Step 5: read an output card, without changing the deck.

    Take the top card's value as ``n``, count ``n`` cards down from the top, and
    look at the next one.  If that card is a joker there is no output for this
    round and the caller runs another round.  The deck is never modified here,
    which is why this step can be repeated safely.
    """
    top = deck[0]
    index = top.value
    card = deck[index]
    return StepResult(
        deck=deck,
        phase=Phase.OUTPUT,
        affected=(0, index),
        meta={
            "top_card": top.code,
            "count": top.value,
            "output_index": index,
            "output_card": card.code,
            "is_joker": card.is_joker,
            "output_value": None if card.is_joker else card.value,
            "output_letter": None if card.is_joker else value_to_letter(card.value),
        },
        output=None if card.is_joker else card,
    )
