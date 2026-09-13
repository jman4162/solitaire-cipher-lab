"""The web explainer's data files must match what the engine produces now.

The page ships precomputed traces so the browser never needs a cipher
implementation of its own. The risk that buys is staleness: the engine changes
and the page quietly keeps showing the old behaviour. This test closes that gap
by rebuilding every file and comparing.

If this fails, run ``python scripts/build_web.py`` and commit the result.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_web import BUILDERS, DATA  # noqa: E402

from solitaire_lab.trace.schema import from_dict, replay  # noqa: E402


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_committed_file_matches_a_fresh_build(name):
    path = DATA / name
    assert path.exists(), f"{name} is missing — run python scripts/build_web.py"
    committed = json.loads(path.read_text())
    fresh = json.loads(json.dumps(BUILDERS[name](), sort_keys=True))
    assert committed == fresh, f"{name} is stale — run python scripts/build_web.py"


@pytest.mark.parametrize("name", ["keystream-trace.json", "message-trace.json"])
def test_shipped_traces_replay(name):
    """A trace the page animates must be one the engine can re-execute."""
    trace = from_dict(json.loads((DATA / name).read_text()))
    assert replay(trace.initial_deck, trace.events) == trace.final_deck


def test_keystream_trace_contains_the_discarded_joker_round():
    """Section 2 of the page teaches this case, so the data must contain it."""
    data = json.loads((DATA / "keystream-trace.json").read_text())
    outputs = [e for e in data["events"] if e["phase"] == "output"]
    assert any(e["meta"]["is_joker"] for e in outputs)


def test_traces_ship_one_explanation_per_event():
    """The page's wording comes from the Python renderer, not from JS."""
    for name in ("keystream-trace.json", "message-trace.json"):
        data = json.loads((DATA / name).read_text())
        assert len(data["explanations"]) == len(data["events"])
        assert all(x["headline"] and x["text"] for x in data["explanations"])


def test_message_trace_carries_what_the_page_renders():
    data = json.loads((DATA / "message-trace.json").read_text())
    assert len(data["plaintext"]) == len(data["ciphertext"]) == len(data["keystream_letters"])
    assert all(1 <= v <= 26 for v in data["keystream_values"])


def test_reuse_data_shows_the_key_cancelling():
    data = json.loads((DATA / "reuse.json").read_text())
    assert data["key_cancelled"] is True
    assert data["cipher_difference"] == data["plain_difference"]


def test_bias_data_shows_an_excess_over_ideal():
    data = json.loads((DATA / "bias.json").read_text())
    assert data["observed_rate"] > data["ideal_rate"]
    assert 1.0 < data["excess_ratio"] < 1.5
