"""Terminal rendering of decks and trace events.

Everything here is derived from trace events.  The renderer knows how to draw a
deck and how to phrase a step; it does not know how Solitaire works, and could
not run the cipher if it wanted to.
"""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..cards import Suit
from ..deck import Deck
from ..steps import Phase
from ..trace.events import TraceEvent
from .explain import explain, headline

__all__ = ["deck_text", "render_event", "render_round", "console"]

console = Console()

_RED_SUITS = {Suit.DIAMONDS, Suit.HEARTS}
_PHASE_STYLE = {
    Phase.MOVE_JOKER_A: "bright_magenta",
    Phase.MOVE_JOKER_B: "bright_magenta",
    Phase.TRIPLE_CUT: "bright_cyan",
    Phase.COUNT_CUT: "bright_yellow",
    Phase.OUTPUT: "bright_green",
}


def deck_text(
    deck: Deck, *, highlight: tuple[int, ...] = (), per_line: int = 18, style: str = "bold"
) -> Text:
    """A deck as coloured text, with ``highlight`` positions called out."""
    marked = set(highlight)
    text = Text()
    for index, card in enumerate(deck):
        if index and index % per_line == 0:
            text.append("\n")
        if card.is_joker:
            label = f"J{card.joker.value}"
            base = "bold white on dark_red"
        else:
            label = card.label
            base = "red" if card.suit in _RED_SUITS else "white"
        cell = f"{label:>4}"
        text.append(cell, style=f"{style} reverse" if index in marked else base)
    return text


def render_event(event: TraceEvent, *, per_line: int = 18, show_deck: bool = True) -> Panel:
    """One trace event as a titled panel: what happened, why, and the result."""
    style = _PHASE_STYLE.get(event.phase, "white")
    parts: list = [Text(explain(event), style="italic dim")]
    if show_deck:
        parts.append(Text(""))
        parts.append(deck_text(event.after, highlight=event.affected, per_line=per_line, style=style))
    if event.output is not None:
        parts.append(Text(""))
        parts.append(
            Text.assemble(
                ("keystream ", "dim"),
                (f"{event.output.label}", "bold"),
                (" = ", "dim"),
                (f"{event.output.value}", "bold"),
                (" -> ", "dim"),
                (f"{_letter(event.output.value)}", "bold bright_green"),
            )
        )
    title = f"Round {event.round} · {headline(event)}"
    return Panel(Group(*parts), title=title, title_align="left", border_style=style)


def _letter(value: int) -> str:
    from ..cards import value_to_letter

    return value_to_letter(value)


def render_round(events: tuple[TraceEvent, ...], **kwargs) -> Group:
    return Group(*(render_event(event, **kwargs) for event in events))


def cipher_table(plaintext: str, keystream: list[int], ciphertext: str) -> Table:
    """The three-layer view: letters, numbers, and the sum that joins them."""
    from ..cards import letter_to_value, value_to_letter

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("label", style="dim", justify="right")
    for _ in plaintext:
        table.add_column(justify="center", width=3)

    table.add_row("plaintext", *[Text(c, style="bold") for c in plaintext])
    table.add_row("", *[str(letter_to_value(c)) for c in plaintext])
    table.add_row("keystream", *[Text(value_to_letter(k), style="bright_green") for k in keystream])
    table.add_row("", *[str(k % 26 or 26) for k in keystream])
    table.add_row("ciphertext", *[Text(c, style="bold bright_yellow") for c in ciphertext])
    return table
