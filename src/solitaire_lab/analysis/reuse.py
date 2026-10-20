"""Why a Solitaire keystream must never be restarted.

This is the most important lesson in the package, and it is not specific to
Solitaire: it holds for every additive stream cipher.  It is worth showing here
because the state that produces the keystream is a physical deck you can watch.

The deck is deterministic.  Reset it to the same starting order, encrypt a
second message, and the second message gets the same keystream K as the first:

    C1 = P1 + K
    C2 = P2 + K

Subtracting one ciphertext from the other then cancels the key entirely:

    C1 - C2 = (P1 + K) - (P2 + K) = P1 - P2

An attacker who never learns K nonetheless learns the difference between the two
plaintexts, which is usually enough to unpick both.  Continuing from the deck
the first message left behind produces the next stretch of keystream instead,
so the subtraction no longer cancels.  That avoids this particular leak; it
does nothing about Solitaire's other weaknesses.

Both cases below run the real cipher.  Nothing here does the modular
arithmetic by hand, so the demonstration cannot disagree with ``encrypt``.
"""

from __future__ import annotations

from typing import Any

from ..cards import value_to_letter
from ..cipher import encrypt
from ..codec import normalize, pad, subtract_mod26, to_text, to_values
from ..deck import Deck
from ..keying import passphrase_deck

__all__ = ["demonstrate", "render"]


def _difference(a: str, b: str) -> str:
    return to_text([subtract_mod26(x, y) for x, y in zip(to_values(a), to_values(b), strict=True)])


def _letters(values: tuple[int, ...]) -> str:
    return "".join(value_to_letter(v) for v in values)


def demonstrate(
    first: str, second: str, *, passphrase: str = "SHAREDKEY", deck: Deck | None = None
) -> dict[str, Any]:
    """Encrypt a second message twice: from the reset deck, and from where the deck ended.

    The top-level fields describe the reset case, where the key cancels.  The
    ``continued`` field describes the same second message encrypted from the
    first message's final deck, where it does not.
    """
    start = deck if deck is not None else passphrase_deck(passphrase)[0]
    p1, p2 = pad(normalize(first)), pad(normalize(second))
    width = min(len(p1), len(p2))
    p1, p2 = p1[:width], p2[:width]

    first_run = encrypt(p1, start, pad_message=False)
    reset = encrypt(p2, start, pad_message=False)
    continued = encrypt(p2, first_run.final_deck, pad_message=False)

    plain_difference = _difference(p1, p2)
    reset_difference = _difference(first_run.text, reset.text)
    continued_difference = _difference(first_run.text, continued.text)

    return {
        "passphrase": passphrase,
        "plaintext_1": p1,
        "plaintext_2": p2,
        "ciphertext_1": first_run.text,
        "ciphertext_2": reset.text,
        "keystream": _letters(first_run.keystream),
        "cipher_difference": reset_difference,
        "plain_difference": plain_difference,
        "key_cancelled": reset_difference == plain_difference,
        "continued": {
            "ciphertext_2": continued.text,
            "keystream": _letters(continued.keystream),
            "cipher_difference": continued_difference,
            "key_cancelled": continued_difference == plain_difference,
        },
    }


def render(report: dict[str, Any]) -> str:
    """A terminal-friendly write-up of the cancellation, and of the continued deck."""
    cont = report["continued"]
    lines = [
        "Key reuse: what an attacker gets for free",
        "=" * 52,
        "",
        f"Both messages start from the same deck (passphrase {report['passphrase']!r}).",
        "",
        f"  P1  {report['plaintext_1']}",
        f"  P2  {report['plaintext_2']}",
        f"  K   {report['keystream']}",
        f"  C1  {report['ciphertext_1']}",
        f"  C2  {report['ciphertext_2']}",
        "",
        "Subtract the two ciphertexts. The keystream cancels:",
        "",
        "  C1 - C2  =  (P1 + K) - (P2 + K)  =  P1 - P2",
        "",
        f"  C1 - C2  {report['cipher_difference']}",
        f"  P1 - P2  {report['plain_difference']}",
        "",
        f"  identical: {report['key_cancelled']}",
        "",
        "The attacker never recovers K, and does not need to. The difference",
        "between the two plaintexts is usually enough to unpick both.",
        "",
        "Now encrypt P2 from the deck the first message left behind instead:",
        "",
        f"  K2       {cont['keystream']}",
        f"  C2       {cont['ciphertext_2']}",
        f"  C1 - C2  {cont['cipher_difference']}",
        f"  P1 - P2  {report['plain_difference']}",
        "",
        f"  identical: {cont['key_cancelled']}",
        "",
        "The keystream continued instead of restarting, so nothing cancels.",
    ]
    return "\n".join(lines)
