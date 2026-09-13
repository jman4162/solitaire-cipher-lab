"""Why a Solitaire key must never be used twice.

This is the most important lesson in the package, and it is not specific to
Solitaire — it is true of every additive stream cipher, which is exactly why it
is worth showing here, where the key is a physical object you can watch.

If two messages are encrypted with the same keystream K:

    C1 = P1 + K
    C2 = P2 + K

then subtracting one ciphertext from the other cancels the key entirely:

    C1 - C2 = (P1 + K) - (P2 + K) = P1 - P2

An attacker who never learns K nonetheless learns the difference between the two
plaintexts, which is usually enough to unpick both.  Schneier's own description
warns against reusing a key for this reason.
"""

from __future__ import annotations

from typing import Any

from ..codec import normalize, pad, subtract_mod26, to_text, to_values
from ..deck import Deck
from ..keying import passphrase_deck
from ..keystream import generate

__all__ = ["demonstrate", "render"]


def demonstrate(
    first: str, second: str, *, passphrase: str = "SHAREDKEY", deck: Deck | None = None
) -> dict[str, Any]:
    """Encrypt two messages under the same deck and cancel the key out."""
    start = deck if deck is not None else passphrase_deck(passphrase)[0]
    p1, p2 = pad(normalize(first)), pad(normalize(second))
    width = min(len(p1), len(p2))
    p1, p2 = p1[:width], p2[:width]

    keystream = generate(start, width).values
    keys = [k % 26 or 26 for k in keystream]
    c1 = [(p + k - 1) % 26 + 1 for p, k in zip(to_values(p1), keys, strict=True)]
    c2 = [(p + k - 1) % 26 + 1 for p, k in zip(to_values(p2), keys, strict=True)]

    cipher_difference = [subtract_mod26(a, b) for a, b in zip(c1, c2, strict=True)]
    plain_difference = [subtract_mod26(a, b) for a, b in zip(to_values(p1), to_values(p2), strict=True)]

    return {
        "passphrase": passphrase,
        "plaintext_1": p1,
        "plaintext_2": p2,
        "ciphertext_1": to_text(c1),
        "ciphertext_2": to_text(c2),
        "keystream": to_text(keys),
        "cipher_difference": to_text(cipher_difference),
        "plain_difference": to_text(plain_difference),
        "key_cancelled": cipher_difference == plain_difference,
    }


def render(report: dict[str, Any]) -> str:
    """A terminal-friendly write-up of the cancellation."""
    lines = [
        "Key reuse: what an attacker gets for free",
        "=" * 52,
        "",
        f"Both messages encrypted with the same deck (passphrase {report['passphrase']!r}).",
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
    ]
    return "\n".join(lines)
