"""Serialization of traces, and the replay invariant.

The JSON produced here is a wire format consumed by the web player, not just an
internal convenience, so it carries an explicit ``schema`` version from the
outset.  Decks are encoded as card codes rather than raw values because two
jokers share the value 53 and would otherwise be indistinguishable.
"""

from __future__ import annotations

import json
from typing import Any

from ..cards import Card, letter_to_value
from ..deck import Deck, validate_deck
from ..steps import (
    Phase,
    count_cut,
    move_joker_a,
    move_joker_b,
    output_card,
    triple_cut,
)
from .events import Trace, TraceEvent

__all__ = ["SCHEMA_VERSION", "to_dict", "to_json", "from_dict", "from_json", "replay", "validate"]

SCHEMA_VERSION = 1

_REPLAY_STEPS = {
    Phase.MOVE_JOKER_A: move_joker_a,
    Phase.MOVE_JOKER_B: move_joker_b,
    Phase.TRIPLE_CUT: triple_cut,
    Phase.OUTPUT: output_card,
}


def _encode_deck(deck: Deck) -> list[str]:
    return [card.code for card in deck]


def _decode_deck(codes: list[str]) -> Deck:
    return validate_deck(Card.parse(code) for code in codes)


def to_dict(trace: Trace) -> dict[str, Any]:
    """Convert a trace to plain JSON-serializable data."""
    return {
        "schema": SCHEMA_VERSION,
        "initial_deck": _encode_deck(trace.initial_deck),
        "events": [
            {
                "round": event.round,
                "phase": event.phase,
                "after": _encode_deck(event.after),
                "affected": list(event.affected),
                "meta": event.meta,
                **({"output": event.output.code} if event.output is not None else {}),
            }
            for event in trace.events
        ],
        "output": list(trace.output),
    }


def to_json(trace: Trace, *, indent: int | None = None) -> str:
    return json.dumps(to_dict(trace), indent=indent)


def from_dict(data: dict[str, Any]) -> Trace:
    version = data.get("schema")
    if version != SCHEMA_VERSION:
        raise ValueError(f"unsupported trace schema version: {version!r}")
    events = tuple(
        TraceEvent(
            round=item["round"],
            phase=item["phase"],
            after=_decode_deck(item["after"]),
            affected=tuple(item.get("affected", ())),
            meta=item.get("meta", {}),
            output=Card.parse(item["output"]) if item.get("output") else None,
        )
        for item in data["events"]
    )
    return Trace(
        initial_deck=_decode_deck(data["initial_deck"]),
        events=events,
        output=tuple(data.get("output", ())),
    )


def from_json(text: str) -> Trace:
    return from_dict(json.loads(text))


def replay(initial_deck: Deck, events: tuple[TraceEvent, ...]) -> Deck:
    """Re-execute a trace's events from scratch and return the final deck.

    This is the package's central invariant: re-running the steps a trace claims
    were taken must reproduce, event for event, the decks the trace recorded.  A
    trace that passes is a replay-verified record of what the engine did, which
    is what lets the renderers draw from traces alone.

    For each event, the deck, the affected positions, the output card and the
    metadata must all match a fresh run of that step.  Metadata must match
    exactly; the only extra key allowed is ``letter`` on a keying count cut,
    and that letter must be the one whose value is the cut's count.  A
    round's ordinary count cut must be followed by its output (or, while keying,
    by the letter's count cut).  ``validate`` adds the checks that need the
    whole trace: round numbering, phase order and the output list.
    """
    deck = initial_deck
    pending_output = None
    for event in events:
        letter_cut = event.phase == Phase.COUNT_CUT and event.meta.get("from_letter")
        if pending_output is not None and event.phase != Phase.OUTPUT and not letter_cut:
            raise ValueError(f"replay diverged at round {pending_output}: the round has no output step")
        if event.phase == Phase.COUNT_CUT:
            result = count_cut(deck, event.meta.get("count") if letter_cut else None)
        else:
            step = _REPLAY_STEPS.get(event.phase)
            if step is None:
                raise ValueError(f"cannot replay unknown phase: {event.phase!r}")
            result = step(deck)
        recorded_meta = dict(event.meta)
        if letter_cut:
            # The letter is the reason for the cut, so it must be the letter that
            # gives this count; otherwise the explanation a renderer draws is false.
            letter = recorded_meta.pop("letter", None)
            if not (
                isinstance(letter, str)
                and len(letter) == 1
                and "A" <= letter <= "Z"
                and letter_to_value(letter) == event.meta.get("count")
            ):
                raise ValueError(
                    f"replay diverged at round {event.round}: letter {letter!r} does not give this count"
                )
        if (
            result.deck != event.after
            or tuple(result.affected) != tuple(event.affected)
            or _plain(result.metadata) != _plain(recorded_meta)
            or result.output != event.output
        ):
            raise ValueError(f"replay diverged at round {event.round} phase {event.phase}")
        pending_output = event.round if event.phase == Phase.COUNT_CUT and not letter_cut else None
        deck = result.deck
    if pending_output is not None:
        raise ValueError(f"replay diverged at round {pending_output}: the round has no output step")
    return deck


_ROUND_STEPS = (Phase.MOVE_JOKER_A, Phase.MOVE_JOKER_B, Phase.TRIPLE_CUT, Phase.COUNT_CUT)


def validate(trace: Trace) -> Deck:
    """Replay a whole trace and check that it is a well-formed Solitaire run.

    On top of ``replay``: rounds are numbered 1, 2, 3 ... with no gaps; every
    round is the four deck steps followed by either an output step or, while
    keying, a letter count cut, with every round of one trace ending the same
    way (a trace is a keystream run or a keying run, never both); and
    ``trace.output`` lists exactly the values of the non-joker output cards, in
    order.  Returns the final deck.
    """
    final = replay(trace.initial_deck, trace.events)
    events = trace.events
    if len(events) % 5:
        raise ValueError(f"invalid trace: {len(events)} events is not a whole number of rounds")
    endings = {events[i].phase for i in range(4, len(events), 5)}
    if len(endings) > 1:
        raise ValueError("invalid trace: it mixes keying rounds with keystream rounds")
    for start in range(0, len(events), 5):
        number = start // 5 + 1
        block = events[start : start + 5]
        if any(event.round != number for event in block):
            raise ValueError(f"invalid trace: round {number} is misnumbered")
        if tuple(event.phase for event in block[:4]) != _ROUND_STEPS:
            raise ValueError(f"invalid trace: round {number} steps are out of order")
        last = block[4]
        if not (
            last.phase == Phase.OUTPUT or (last.phase == Phase.COUNT_CUT and last.meta.get("from_letter"))
        ):
            raise ValueError(f"invalid trace: round {number} does not end in an output or a letter cut")
    outputs = tuple(e.output.value for e in events if e.phase == Phase.OUTPUT and e.output is not None)
    if outputs != tuple(trace.output):
        raise ValueError("invalid trace: the output list does not match the output cards")
    return final


def _plain(value: Any) -> Any:
    """Normalise tuples to lists, as a JSON round trip would."""
    return json.loads(json.dumps(value))
