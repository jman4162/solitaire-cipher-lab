"""Text handling: normalization, padding, grouping, and mod-26 arithmetic.

Solitaire works on the 26 letters valued 1-26, with 26 standing for Z, so the
arithmetic is "mod 26 in the range 1..26" rather than the more familiar 0..25.
"""

from __future__ import annotations

__all__ = ["normalize", "pad", "group", "add_mod26", "subtract_mod26", "to_values", "to_text"]

PAD_CHARACTER = "X"
GROUP_SIZE = 5


def normalize(text: str) -> str:
    """Upper-case ``text`` and drop everything that is not a letter."""
    return "".join(ch for ch in text.upper() if "A" <= ch <= "Z")


def pad(text: str, *, size: int = GROUP_SIZE, character: str = PAD_CHARACTER) -> str:
    """Pad to a whole number of groups, as hand-worked messages conventionally are."""
    remainder = len(text) % size
    return text if remainder == 0 else text + character * (size - remainder)


def group(text: str, *, size: int = GROUP_SIZE) -> str:
    """Split into space-separated groups, the usual way ciphertext is written out."""
    return " ".join(text[i : i + size] for i in range(0, len(text), size))


def add_mod26(a: int, b: int) -> int:
    """Add two 1..26 values, wrapping so the result stays in 1..26."""
    return (a + b - 1) % 26 + 1


def subtract_mod26(a: int, b: int) -> int:
    """Subtract two 1..26 values, wrapping so the result stays in 1..26."""
    return (a - b - 1) % 26 + 1


def to_values(text: str) -> tuple[int, ...]:
    return tuple(ord(ch) - ord("A") + 1 for ch in text)


def to_text(values: tuple[int, ...] | list[int]) -> str:
    return "".join(chr(ord("A") + v - 1) for v in values)
