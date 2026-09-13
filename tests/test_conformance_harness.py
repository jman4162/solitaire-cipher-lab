"""The conformance harness itself: does it exist, does it run, and can it fail?

A conformance suite that cannot fail proves nothing. These tests check that the
generated vectors cover the cases that matter, and — the important one — that
deliberately breaking the JavaScript engine makes the suite go red.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "tests" / "conformance"
ENGINE = ROOT / "web" / "engine.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def run_conformance() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", "--test", *[str(p) for p in sorted(CONFORMANCE.glob("*.test.mjs"))]],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=300,
    )


@pytest.fixture(scope="module")
def smoke() -> dict:
    return json.loads((CONFORMANCE / "smoke.json").read_text())


def test_smoke_vectors_are_committed(smoke):
    """The suite must run offline, without a Python generation step."""
    assert smoke["cases"], "smoke.json is empty"


def test_smoke_covers_every_kind(smoke):
    kinds = {c["kind"] for c in smoke["cases"]}
    assert kinds == {"keystream", "keying", "encrypt", "published", "published-keystream"}


def test_smoke_covers_the_joker_edge_decks(smoke):
    edges = [c for c in smoke["cases"] if c["name"].startswith("edge:")]
    assert len(edges) >= 12, f"only {len(edges)} edge decks"
    names = " ".join(c["name"] for c in edges)
    for case in ["on the bottom", "second from bottom", "on top", "adjacent", "both ends"]:
        assert case in names, f"edge decks do not cover: {case}"


def test_smoke_cases_carry_full_traces(smoke):
    traced = [c for c in smoke["cases"] if "trace" in c]
    assert traced
    for case in traced:
        assert case["trace"]["schema"] == 1
        assert case["trace"]["events"]
        assert len(case["trace"]["initial_deck"]) == 54


def test_the_suite_passes_as_committed():
    result = run_conformance()
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]


@pytest.mark.parametrize(
    "label,old,new",
    [
        # A joker wrapping to the top instead of below the top card. The
        # keystream still looks plausible; the trace does not.
        ("joker wrap off by one", "cards.splice(1, 0, target);", "cards.splice(0, 0, target);"),
        # The count cut failing to pin the bottom card.
        (
            "count cut moves the bottom card",
            "deck: [...deck.slice(n, -1), ...deck.slice(0, n), bottom],",
            "deck: [...deck.slice(n), ...deck.slice(0, n)],",
        ),
        # Output correct, one metadata flag wrong. Only a trace-level check
        # catches this, which is the whole argument for comparing traces.
        ("metadata flag only", "identity: n === 0 || n === JOKER_VALUE,", "identity: n === 0,"),
        # A suit offset wrong: every card value in one suit shifts.
        ("suit offset", "{ C: 0, D: 13, H: 26, S: 39 }", "{ C: 0, D: 13, H: 26, S: 40 }"),
    ],
)
def test_mutating_the_engine_makes_conformance_fail(label, old, new, tmp_path):
    """Mutation testing: prove the net has no holes where it matters."""
    original = ENGINE.read_text()
    assert old in original, f"mutation target not found for {label}: {old!r}"
    backup = tmp_path / "engine.js"
    backup.write_text(original)
    try:
        ENGINE.write_text(original.replace(old, new, 1))
        result = run_conformance()
        assert result.returncode != 0, f"conformance passed with a broken engine ({label})"
    finally:
        ENGINE.write_text(backup.read_text())

    # And the engine must be left exactly as it was found.
    assert ENGINE.read_text() == original
