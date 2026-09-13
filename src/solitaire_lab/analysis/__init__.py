"""Cryptanalysis experiments: why Solitaire is a teaching tool, not a weapon.

Presenting Solitaire as "a historical cipher that works" wastes it.  The
interesting part is that it is a genuine stream cipher, small enough to hold in
your hands, whose weaknesses can be demonstrated rather than merely asserted --
which makes it a route into why modern ciphers are built the way they are.
"""

from . import bias, reuse

__all__ = ["bias", "reuse"]
