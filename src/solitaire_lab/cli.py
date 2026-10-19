"""Command line interface.

``solitaire-lab --help`` lists the subcommands.  The interesting ones are
``teach`` (walk a round at a time, with explanations) and ``worksheet`` (a
printable checklist for running the cipher by hand with a real deck).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.markup import escape

from .cards import value_to_letter
from .cipher import decrypt, encrypt
from .codec import group, normalize
from .deck import Deck, format_deck
from .keying import explicit_deck, ordered_deck, passphrase_deck, shuffled_deck
from .keystream import generate
from .render.rich_render import cipher_table, console, deck_text, render_event
from .render.svg import deck_svg, event_svg, trace_svg
from .trace.schema import to_json

__all__ = ["main", "build_parser"]

WARNING = (
    "[yellow]Solitaire is a teaching cipher with known biases. Do not use it to protect real information.[/]"
)


def add_key_options(parser: argparse.ArgumentParser) -> None:
    """The ways of choosing a starting deck, shared by most subcommands."""
    keyset = parser.add_mutually_exclusive_group()
    keyset.add_argument("-p", "--passphrase", help="key the deck with a passphrase")
    keyset.add_argument("-d", "--deck", help="54 card codes, e.g. 'AC 2C ... JA JB'")
    keyset.add_argument("--deck-file", type=Path, help="read the deck from a file")
    keyset.add_argument("--ordered-deck", action="store_true", help="the unkeyed deck, for test vectors")
    keyset.add_argument("--shuffle", type=int, metavar="SEED", help="a seeded random deck (not a real key)")


def resolve_deck(args: argparse.Namespace) -> Deck:
    # ``is not None``: an empty -p "" or -d "" is a mistake to report, not a
    # request for the unkeyed deck.
    if args.passphrase is not None:
        return passphrase_deck(args.passphrase)[0]
    if args.deck is not None:
        return explicit_deck(args.deck)
    if getattr(args, "deck_file", None):
        return explicit_deck(args.deck_file.read_text())
    if args.shuffle is not None:
        return shuffled_deck(args.shuffle)
    return ordered_deck()


def warn_if_unkeyed(args: argparse.Namespace) -> None:
    keyed = (args.passphrase, args.deck, getattr(args, "deck_file", None), args.shuffle)
    if all(key is None for key in keyed):
        console.print("[dim]Using the unkeyed deck in bridge order — this is a test fixture, not a key.[/]")


def cmd_encrypt(args: argparse.Namespace) -> int:
    warn_if_unkeyed(args)
    deck = resolve_deck(args)
    result = encrypt(args.message, deck, trace=args.show_work)
    if args.show_work:
        console.print(
            cipher_table(
                normalize(args.message).ljust(len(result.text), "X"), list(result.keystream), result.text
            )
        )
        console.print()
    console.print(f"[bold bright_yellow]{result.grouped}[/]")
    console.print(WARNING)
    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    warn_if_unkeyed(args)
    deck = resolve_deck(args)
    result = decrypt(args.message, deck)
    console.print(f"[bold]{result.grouped}[/]")
    return 0


def cmd_keystream(args: argparse.Namespace) -> int:
    warn_if_unkeyed(args)
    result = generate(resolve_deck(args), args.length)
    console.print("values : " + " ".join(str(v) for v in result.values))
    console.print("letters: " + group(result.letters))
    return 0


def cmd_deck(args: argparse.Namespace) -> int:
    deck = resolve_deck(args)
    console.print(deck_text(deck, per_line=args.per_line))
    console.print()
    console.print(f"[dim]{format_deck(deck)}[/]")
    return 0


def cmd_teach(args: argparse.Namespace) -> int:
    """Walk through rounds one step at a time, pausing between each."""
    warn_if_unkeyed(args)
    deck = resolve_deck(args)
    result = generate(deck, args.rounds, trace=True)
    console.rule("[bold]Solitaire, one step at a time")
    console.print(
        "The deck is the key and the state. Each round shuffles it in four fixed ways,\n"
        "then reads one card off the top to produce a keystream letter.\n"
    )
    console.print(deck_text(result.trace.initial_deck, per_line=args.per_line))
    console.print()
    for event in result.trace.events:
        if args.step and not _pause():
            return 0
        console.print(render_event(event, per_line=args.per_line))
    console.print()
    console.print(f"keystream: [bold bright_green]{group(result.letters)}[/]")
    console.print(WARNING)
    return 0


def _pause() -> bool:
    try:
        return input("  [enter to continue, q to quit] ").strip().lower() != "q"
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def cmd_worksheet(args: argparse.Namespace) -> int:
    """A printable checklist for running the cipher by hand with a real deck.

    The whole point of Solitaire is that a person can execute it with a physical
    deck.  This prints the deck state after every round so a learner can check
    their own hands against the machine, and find the exact round where they
    went wrong.
    """
    deck = resolve_deck(args)
    result = generate(deck, args.rounds, trace=True)
    lines = [
        "SOLITAIRE / PONTIFEX — HAND WORKSHEET",
        "=" * 72,
        "",
        "For each round: (1) joker A down 1  (2) joker B down 2  (3) triple cut",
        "(4) count cut on the bottom card  (5) read the output card.",
        "Check your deck against the line below after each round.",
        "",
        f"Start: {format_deck(result.trace.initial_deck)}",
        "",
    ]
    outputs = {e.round: e for e in result.trace.events if e.phase == "output"}
    for number in range(1, result.trace.rounds + 1):
        events = result.trace.round_events(number)
        after = events[-1].after
        out = outputs.get(number)
        if out is None or out.output is None:
            note = "no output (joker) — run this round again"
        else:
            note = f"output {out.output.code} = {out.output.value} -> {value_to_letter(out.output.value)}"
        lines += [f"Round {number:>3}: {format_deck(after)}", f"           {note}", ""]
    lines += ["", f"Keystream: {group(result.letters)}", ""]
    text = "\n".join(lines)
    if args.output:
        args.output.write_text(text)
        console.print(f"[green]wrote[/] {escape(str(args.output))}")
    else:
        print(text)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Write a trace as JSON — the format the web player consumes."""
    deck = resolve_deck(args)
    if args.message:
        result = encrypt(args.message, deck, trace=True)
        trace = result.trace
    else:
        trace = generate(deck, args.rounds, trace=True).trace
    payload = to_json(trace, indent=None if args.compact else 2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
        size = len(payload) / 1024
        console.print(
            f"[green]wrote[/] {escape(str(args.output))} ({size:.1f} KiB, {len(trace.events)} events)"
        )
    else:
        print(payload)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """Write an SVG figure: a keyed deck, one step, or whole rounds."""
    deck = resolve_deck(args)
    if args.what == "deck":
        svg = deck_svg(deck, title="Keyed deck")
    else:
        trace = generate(deck, args.rounds, trace=True).trace
        if args.what == "step":
            if not 1 <= args.step <= len(trace.events):
                raise ValueError(f"step must be between 1 and {len(trace.events)}")
            svg = event_svg(trace.events[args.step - 1], caption=not args.no_caption)
        else:
            svg = trace_svg(trace, caption=not args.no_caption)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg)
        console.print(f"[green]wrote[/] {escape(str(args.output))} ({len(svg) / 1024:.1f} KiB)")
    else:
        print(svg)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from .analysis import bias, reuse

    if args.experiment == "reuse":
        report = reuse.demonstrate(
            args.first, args.second, passphrase="SHAREDKEY" if args.passphrase is None else args.passphrase
        )
        console.print(reuse.render(report), markup=False)
    else:
        report = bias.measure(samples=args.samples, length=args.length, seed=args.seed)
        console.print(bias.render(report), markup=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2))
            console.print(f"[green]wrote[/] {escape(str(args.output))}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solitaire-lab",
        description="Teach and visualize the Solitaire (Pontifex) cipher.",
        epilog="Solitaire is for education. It has known biases and must not protect real information.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("encrypt", help="encrypt a message")
    add_key_options(p)
    p.add_argument("message")
    p.add_argument(
        "--show-work", action="store_true", help="show plaintext, keystream and ciphertext together"
    )
    p.set_defaults(func=cmd_encrypt)

    p = sub.add_parser("decrypt", help="decrypt a message")
    add_key_options(p)
    p.add_argument("message")
    p.set_defaults(func=cmd_decrypt)

    p = sub.add_parser("keystream", help="generate keystream letters")
    add_key_options(p)
    p.add_argument("-n", "--length", type=int, default=10)
    p.set_defaults(func=cmd_keystream)

    p = sub.add_parser("deck", help="show a keyed deck")
    add_key_options(p)
    p.add_argument("--per-line", type=int, default=18)
    p.set_defaults(func=cmd_deck)

    p = sub.add_parser("teach", help="walk through the algorithm one step at a time")
    add_key_options(p)
    p.add_argument("-r", "--rounds", type=int, default=2, help="keystream letters to produce")
    p.add_argument("--step", action="store_true", help="pause between steps")
    p.add_argument("--per-line", type=int, default=18)
    p.set_defaults(func=cmd_teach)

    p = sub.add_parser("worksheet", help="printable checklist for running the cipher by hand")
    add_key_options(p)
    p.add_argument("-r", "--rounds", type=int, default=10)
    p.add_argument("-o", "--output", type=Path)
    p.set_defaults(func=cmd_worksheet)

    p = sub.add_parser("export", help="write a trace as JSON for the web player")
    add_key_options(p)
    p.add_argument("-m", "--message", help="export an encryption trace instead of a bare keystream")
    p.add_argument("-r", "--rounds", type=int, default=5)
    p.add_argument("-o", "--output", type=Path)
    p.add_argument("--compact", action="store_true")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("render", help="write an SVG figure of a deck, a step, or whole rounds")
    add_key_options(p)
    p.add_argument("what", choices=["deck", "step", "rounds"], nargs="?", default="rounds")
    p.add_argument("-r", "--rounds", type=int, default=1, help="rounds to trace (keystream letters)")
    p.add_argument("-s", "--step", type=int, default=1, help="with 'step': which event, 1-based")
    p.add_argument("--no-caption", action="store_true", help="omit the explanation text")
    p.add_argument("-o", "--output", type=Path)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("analyze", help="cryptanalysis experiments")
    p.add_argument("experiment", choices=["reuse", "bias"])
    p.add_argument("--passphrase")
    p.add_argument("--first", default="ATTACKATDAWN")
    p.add_argument("--second", default="RETREATATTEN")
    p.add_argument("--samples", type=int, default=2000)
    p.add_argument("--length", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("-o", "--output", type=Path)
    p.set_defaults(func=cmd_analyze)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        console.print(f"[red]error:[/] {escape(str(exc))}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
