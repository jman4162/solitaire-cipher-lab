"""The SVG renderer: well-formed, complete, and driven by traces alone."""

import xml.etree.ElementTree as ET

import pytest

from solitaire_lab.deck import ORDERED_DECK
from solitaire_lab.keying import passphrase_deck
from solitaire_lab.keystream import generate
from solitaire_lab.render.svg import deck_svg, event_svg, round_svg, trace_svg

SVG = "{http://www.w3.org/2000/svg}"


def cards_in(svg: str):
    root = ET.fromstring(svg)
    return [r for r in root.iter(f"{SVG}rect") if "card" in (r.get("class") or "")]


@pytest.fixture(scope="module")
def trace():
    return generate(ORDERED_DECK, 4, trace=True).trace


def test_deck_svg_is_well_formed_and_complete():
    svg = deck_svg(ORDERED_DECK)
    assert len(cards_in(svg)) == 54
    root = ET.fromstring(svg)
    assert root.tag == f"{SVG}svg"
    assert root.find(f"{SVG}title") is not None


def test_deck_svg_marks_highlights():
    svg = deck_svg(ORDERED_DECK, highlight=[0, 53])
    assert sum("hl" in r.get("class") for r in cards_in(svg)) == 2


def test_jokers_are_visually_distinct():
    svg = deck_svg(ORDERED_DECK)
    assert sum("joker" in r.get("class") for r in cards_in(svg)) == 2


def test_event_svg_highlights_the_affected_cards(trace):
    event = trace.events[0]
    svg = event_svg(event)
    assert sum("hl" in r.get("class") for r in cards_in(svg)) == len(event.affected)


def test_event_svg_carries_the_explanation(trace):
    event = trace.events[2]  # a triple cut
    svg = event_svg(event)
    assert "Triple cut" in svg
    assert "switches sides" in svg


def test_caption_can_be_omitted(trace):
    assert "switches sides" not in event_svg(trace.events[2], caption=False)


def test_round_svg_stacks_every_step(trace):
    svg = round_svg(trace.round_events(1))
    assert len(cards_in(svg)) == 54 * 5


def test_trace_svg_limits_rounds(trace):
    assert len(cards_in(trace_svg(trace, rounds=2))) == 54 * 10
    assert len(cards_in(trace_svg(trace))) == 54 * len(trace.events)


def test_round_svg_rejects_nothing():
    with pytest.raises(ValueError):
        round_svg(())


def test_special_characters_are_escaped(trace):
    """Explanations contain em dashes and quotes; the XML must stay valid."""
    deck, keying = passphrase_deck("FOO", trace=True)
    for event in keying.events:
        ET.fromstring(event_svg(event))


def test_svg_has_a_dark_mode_block():
    assert "prefers-color-scheme:dark" in deck_svg(ORDERED_DECK)
