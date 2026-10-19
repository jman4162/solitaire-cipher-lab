"""The replay invariant and the JSON wire format.

``replay(initial_deck, events) == final_deck`` is the load-bearing guarantee of
this package: it makes every trace an executable proof of what the engine did,
which is what licenses the renderers to draw pictures from traces alone.
"""

import json

import pytest

from helpers import random_decks
from solitaire_lab.deck import ORDERED_DECK
from solitaire_lab.keying import passphrase_deck
from solitaire_lab.keystream import generate
from solitaire_lab.trace.schema import SCHEMA_VERSION, from_json, replay, to_dict, to_json


@pytest.fixture(scope="module")
def trace():
    return generate(ORDERED_DECK, 12, trace=True).trace


def test_replay_reproduces_the_final_deck(trace):
    assert replay(trace.initial_deck, trace.events) == trace.final_deck


def test_replay_detects_a_tampered_event(trace):
    """If the recorded decks and the steps disagree, replay must say so."""
    events = list(trace.events)
    bad = events[3]
    events[3] = type(bad)(
        round=bad.round,
        phase=bad.phase,
        after=bad.after[1:] + bad.after[:1],
        affected=bad.affected,
        meta=bad.meta,
        output=bad.output,
    )
    with pytest.raises(ValueError, match="diverged"):
        replay(trace.initial_deck, tuple(events))


def test_replay_detects_a_forged_output(trace):
    """The output step leaves the deck alone, so only the output check can catch this."""
    events = list(trace.events)
    index = next(i for i, e in enumerate(events) if e.output is not None)
    bad = events[index]
    forged = next(card for card in ORDERED_DECK if card != bad.output and not card.is_joker)
    events[index] = type(bad)(
        round=bad.round,
        phase=bad.phase,
        after=bad.after,
        affected=bad.affected,
        meta=dict(bad.meta, output_card=forged.code),
        output=forged,
    )
    with pytest.raises(ValueError, match="diverged"):
        replay(trace.initial_deck, tuple(events))


def test_replay_detects_forged_affected_positions(trace):
    events = list(trace.events)
    bad = events[2]
    events[2] = type(bad)(
        round=bad.round,
        phase=bad.phase,
        after=bad.after,
        affected=(9, 9),
        meta=bad.meta,
        output=bad.output,
    )
    with pytest.raises(ValueError, match="diverged"):
        replay(trace.initial_deck, tuple(events))


def test_replay_detects_stripped_output_events(trace):
    events = tuple(e for e in trace.events if e.phase != "output")
    with pytest.raises(ValueError, match="no output step"):
        replay(trace.initial_deck, events)


def test_json_round_trip_is_lossless(trace):
    restored = from_json(to_json(trace))
    assert restored.initial_deck == trace.initial_deck
    assert restored.final_deck == trace.final_deck
    assert restored.output == trace.output
    assert len(restored.events) == len(trace.events)
    assert [e.phase for e in restored.events] == [e.phase for e in trace.events]


def test_restored_trace_still_replays(trace):
    restored = from_json(to_json(trace))
    assert replay(restored.initial_deck, restored.events) == trace.final_deck


def test_schema_version_is_declared(trace):
    assert to_dict(trace)["schema"] == SCHEMA_VERSION


def test_unknown_schema_version_is_rejected(trace):
    data = to_dict(trace)
    data["schema"] = 99
    with pytest.raises(ValueError, match="schema"):
        from_json(json.dumps(data))


def test_events_carry_no_prose(trace):
    """Wording is a rendering concern and must stay out of the wire format."""
    for event in to_dict(trace)["events"]:
        assert "explanation" not in event


def test_events_store_only_the_after_deck(trace):
    """`before` is redundant: it is the previous event's `after`."""
    for event in to_dict(trace)["events"]:
        assert "before" not in event
    decks = [trace.initial_deck] + [e.after for e in trace.events]
    assert all(len(d) == 54 for d in decks)


def test_decks_are_encoded_as_codes_not_values(trace):
    """Both jokers are worth 53, so raw values could not tell them apart."""
    codes = to_dict(trace)["initial_deck"]
    assert "JA" in codes and "JB" in codes
    assert len(set(codes)) == 54


@pytest.mark.parametrize("deck", list(random_decks(10)))
def test_replay_holds_for_arbitrary_decks(deck):
    result = generate(deck, 15, trace=True)
    assert replay(result.trace.initial_deck, result.trace.events) == result.final_deck


def test_keying_trace_also_replays():
    """Passphrase keying uses letter-driven count cuts; replay must honour them."""
    deck, trace = passphrase_deck("CRYPTONOMICON", trace=True)
    assert replay(trace.initial_deck, trace.events) == deck
