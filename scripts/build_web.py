"""Generate the data files the web explainer consumes.

The web player implements no cipher logic: it replays what the engine here
recorded.  That is the whole point -- the page cannot show something the
implementation does not actually do.  Run this whenever the engine changes:

    python scripts/build_web.py

``tests/test_web_data.py`` asserts the committed files still match what this
script produces, so they cannot silently go stale.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from solitaire_lab.analysis import bias, reuse  # noqa: E402
from solitaire_lab.cards import value_to_letter  # noqa: E402
from solitaire_lab.cipher import encrypt  # noqa: E402
from solitaire_lab.deck import ORDERED_DECK  # noqa: E402
from solitaire_lab.keying import passphrase_deck  # noqa: E402
from solitaire_lab.keystream import generate  # noqa: E402
from solitaire_lab.render.explain import explain, headline  # noqa: E402
from solitaire_lab.trace.schema import to_dict  # noqa: E402

DATA = ROOT / "web" / "data"

DEMO_PASSPHRASE = "CRYPTONOMICON"
DEMO_MESSAGE = "DONOTUSEPC"


def _with_explanations(payload: dict, trace) -> dict:
    """Attach per-event wording from the Python renderer.

    Kept outside the trace schema on purpose: wording is presentation, and the
    wire format stays free of it. But generating it here rather than in JS
    means one explanation engine, not two that drift.
    """
    payload["explanations"] = [{"headline": headline(e), "text": explain(e)} for e in trace.events]
    return payload


def build_keystream_trace() -> dict:
    """Six rounds on the unkeyed deck.

    Chosen because round 4 lands on a joker and is discarded -- the case most
    implementations get wrong, and the one worth showing a reader early.
    """
    result = generate(ORDERED_DECK, 6, trace=True)
    payload = _with_explanations(to_dict(result.trace), result.trace)
    payload["title"] = "Six rounds from an unkeyed deck"
    payload["letters"] = result.letters
    return payload


def build_message_trace() -> dict:
    """A full encryption under a passphrase-keyed deck."""
    deck, _ = passphrase_deck(DEMO_PASSPHRASE)
    result = encrypt(DEMO_MESSAGE, deck, trace=True)
    payload = _with_explanations(to_dict(result.trace), result.trace)
    payload["title"] = f"Encrypting {DEMO_MESSAGE} with passphrase {DEMO_PASSPHRASE}"
    payload["passphrase"] = DEMO_PASSPHRASE
    payload["plaintext"] = DEMO_MESSAGE
    payload["ciphertext"] = result.text
    payload["keystream_letters"] = [value_to_letter(v) for v in result.keystream]
    payload["keystream_values"] = [v % 26 or 26 for v in result.keystream]
    return payload


def build_reuse() -> dict:
    return reuse.demonstrate("ATTACKATDAWN", "RETREATATTEN", passphrase="SHAREDKEY")


def build_bias() -> dict:
    """Measured, not asserted. Fixed seed so the page and the repo agree."""
    return bias.measure(samples=1500, length=250, seed=42)


BUILDERS = {
    "keystream-trace.json": build_keystream_trace,
    "message-trace.json": build_message_trace,
    "reuse.json": build_reuse,
    "bias.json": build_bias,
}


def build(write: bool = True) -> dict[str, dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    built = {}
    for name, builder in BUILDERS.items():
        payload = builder()
        built[name] = payload
        if write:
            path = DATA / name
            path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
            print(f"  {path.relative_to(ROOT)}  {path.stat().st_size / 1024:.1f} KiB")
    return built


if __name__ == "__main__":
    print("building web data")
    build()
