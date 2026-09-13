"""Cards, their Solitaire values, and the value <-> letter mapping.

Solitaire uses a 54-card deck: the standard 52 cards plus two distinguishable
jokers, conventionally called A and B.  Every card has a numeric value used by
the algorithm:

* pip cards are valued in *bridge order* -- clubs, diamonds, hearts, spades --
  so a card's value is its face value (A=1 .. K=13) plus an offset of 0, 13, 26
  or 39 for its suit.  Ace of clubs is 1; king of spades is 52.
* both jokers are valued 53.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "Joker",
    "Suit",
    "Card",
    "JOKER_VALUE",
    "letter_to_value",
    "value_to_letter",
]

JOKER_VALUE = 53
"""Both jokers share the value 53, which is why the count cut is a no-op when a
joker is the bottom card."""


class Suit(Enum):
    """Suits, in the bridge order that fixes each suit's value offset."""

    CLUBS = ("C", "♣", 0)
    DIAMONDS = ("D", "♦", 13)
    HEARTS = ("H", "♥", 26)
    SPADES = ("S", "♠", 39)

    def __init__(self, letter: str, symbol: str, offset: int) -> None:
        self.letter = letter
        self.symbol = symbol
        self.offset = offset

    @classmethod
    def from_letter(cls, letter: str) -> Suit:
        for suit in cls:
            if suit.letter == letter.upper():
                return suit
        raise ValueError(f"unknown suit letter: {letter!r}")


class Joker(Enum):
    """The two jokers.  They differ only in how far they move each round."""

    A = "A"
    B = "B"


_RANK_LETTERS = {1: "A", 10: "T", 11: "J", 12: "Q", 13: "K"}
_LETTER_RANKS = {v: k for k, v in _RANK_LETTERS.items()}


@dataclass(frozen=True, slots=True)
class Card:
    """A pip card (``rank`` and ``suit``) or a joker (``joker``).

    Construct one with :meth:`pip` or :meth:`the_joker` rather than by hand.
    """

    rank: int | None = None
    suit: Suit | None = None
    joker: Joker | None = None

    def __post_init__(self) -> None:
        if self.joker is not None:
            if self.rank is not None or self.suit is not None:
                raise ValueError("a joker has no rank or suit")
        else:
            if self.rank is None or self.suit is None:
                raise ValueError("a pip card needs both a rank and a suit")
            if not 1 <= self.rank <= 13:
                raise ValueError(f"rank out of range: {self.rank}")

    @classmethod
    def pip(cls, rank: int, suit: Suit | str) -> Card:
        """Build a pip card, e.g. ``Card.pip(1, "C")`` for the ace of clubs."""
        if isinstance(suit, str):
            suit = Suit.from_letter(suit)
        return cls(rank=rank, suit=suit)

    @classmethod
    def the_joker(cls, which: Joker | str) -> Card:
        """Build joker A or joker B."""
        if isinstance(which, str):
            which = Joker(which.upper())
        return cls(joker=which)

    @classmethod
    def parse(cls, code: str) -> Card:
        """Parse a short code: ``"AC"``, ``"TD"``, ``"JA"``, ``"JB"``.

        Rank letters are A, 2-9, T, J, Q, K; suit letters are C, D, H, S.  The
        joker codes ``JA``/``JB`` are unambiguous because A and B are not suits.
        """
        code = code.strip().upper()
        if code in ("JA", "JB"):
            return cls.the_joker(code[1])
        if len(code) != 2:
            raise ValueError(f"unparseable card code: {code!r}")
        rank_char, suit_char = code
        if rank_char in _LETTER_RANKS:
            rank = _LETTER_RANKS[rank_char]
        elif rank_char.isdigit() and rank_char != "0" and rank_char != "1":
            rank = int(rank_char)
        else:
            raise ValueError(f"unparseable rank in card code: {code!r}")
        return cls.pip(rank, Suit.from_letter(suit_char))

    @property
    def is_joker(self) -> bool:
        return self.joker is not None

    @property
    def value(self) -> int:
        """The card's Solitaire value: 1-52 for pip cards, 53 for either joker."""
        if self.joker is not None:
            return JOKER_VALUE
        assert self.rank is not None and self.suit is not None
        return self.suit.offset + self.rank

    @property
    def code(self) -> str:
        """The short ASCII code this card parses from."""
        if self.joker is not None:
            return f"J{self.joker.value}"
        assert self.rank is not None and self.suit is not None
        rank = _RANK_LETTERS.get(self.rank, str(self.rank))
        return f"{rank}{self.suit.letter}"

    @property
    def label(self) -> str:
        """A display label using suit symbols, e.g. ``A♣`` or ``JOKER A``."""
        if self.joker is not None:
            return f"JOKER {self.joker.value}"
        assert self.rank is not None and self.suit is not None
        rank = _RANK_LETTERS.get(self.rank, str(self.rank))
        return f"{rank}{self.suit.symbol}"

    def __str__(self) -> str:
        return self.code


def letter_to_value(letter: str) -> int:
    """Map ``A``-``Z`` to 1-26."""
    letter = letter.upper()
    if not ("A" <= letter <= "Z") or len(letter) != 1:
        raise ValueError(f"not a letter A-Z: {letter!r}")
    return ord(letter) - ord("A") + 1


def value_to_letter(value: int) -> str:
    """Map a card value to a keystream letter.

    Values 1-26 map to A-Z directly; 27-52 wrap back round to A-Z.  53 (a joker)
    has no letter -- the caller must skip it and run another round.
    """
    if value == JOKER_VALUE:
        raise ValueError("jokers produce no keystream letter")
    if not 1 <= value <= 52:
        raise ValueError(f"value out of range: {value}")
    if value > 26:
        value -= 26
    return chr(ord("A") + value - 1)
