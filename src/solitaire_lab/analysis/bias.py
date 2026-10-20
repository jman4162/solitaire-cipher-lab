"""Measuring a known statistical weakness in Solitaire's keystream.

An ideal keystream over 26 letters would repeat a letter — that is, produce the
same letter twice in a row — with probability 1/26, about 3.85%.  Solitaire's
does so noticeably more often.  The bias was identified early (Paul Crowley,
1999) and analysed in detail by Daniel Shiu (2019).

The point of measuring it here is not to declare Solitaire broken and stop.  It
is that "looks random" and "is random" are different claims, and the gap between
them is what cryptanalysis is *for*.  A cipher can be perfectly usable by hand,
entirely deterministic, and still leak — and the leak shows up as a
number a learner can compute themselves in a few seconds.
"""

from __future__ import annotations

import random
from typing import Any

from ..cards import value_to_letter
from ..deck import ORDERED_DECK, validate_deck
from ..keystream import generate_fast

__all__ = ["measure", "render", "IDEAL_REPEAT_RATE"]

IDEAL_REPEAT_RATE = 1 / 26


BOOTSTRAP_RESAMPLES = 1000


def measure(*, samples: int = 2000, length: int = 200, seed: int = 0) -> dict[str, Any]:
    """Sample many keystreams and count adjacent repeated letters.

    Uses the non-traced fast path: a run of this size is several times quicker
    that way, and never allocates the millions of trace events that a fully
    traced run of the same length would.

    Adjacent pairs within one keystream are not independent, so the 95%
    interval is a bootstrap over decks: resample whole decks with replacement
    and recompute the rate.
    """
    rng = random.Random(seed)
    repeats = 0
    pairs = 0
    per_deck: list[int] = []
    letter_counts = dict.fromkeys((chr(ord("A") + i) for i in range(26)), 0)

    for _ in range(samples):
        cards = list(ORDERED_DECK)
        rng.shuffle(cards)
        values = generate_fast(validate_deck(cards), length)
        letters = [value_to_letter(v) for v in values]
        for letter in letters:
            letter_counts[letter] += 1
        deck_repeats = sum(a == b for a, b in zip(letters, letters[1:], strict=False))
        per_deck.append(deck_repeats)
        repeats += deck_repeats
        pairs += len(letters) - 1

    observed = repeats / pairs if pairs else 0.0
    ci_low, ci_high = _bootstrap_interval(per_deck, length - 1, seed)
    total_letters = sum(letter_counts.values())
    return {
        "samples": samples,
        "length": length,
        "seed": seed,
        "pairs_examined": pairs,
        "repeats_observed": repeats,
        "observed_rate": observed,
        "ideal_rate": IDEAL_REPEAT_RATE,
        "excess_ratio": observed / IDEAL_REPEAT_RATE if IDEAL_REPEAT_RATE else 0.0,
        "ci_level": 0.95,
        "ci_low": ci_low,
        "ci_high": ci_high,
        # The ideal rate is a fixed 1/26, so the excess interval is the rate
        # interval shifted by it: how many points more often Solitaire repeats.
        "excess": observed - IDEAL_REPEAT_RATE,
        "excess_low": ci_low - IDEAL_REPEAT_RATE,
        "excess_high": ci_high - IDEAL_REPEAT_RATE,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "letter_frequencies": {k: v / total_letters for k, v in letter_counts.items()}
        if total_letters
        else {},
    }


def _bootstrap_interval(per_deck: list[int], pairs_per_deck: int, seed: int) -> tuple[float, float]:
    """A 95% percentile interval for the repeat rate, resampling decks."""
    if not per_deck or pairs_per_deck <= 0:
        return 0.0, 0.0
    rng = random.Random(f"bootstrap-{seed}")
    n = len(per_deck)
    rates = sorted(sum(rng.choices(per_deck, k=n)) / (n * pairs_per_deck) for _ in range(BOOTSTRAP_RESAMPLES))
    return rates[int(0.025 * BOOTSTRAP_RESAMPLES)], rates[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]


def render(report: dict[str, Any]) -> str:
    """A terminal-friendly write-up of the measured bias."""
    observed = report["observed_rate"]
    ideal = report["ideal_rate"]
    lines = [
        "Keystream bias: repeated letters",
        "=" * 52,
        "",
        f"Sampled {report['samples']:,} random decks, {report['length']} letters each.",
        f"Examined {report['pairs_examined']:,} adjacent pairs.",
        "",
        f"  an ideal 26-letter stream repeats   {ideal:.4%}",
        f"  Solitaire's keystream repeats       {observed:.4%}",
        f"  95% interval (bootstrap over decks) {report['ci_low']:.4%} to {report['ci_high']:.4%}",
        f"  excess over 1/26                    {report['excess'] * 100:+.3f} points "
        f"({report['excess_low'] * 100:+.3f} to {report['excess_high'] * 100:+.3f})",
        f"  excess                              {report['excess_ratio']:.2f}x",
        "",
        "A stream cipher is supposed to be computationally indistinguishable",
        "from random. This one is distinguishable with nothing more than a",
        "counter, so 'its letters look scrambled' is no security argument.",
        "Telling the stream apart from random is a weaker result than reading a",
        "given short message, but it is the property a stream cipher promises.",
        "Modern stream ciphers are designed and analysed so that no test that",
        "can feasibly be run separates their output from random.",
    ]
    return "\n".join(lines)
