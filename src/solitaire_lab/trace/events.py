"""Trace event types.

A trace is the complete, replayable account of what the engine did.  Two design
choices are worth spelling out, because both are departures from the obvious
design and both are load-bearing:

* **No explanation string.**  Wording is a rendering concern.  Keeping prose out
  of the trace keeps the JSON small and keeps translation decisions out of the
  core; renderers map a phase plus its metadata to whatever sentence they want.
* **No ``before`` deck.**  The ``before`` of event *N* is the ``after`` of event
  *N-1*.  Storing only ``after``, plus one initial deck, halves the payload and
  turns the replay check into a genuine chain: every event must follow from the
  last, not merely be self-consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..cards import Card
from ..deck import Deck

__all__ = ["TraceEvent", "Trace"]


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """One state transition: which round, which step, and the resulting deck."""

    round: int
    phase: str
    after: Deck
    affected: tuple[int, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)
    output: Card | None = None


@dataclass(frozen=True, slots=True)
class Trace:
    """An initial deck plus the events that transform it."""

    initial_deck: Deck
    events: tuple[TraceEvent, ...]
    output: tuple[int, ...] = ()

    @property
    def final_deck(self) -> Deck:
        return self.events[-1].after if self.events else self.initial_deck

    @property
    def rounds(self) -> int:
        return self.events[-1].round if self.events else 0

    def round_events(self, number: int) -> tuple[TraceEvent, ...]:
        """All events belonging to a single round."""
        return tuple(event for event in self.events if event.round == number)
