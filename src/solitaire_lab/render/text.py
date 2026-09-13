"""Plain-text deck rendering, used by the Rich renderer and by tests."""

from __future__ import annotations

from collections.abc import Iterable

from ..deck import Deck

__all__ = ["deck_lines", "compact_deck"]


def compact_deck(deck: Deck, *, symbols: bool = True) -> str:
    return " ".join(card.short_label if symbols else card.code for card in deck)


def deck_lines(
    deck: Deck, *, per_line: int = 18, symbols: bool = True, mark: Iterable[int] = ()
) -> list[str]:
    """Wrap a deck across several lines, optionally bracketing marked positions."""
    marked = set(mark)
    cells = []
    for index, card in enumerate(deck):
        label = card.short_label if symbols else card.code
        cells.append(f"[{label}]" if index in marked else f" {label} ")
    return ["".join(cells[i : i + per_line]) for i in range(0, len(cells), per_line)]
