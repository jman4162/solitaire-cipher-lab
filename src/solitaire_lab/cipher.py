"""Encryption and decryption over the 1..26 alphabet.

Solitaire is a stream cipher: the deck generates a keystream, and the keystream
is added to the plaintext letter by letter.  Everything interesting is in the
keystream; this module is deliberately thin, which is itself the lesson.
"""

from __future__ import annotations

from dataclasses import dataclass

from .codec import add_mod26, group, normalize, pad, subtract_mod26, to_text, to_values
from .deck import Deck
from .keystream import generate
from .trace.events import Trace

__all__ = ["CipherResult", "encrypt", "decrypt"]


@dataclass(frozen=True, slots=True)
class CipherResult:
    """The transformed text, the keystream used, and the deck left behind.

    Note that the initial deck is an explicit input and the final deck an
    explicit output.  There is no hidden cipher object carrying state between
    calls, so a second call cannot silently depend on a first.
    """

    text: str
    keystream: tuple[int, ...]
    final_deck: Deck
    trace: Trace | None = None

    @property
    def grouped(self) -> str:
        """The text in conventional five-letter groups."""
        return group(self.text)


def _run(message: str, deck: Deck, *, combine, do_pad: bool, trace: bool) -> CipherResult:
    text = normalize(message)
    if do_pad:
        text = pad(text)
    result = generate(deck, len(text), trace=trace)
    values = tuple(
        combine(p, k % 26 if k % 26 else 26) for p, k in zip(to_values(text), result.values, strict=True)
    )
    return CipherResult(
        text=to_text(values),
        keystream=result.values,
        final_deck=result.final_deck,
        trace=result.trace,
    )


def encrypt(plaintext: str, deck: Deck, *, trace: bool = False, pad_message: bool = True) -> CipherResult:
    """Encrypt ``plaintext`` with the keystream generated from ``deck``.

    Ciphertext letter = plaintext letter + keystream letter, mod 26.
    """
    return _run(plaintext, deck, combine=add_mod26, do_pad=pad_message, trace=trace)


def decrypt(ciphertext: str, deck: Deck, *, trace: bool = False) -> CipherResult:
    """Decrypt ``ciphertext`` with the keystream generated from ``deck``.

    Plaintext letter = ciphertext letter - keystream letter, mod 26.  Padding
    added at encryption time is left in place rather than guessed at.
    """
    return _run(ciphertext, deck, combine=subtract_mod26, do_pad=False, trace=trace)
