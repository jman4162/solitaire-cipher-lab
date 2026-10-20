"""Solitaire Cipher Lab -- teach and visualize the Solitaire (Pontifex) cipher.

Solitaire was designed by Bruce Schneier in 1999 to be executed by hand with an
ordinary deck of 54 cards.  That makes it an unusually good teaching subject:
the cipher's internal state is a physical object a learner can hold, so a stream
cipher stops being a black box and becomes something you can watch evolve.

This package treats the *execution trace* as its primary product.  Every
operation reports what it did in structured form, and every renderer -- terminal,
SVG, web -- is driven by those reports rather than reimplementing the algorithm.
A diagram therefore cannot drift out of step with the code that produced it.

.. warning::
   Solitaire is for education and experimentation.  It has known statistical
   biases and is not suitable for protecting real information.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .cards import Card, Joker, Suit, letter_to_value, value_to_letter
from .cipher import CipherResult, decrypt, encrypt
from .deck import ORDERED_DECK, Deck, format_deck, parse_deck, validate_deck
from .keying import explicit_deck, ordered_deck, passphrase_deck, shuffled_deck
from .keystream import KeystreamResult, generate, generate_fast
from .trace import Trace, TraceEvent, replay, validate

try:
    __version__ = _version("solitaire-cipher-lab")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0+unknown"

__all__ = [
    "Card",
    "Joker",
    "Suit",
    "letter_to_value",
    "value_to_letter",
    "Deck",
    "ORDERED_DECK",
    "parse_deck",
    "format_deck",
    "validate_deck",
    "generate",
    "generate_fast",
    "KeystreamResult",
    "encrypt",
    "decrypt",
    "CipherResult",
    "ordered_deck",
    "explicit_deck",
    "shuffled_deck",
    "passphrase_deck",
    "Trace",
    "TraceEvent",
    "replay",
    "validate",
    "__version__",
]
