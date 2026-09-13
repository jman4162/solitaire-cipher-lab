"""Standalone SVG rendering of decks, steps and rounds.

Dependency-free, and driven entirely by trace events -- this module can draw
what the engine did but cannot run the cipher.  Output is a self-contained SVG
document with its own ``<style>`` block, so a figure dropped into a blog post,
a notebook or a README renders the same everywhere, and follows the viewer's
light or dark preference where the host honours ``prefers-color-scheme``.
"""

from __future__ import annotations

from collections.abc import Iterable
from xml.sax.saxutils import escape

from ..cards import Card, Suit
from ..deck import Deck
from ..trace.events import Trace, TraceEvent
from .explain import explain, headline

__all__ = ["deck_svg", "event_svg", "round_svg", "trace_svg"]

CARD_W = 30
CARD_H = 38
GAP = 4
PAD = 12
COLUMNS = 18
LABEL_H = 22
CAPTION_LINE = 15

_RED = {Suit.DIAMONDS, Suit.HEARTS}

_STYLE = """
.card{fill:var(--card,#fffefb);stroke:var(--rule,#c9cdc4);stroke-width:1}
.card.hl{fill:var(--hl,#f2ead3);stroke:var(--hl-edge,#8a6a1f);stroke-width:1.5}
.card.joker{fill:var(--joker-bg,#ece5f6);stroke:var(--joker,#6b4c9a)}
.card.joker.hl{stroke:var(--hl-edge,#8a6a1f);stroke-width:1.5}
text{font-family:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;font-size:11px;text-anchor:middle}
.black{fill:var(--black,#1e2120)}.red{fill:var(--red,#a51f14)}
.joker-text{fill:var(--joker,#6b4c9a);font-weight:700}
.label{fill:var(--ink,#16191a);font-size:12px;font-weight:600;text-anchor:start}
.label .round{fill:var(--dim,#838a89);font-weight:400}
.caption{fill:var(--dim,#53595a);font-size:11px;text-anchor:start}
.bg{fill:var(--bg,#f2f2ee)}
@media (prefers-color-scheme:dark){
 :root{--bg:#101413;--card:#181e1c;--rule:#2c3532;--hl:#332c16;--hl-edge:#d8b458;
  --joker-bg:#2c2438;--joker:#b79ae0;--black:#d4dad6;--red:#e8776b;--ink:#e6eae7;--dim:#a2aca8}
}
""".strip()


def _card_class(card: Card, highlighted: bool) -> tuple[str, str]:
    rect = "card" + (" joker" if card.is_joker else "") + (" hl" if highlighted else "")
    text = "joker-text" if card.is_joker else ("red" if card.suit in _RED else "black")
    return rect, text


def _grid_height(count: int, columns: int) -> int:
    rows = -(-count // columns)
    return rows * (CARD_H + GAP) - GAP


def _deck_body(deck: Deck, highlight: Iterable[int], *, x0: int, y0: int, columns: int) -> str:
    marked = set(highlight)
    parts = []
    for index, card in enumerate(deck):
        col, row = index % columns, index // columns
        x = x0 + col * (CARD_W + GAP)
        y = y0 + row * (CARD_H + GAP)
        rect_cls, text_cls = _card_class(card, index in marked)
        label = escape(card.short_label)
        parts.append(
            f'<rect class="{rect_cls}" x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="3"/>'
            f'<text class="{text_cls}" x="{x + CARD_W / 2:.1f}" y="{y + CARD_H / 2 + 4:.1f}">{label}</text>'
        )
    return "".join(parts)


def _wrap(text: str, width: int = 84) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def _document(width: float, height: float, body: str, *, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" '
        f'aria-label="{escape(title, {chr(34): "&quot;"})}">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style>"
        f'<rect class="bg" x="0" y="0" width="{width:.0f}" height="{height:.0f}" rx="8"/>'
        f"{body}</svg>"
    )


def deck_svg(
    deck: Deck, highlight: Iterable[int] = (), *, columns: int = COLUMNS, title: str = "Deck"
) -> str:
    """A single deck as a grid of cards, with ``highlight`` positions called out."""
    width = PAD * 2 + columns * (CARD_W + GAP) - GAP
    height = PAD * 2 + _grid_height(len(deck), columns)
    body = _deck_body(deck, highlight, x0=PAD, y0=PAD, columns=columns)
    return _document(width, height, body, title=title)


def event_svg(event: TraceEvent, *, columns: int = COLUMNS, caption: bool = True) -> str:
    """One step: its headline, the resulting deck with moved cards marked, and why."""
    width = PAD * 2 + columns * (CARD_W + GAP) - GAP
    lines = _wrap(explain(event)) if caption else []
    height = (
        PAD
        + LABEL_H
        + _grid_height(len(event.after), columns)
        + (len(lines) * CAPTION_LINE + 10 if lines else 0)
        + PAD
    )
    y = PAD + 14
    body = [
        f'<text class="label" x="{PAD}" y="{y}"><tspan class="round">Round {event.round} · </tspan>'
        f"{escape(headline(event))}</text>"
    ]
    body.append(_deck_body(event.after, event.affected, x0=PAD, y0=PAD + LABEL_H, columns=columns))
    if lines:
        cy = PAD + LABEL_H + _grid_height(len(event.after), columns) + 20
        for i, line in enumerate(lines):
            body.append(f'<text class="caption" x="{PAD}" y="{cy + i * CAPTION_LINE}">{escape(line)}</text>')
    return _document(width, height, "".join(body), title=f"Round {event.round}: {headline(event)}")


def round_svg(events: Iterable[TraceEvent], *, columns: int = COLUMNS, caption: bool = True) -> str:
    """Every step of a round stacked vertically -- the figure for a blog post."""
    events = tuple(events)
    if not events:
        raise ValueError("no events to render")
    width = PAD * 2 + columns * (CARD_W + GAP) - GAP
    panels, y = [], PAD
    for event in events:
        lines = _wrap(explain(event)) if caption else []
        grid_h = _grid_height(len(event.after), columns)
        panels.append(
            f'<text class="label" x="{PAD}" y="{y + 14}"><tspan class="round">Round {event.round} · </tspan>'
            f"{escape(headline(event))}</text>"
        )
        panels.append(_deck_body(event.after, event.affected, x0=PAD, y0=y + LABEL_H, columns=columns))
        cy = y + LABEL_H + grid_h + 20
        for i, line in enumerate(lines):
            panels.append(
                f'<text class="caption" x="{PAD}" y="{cy + i * CAPTION_LINE}">{escape(line)}</text>'
            )
        y = cy + len(lines) * CAPTION_LINE + (4 if lines else 12) + 10
    title = f"Round {events[0].round}"
    return _document(width, y + PAD - 10, "".join(panels), title=title)


def trace_svg(
    trace: Trace, *, rounds: int | None = None, columns: int = COLUMNS, caption: bool = True
) -> str:
    """The first ``rounds`` rounds of a trace (all of them by default), stacked."""
    limit = trace.rounds if rounds is None else min(rounds, trace.rounds)
    events = tuple(e for e in trace.events if e.round <= limit)
    return round_svg(events, columns=columns, caption=caption)
