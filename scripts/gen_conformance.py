"""Generate the conformance vector set the JavaScript engine is held to.

The JS engine in ``web/engine.js`` is a second implementation of Solitaire, and
a second implementation is exactly what this package exists to distrust.  What
makes it tolerable is that it is not checked against ciphertexts -- it is
checked against whole *traces*.  Every event, every affected index, every
metadata key must deep-equal what the Python engine recorded, across hundreds
of decks.  A joker landing one position off fails the build.

The full set is large (tens of MB) and is generated in CI rather than
committed.  ``tests/conformance/smoke.json`` holds a handful of cases and *is*
committed, so ``node --test`` runs offline with no Python step.

    python scripts/gen_conformance.py                 # full set, to tests/conformance/vectors.json
    python scripts/gen_conformance.py --smoke         # rewrite the committed smoke set
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from solitaire_lab.cipher import encrypt  # noqa: E402
from solitaire_lab.deck import ORDERED_DECK, validate_deck  # noqa: E402
from solitaire_lab.keying import passphrase_deck  # noqa: E402
from solitaire_lab.keystream import generate  # noqa: E402
from solitaire_lab.trace.schema import to_dict, validate  # noqa: E402


def checked(trace):
    """Serialize a trace only after validate() accepts it, so no malformed vector ships."""
    validate(trace)
    return to_dict(trace)


OUT = ROOT / "tests" / "conformance"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def deck_codes(deck) -> list[str]:
    return [card.code for card in deck]


def random_deck(rng: random.Random):
    cards = list(ORDERED_DECK)
    rng.shuffle(cards)
    return validate_deck(cards)


def edge_decks() -> list[tuple[str, list]]:
    """Decks that put the jokers exactly where implementations go wrong."""
    from solitaire_lab.cards import Card, Joker

    ja, jb = Card.the_joker(Joker.A), Card.the_joker(Joker.B)
    pips = [c for c in ORDERED_DECK if not c.is_joker]

    def place(first: int, second: int):
        slots: list = [None] * 54
        slots[first], slots[second] = ja, jb
        it = iter(pips)
        for i in range(54):
            if slots[i] is None:
                slots[i] = next(it)
        return validate_deck(slots)

    # A deck whose count cut lands on a joker-bottomed deck, making the cut an
    # identity. Found by scanning shuffles: it is the only way to exercise that
    # branch, and no hand-placed starting deck reaches it, because the joker
    # moves and triple cut run first. Without this the committed smoke set
    # cannot catch a wrong `identity` flag -- which mutation testing proved.
    identity_cut = random_deck(random.Random(310))

    return [
        ("identity count cut (joker on the bottom at cut time)", identity_cut),
        ("joker A on the bottom", place(53, 20)),
        ("joker B on the bottom", place(20, 53)),
        ("joker B second from bottom", place(20, 52)),
        ("both jokers at the bottom", place(52, 53)),
        ("joker A on top", place(0, 30)),
        ("joker B on top", place(30, 0)),
        ("joker B top, joker A bottom", place(53, 0)),
        ("jokers adjacent, mid-deck", place(26, 27)),
        ("jokers adjacent, reversed", place(27, 26)),
        ("joker A top, joker B bottom", place(0, 53)),
        ("jokers at 1 and 2", place(1, 2)),
        ("jokers at 51 and 52", place(51, 52)),
    ]


def build(*, decks: int, length: int, keyings: int, messages: int, seed: int) -> dict:
    rng = random.Random(seed)
    cases: list[dict] = []

    for name, deck in edge_decks():
        result = generate(deck, 8, trace=True)
        cases.append(
            {
                "kind": "keystream",
                "name": f"edge: {name}",
                "deck": deck_codes(deck),
                "length": 8,
                "values": list(result.values),
                "trace": checked(result.trace),
            }
        )

    for i in range(decks):
        deck = random_deck(rng)
        result = generate(deck, length, trace=True)
        cases.append(
            {
                "kind": "keystream",
                "name": f"random deck {i}",
                "deck": deck_codes(deck),
                "length": length,
                "values": list(result.values),
                "trace": checked(result.trace),
            }
        )

    for _ in range(keyings):
        phrase = "".join(rng.choice(LETTERS) for _ in range(rng.randint(1, 20)))
        deck, trace = passphrase_deck(phrase, trace=True)
        cases.append(
            {
                "kind": "keying",
                "name": f"passphrase {phrase}",
                "passphrase": phrase,
                "deck": deck_codes(deck),
                "trace": checked(trace),
            }
        )

    for i in range(messages):
        deck = random_deck(rng)
        message = "".join(rng.choice(LETTERS) for _ in range(rng.randint(1, 60)))
        result = encrypt(message, deck, trace=True)
        cases.append(
            {
                "kind": "encrypt",
                "name": f"message {i}",
                "deck": deck_codes(deck),
                "plaintext": message,
                "ciphertext": result.text,
                "keystream": list(result.keystream),
                "trace": checked(result.trace),
            }
        )

    published = json.loads((ROOT / "tests" / "vectors" / "published.json").read_text())
    for case in published["messages"]:
        deck = ORDERED_DECK if case["keying"] == "ordered" else passphrase_deck(case["passphrase"])[0]
        cases.append(
            {
                "kind": "published",
                "name": case["name"],
                "deck": deck_codes(deck),
                "plaintext": case["plaintext"],
                "ciphertext": case["ciphertext"],
            }
        )
    for case in published["keystreams"]:
        deck = ORDERED_DECK if case["keying"] == "ordered" else passphrase_deck(case["passphrase"])[0]
        cases.append(
            {
                "kind": "published-keystream",
                "name": case["name"],
                "deck": deck_codes(deck),
                "length": case["length"],
                "values": case["values"],
                "letters": case["letters"],
            }
        )

    return {"generator": "scripts/gen_conformance.py", "seed": seed, "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="write the small committed set instead")
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        payload = build(decks=5, length=6, keyings=3, messages=3, seed=args.seed)
        path = OUT / "smoke.json"
    else:
        payload = build(decks=300, length=20, keyings=100, messages=100, seed=args.seed)
        path = OUT / "vectors.json"

    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"{path.relative_to(ROOT)}  {len(payload['cases'])} cases  {path.stat().st_size / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
