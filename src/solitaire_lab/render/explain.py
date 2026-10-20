"""Turning structured trace metadata into sentences.

This lives in the renderers, not in the trace, on purpose.  A trace records
*what happened*; how that is worded -- terse or chatty, English or otherwise --
is a presentation decision, and keeping it here means the wire format stays
small and translation never touches the core.
"""

from __future__ import annotations

from ..steps import Phase
from ..trace.events import TraceEvent

__all__ = ["explain", "focus", "headline"]

_HEADLINES = {
    Phase.MOVE_JOKER_A: "Move joker A down one",
    Phase.MOVE_JOKER_B: "Move joker B down two",
    Phase.TRIPLE_CUT: "Triple cut",
    Phase.COUNT_CUT: "Count cut",
    Phase.OUTPUT: "Read the output card",
}


def _cards(n: int) -> str:
    return "1 card" if n == 1 else f"{n} cards"


def _short_side(event: TraceEvent) -> str:
    """For a count cut that moves most of the deck, the same move told from the other side.

    Cutting ``count`` cards to just above the bottom card leaves the other
    ``53 - count`` cards on top, so when that block is the smaller one it is the
    easier move to see.
    """
    count = event.meta["count"]
    rest = 53 - count
    if not 0 < rest < count:
        return ""
    named = f", {event.after[0].code}," if rest == 1 else ""
    return f" That is the same as moving the {_cards(rest)} above the bottom card{named} to the top."


def focus(event: TraceEvent) -> list[int]:
    """Which positions a renderer should outline for this event.

    Usually the event's ``affected`` positions.  A count cut that moves most of
    the deck outlines the smaller block that ends up on top instead, the one
    ``_short_side`` describes, since outlining 52 of 54 cards says nothing.
    """
    if event.phase == Phase.COUNT_CUT and not event.meta.get("identity"):
        rest = 53 - event.meta["count"]
        if 0 < rest < event.meta["count"]:
            return list(range(rest))
    return list(event.affected)


def headline(event: TraceEvent) -> str:
    """A short title for the step, e.g. ``Triple cut``."""
    return _HEADLINES.get(event.phase, event.phase.replace("_", " ").title())


def explain(event: TraceEvent) -> str:
    """A one- or two-sentence account of why the deck changed as it did."""
    meta = event.meta
    if event.phase in (Phase.MOVE_JOKER_A, Phase.MOVE_JOKER_B):
        joker = meta["joker"]
        positions = "one position" if meta["positions"] == 1 else f"{meta['positions']} positions"
        if meta["wrapped"]:
            return (
                f"Joker {joker} moves down {positions}. It ran off the bottom, so it wraps round to "
                f"just below the top card, skipping the top itself, and ends at position "
                f"{meta['to_index'] + 1}."
            )
        return (
            f"Joker {joker} moves down {positions}, from position "
            f"{meta['from_index'] + 1} to {meta['to_index'] + 1}."
        )

    if event.phase == Phase.TRIPLE_CUT:
        top, bottom = meta["top_len"], meta["bottom_len"]
        if top == 0 and bottom == 0:
            return (
                "The jokers are already at the very top and bottom, so there is nothing outside them to swap."
            )
        return (
            f"Everything outside the two jokers switches sides: the {_cards(top)} above the first joker "
            f"and the {_cards(bottom)} below the second trade places. The {meta['middle_len']} cards from "
            f"one joker to the other stay exactly as they were."
        )

    if event.phase == Phase.COUNT_CUT:
        count = meta["count"]
        if meta.get("from_letter"):
            letter = meta.get("letter")
            source = f"the passphrase letter {letter} (worth {count})" if letter else f"a count of {count}"
            return (
                f"An extra count cut driven by {source}: move that many cards from the top "
                f"to just above the bottom card.{_short_side(event)}"
            )
        if meta["identity"]:
            return (
                f"The bottom card is {meta['bottom_card']}, a joker, worth 53. Cutting 53 of the "
                f"54 cards to just above the bottom card puts every one of them straight back, "
                f"so the deck is unchanged."
            )
        return (
            f"The bottom card is {meta['bottom_card']}, worth {count}. Move {_cards(count)} "
            f"from the top to just above it. The bottom card itself never moves.{_short_side(event)}"
        )

    if event.phase == Phase.OUTPUT:
        top, count, card = meta["top_card"], meta["count"], meta["output_card"]
        if meta["is_joker"]:
            return (
                f"The top card is {top}, worth {count}. Counting {count} down lands on {card}, a joker. "
                f"Jokers produce no output, so this round is discarded and we run the whole thing again."
            )
        return (
            f"The top card is {top}, worth {count}. Counting {count} down lands on {card}. "
            f"That card's value is this round's keystream number. The deck is not changed by this step."
        )

    return ""
