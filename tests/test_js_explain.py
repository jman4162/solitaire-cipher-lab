"""The browser's wording must match the Python renderer's, character for character.

Traces made in the browser have no build step to draw explanations from, so
``web/explain.js`` duplicates ``solitaire_lab.render.explain``. That is the one
place in the package where prose exists twice, and this test is what keeps the
two honest: it renders the same events through both and compares.

Skipped when node is unavailable; CI has it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from helpers import deck_with_jokers_at, random_decks
from solitaire_lab.deck import ORDERED_DECK
from solitaire_lab.keying import passphrase_deck
from solitaire_lab.keystream import generate
from solitaire_lab.render.explain import explain, headline
from solitaire_lab.steps import triple_cut
from solitaire_lab.trace.events import Trace, TraceEvent
from solitaire_lab.trace.schema import to_dict

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

DRIVER = f"""
import {{ explain, headline }} from "{(WEB / "explain.js").as_uri()}";
let raw = "";
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {{
  const events = JSON.parse(raw);
  process.stdout.write(JSON.stringify(events.map((e) => [headline(e), explain(e)])));
}});
"""


def render_in_node(events: list[dict]) -> list[list[str]]:
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", DRIVER],
        input=json.dumps(events),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _no_op_triple_cut() -> Trace:
    """A triple cut with both jokers already at the ends, so nothing moves.

    This state cannot arise during a round -- the joker moves guarantee neither
    joker is sitting at position 0 when the triple cut happens, and a scan of
    12,481 mid-round triple cuts finds none. But ``triple_cut`` is a public
    function and the branch is real, so its wording still has to be checked.
    """
    deck = deck_with_jokers_at(0, 53)
    result = triple_cut(deck)
    assert result.metadata["top_len"] == 0 and result.metadata["bottom_len"] == 0
    event = TraceEvent(
        round=1, phase=result.phase, after=result.deck, affected=result.affected, meta=result.metadata
    )
    return Trace(initial_deck=deck, events=(event,))


def collect_events() -> tuple[list[dict], list]:
    """Events covering every phase, both wrap cases, the identity cut and a joker output."""
    # Seed 310 is the first shuffle whose count cut lands on a joker-bottomed
    # deck, which is the only way to exercise the identity-cut wording.
    identity_deck = next(random_decks(1, start_seed=310))
    traces = [
        generate(ORDERED_DECK, 8, trace=True).trace,
        generate(identity_deck, 4, trace=True).trace,
        generate(deck_with_jokers_at(53, 20), 6, trace=True).trace,
        generate(deck_with_jokers_at(20, 53), 6, trace=True).trace,
        generate(deck_with_jokers_at(0, 53), 6, trace=True).trace,
        passphrase_deck("CRYPTONOMICON", trace=True)[1],
        _no_op_triple_cut(),
    ]
    python_events = [e for t in traces for e in t.events]
    json_events = [e for t in traces for e in to_dict(t)["events"]]
    return json_events, python_events


def test_wording_is_identical_across_languages():
    json_events, python_events = collect_events()
    rendered = render_in_node(json_events)
    assert len(rendered) == len(python_events)

    mismatches = []
    for (js_headline, js_text), event in zip(rendered, python_events, strict=True):
        if js_headline != headline(event):
            mismatches.append((event.phase, "headline", headline(event), js_headline))
        if js_text != explain(event):
            mismatches.append((event.phase, "text", explain(event), js_text))
    assert not mismatches, "\n".join(
        f"{phase} {what}:\n  py: {py}\n  js: {js}" for phase, what, py, js in mismatches
    )


def test_the_comparison_covers_every_phase():
    """A wording test that never sees a phase proves nothing about it."""
    json_events, _ = collect_events()
    phases = {e["phase"] for e in json_events}
    assert phases == {"move_joker_a", "move_joker_b", "triple_cut", "count_cut", "output"}


def test_the_comparison_covers_the_awkward_cases():
    json_events, _ = collect_events()
    metas = [e["meta"] for e in json_events]
    assert any(m.get("wrapped") for m in metas), "no joker wrap covered"
    assert any(m.get("identity") for m in metas), "no identity count cut covered"
    assert any(m.get("is_joker") for m in metas), "no discarded joker round covered"
    assert any(m.get("letter") for m in metas), "no passphrase-letter cut covered"
    assert any(m.get("top_len") == 0 and m.get("bottom_len") == 0 for m in metas), (
        "no no-op triple cut covered"
    )
