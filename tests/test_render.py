"""Renderers. These consume traces and must never implement the cipher."""

import pytest

from solitaire_lab.deck import ORDERED_DECK
from solitaire_lab.keystream import generate
from solitaire_lab.render.explain import explain, headline
from solitaire_lab.render.rich_render import deck_text, render_event
from solitaire_lab.render.text import compact_deck, deck_lines


@pytest.fixture(scope="module")
def trace():
    return generate(ORDERED_DECK, 6, trace=True).trace


def test_every_event_gets_an_explanation(trace):
    for event in trace.events:
        text = explain(event)
        assert text and text[0].isupper() and text.endswith(".")


def test_every_event_gets_a_headline(trace):
    assert all(headline(event) for event in trace.events)


def test_joker_skip_is_explained_in_plain_words(trace):
    skipped = [e for e in trace.events if e.phase == "output" and e.meta["is_joker"]]
    assert skipped, "the unkeyed deck should skip a round within six letters"
    assert "no output" in explain(skipped[0])


def test_identity_count_cut_is_explained_as_unchanged():
    """A joker on the bottom is worth 53 and leaves the deck alone."""
    from helpers import deck_with_joker_on_bottom
    from solitaire_lab.steps import count_cut
    from solitaire_lab.trace.events import TraceEvent

    deck = deck_with_joker_on_bottom()
    result = count_cut(deck)
    event = TraceEvent(round=1, phase=result.phase, after=result.deck, meta=result.metadata)
    assert "unchanged" in explain(event)


def test_deck_text_covers_all_cards(trace):
    assert len(deck_text(ORDERED_DECK).plain.split()) == 54


def test_render_event_returns_a_panel(trace):
    panel = render_event(trace.events[0])
    assert panel.title.startswith("Round 1")


def test_compact_and_wrapped_text(trace):
    assert len(compact_deck(ORDERED_DECK).split()) == 54
    assert len(deck_lines(ORDERED_DECK, per_line=18)) == 3


def test_marked_positions_are_bracketed():
    assert "[" in deck_lines(ORDERED_DECK, mark=[0])[0]
