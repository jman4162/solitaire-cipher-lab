"""Keystream generation, including the joker-skip and the fast path."""

import pytest

from helpers import random_decks
from solitaire_lab.cards import value_to_letter
from solitaire_lab.deck import ORDERED_DECK, validate_deck
from solitaire_lab.keystream import generate, generate_fast
from solitaire_lab.trace.schema import replay


def test_requested_length_is_always_produced():
    for length in (1, 5, 26, 100):
        assert len(generate(ORDERED_DECK, length).values) == length


def test_joker_outputs_are_never_emitted():
    """Rounds landing on a joker are skipped, so 53 can never appear."""
    values = generate(ORDERED_DECK, 300).values
    assert 53 not in values
    assert all(1 <= v <= 52 for v in values)


def test_skipped_round_appears_in_the_trace_but_not_the_output():
    """The unkeyed deck skips round 4 -- the trace should show it happening."""
    result = generate(ORDERED_DECK, 15, trace=True)
    outputs = [e for e in result.trace.events if e.phase == "output"]
    skipped = [e for e in outputs if e.meta["is_joker"]]
    assert len(outputs) == len(result.values) + len(skipped)
    assert any(e.round == 4 for e in skipped)


def test_every_letter_is_valid():
    result = generate(ORDERED_DECK, 200)
    assert all(ch.isalpha() and ch.isupper() for ch in result.letters)
    assert result.letters == "".join(value_to_letter(v) for v in result.values)


@pytest.mark.parametrize("deck", list(random_decks(60)))
def test_fast_path_matches_reference(deck):
    """The optimized path exists for the analysis lab; it must never diverge."""
    assert generate_fast(deck, 30) == generate(deck, 30).values


@pytest.mark.parametrize("deck", list(random_decks(20)))
def test_generation_leaves_a_valid_deck(deck):
    validate_deck(generate(deck, 40).final_deck)


def test_generation_is_deterministic():
    assert generate(ORDERED_DECK, 50).values == generate(ORDERED_DECK, 50).values


def test_longer_keystreams_extend_shorter_ones():
    """Keystream generation has no lookahead -- a prefix stays a prefix."""
    short = generate(ORDERED_DECK, 10).values
    long = generate(ORDERED_DECK, 40).values
    assert long[:10] == short


def test_trace_is_absent_unless_requested():
    assert generate(ORDERED_DECK, 5).trace is None
    assert generate(ORDERED_DECK, 5, trace=True).trace is not None


@pytest.mark.parametrize("deck", list(random_decks(15)))
def test_trace_replays_to_the_same_final_deck(deck):
    result = generate(deck, 20, trace=True)
    assert replay(result.trace.initial_deck, result.trace.events) == result.final_deck
