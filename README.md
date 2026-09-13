# Solitaire Cipher Lab

Teach and visualize the **Solitaire (Pontifex)** cipher — Bruce Schneier's 1999
hand cipher, designed to be executed with an ordinary deck of 54 playing cards.

> ⚠️ **For education and experimentation, not modern cryptographic security.**
> Solitaire has known statistical biases and must not be used to protect real
> information.

## Why this exists

Most cipher implementations hand you `encrypt()` and `decrypt()` and keep the
interesting part hidden. Solitaire deserves better treatment, because its
internal state *is* a deck of cards — something a learner can hold, shuffle and
watch evolve. A stream cipher stops being a black box.

So this package treats the **execution trace as its primary product**. Every
operation reports what it did in structured form, and every renderer is driven
by those reports rather than reimplementing the algorithm. A diagram cannot
drift out of step with the code that produced it.

```python
from solitaire_lab import ORDERED_DECK, encrypt, replay

result = encrypt("DO NOT USE PC", ORDERED_DECK, trace=True)
result.text  # ciphertext
result.keystream  # the card values behind it
result.final_deck  # where the deck ended up
result.trace.events  # every state transition, replayable

# A trace is an executable proof of what the engine did:
replay(result.trace.initial_deck, result.trace.events) == result.final_deck
```

There is no hidden cipher object: the starting deck is an explicit input and the
final deck an explicit output, so a second call can never silently depend on a
first.

## The interactive explainer

The headline output is a single page — prose interleaved with live widgets —
that walks through the cipher and ends by demonstrating two of its weaknesses.
It lives in [`web/`](web/) and deploys to GitHub Pages.

The page contains **no cipher code**. It replays trace files recorded by the
engine, which is what guarantees it shows what the implementation actually does
rather than an idealised retelling. A test asserts `player.js` cannot run
Solitaire, and another asserts the committed traces still match a fresh build.

```sh
python scripts/build_web.py     # regenerate the page's data from the engine
python -m http.server -d web    # then open http://localhost:8000
```

## Status

| | |
|---|---|
| Engine (cards, deck, five steps, keystream, cipher, keying) | ✅ |
| Structured traces + JSON wire format + replay invariant | ✅ |
| Terminal visualizer and CLI (`teach`, `worksheet`, `export`) | ✅ |
| Cryptanalysis lab (key reuse, keystream bias) | ✅ |
| Interactive web explainer | ✅ |
| Test suite — known-answer, property, CLI, page data (352 tests) | ✅ |
| Standalone SVG renderer for static figures | planned |
| Live "encrypt your own message" in the browser | planned |

## Command line

```sh
solitaire-lab teach --ordered-deck --step        # walk a round at a time
solitaire-lab encrypt -p "CRYPTONOMICON" "DO NOT USE PC" --show-work
solitaire-lab worksheet -p "SECRET" -r 20        # printable hand-execution sheet
solitaire-lab analyze reuse                      # watch the key cancel out
solitaire-lab analyze bias --samples 5000        # measure the keystream bias
solitaire-lab export -p "SECRET" -m "HELLO" -o trace.json
```

`worksheet` is the one to use with a real deck. It prints the deck state after
every round, so when your physical shuffle drifts from the machine's you can
find the exact round where it happened.

## What the analysis shows

Solitaire is presented here as a route into *why* modern stream ciphers are
built as they are, not as a curiosity that happens to work.

- **Key reuse.** `C1 - C2 = (P1 + K) - (P2 + K) = P1 - P2`. The demonstration
  runs two real messages through one deck and shows the keystream cancelling.
- **Keystream bias.** An ideal 26-letter stream repeats the previous letter
  3.85% of the time. Measured over ~900,000 adjacent pairs, Solitaire repeats
  4.45% of the time — a repeat roughly every 22.5 letters instead of every 26.
  The bias was identified by Paul Crowley in 1999 and analysed by Daniel Shiu
  in 2019.

## Verification

The correctness story is **known-answer tests**, not round trips — a broken
implementation decrypts its own incorrectly-generated ciphertext perfectly well.
The engine reproduces the published vectors exactly:

| Keying | Plaintext | Ciphertext |
|---|---|---|
| unkeyed (bridge order) | `AAAAAAAAAAAAAAA` | `EXKYIZSGEHUNTIQ` |
| passphrase `FOO` | `AAAAAAAAAAAAAAA` | `ITHZUJIWGRFARMW` |
| passphrase `CRYPTONOMICON` | `SOLITAIRE` | `KIRAKSFJAN` |

Round trips are deliberately *not* the correctness story, and the joker-skip
round, both joker wrap cases and the joker-on-bottom count-cut identity are each
tested directly.

The unkeyed keystream is `4 49 10 (53) 24 8 51 44 6 4 33 20 39 19 34 42` — the
parenthesised 53 is a round that lands on a joker and produces no output. That
skip is the most commonly mis-implemented part of Solitaire, and it is invisible
to any encrypt-then-decrypt test, so it is tested directly.

Vectors are pinned in [`tests/vectors/published.json`](tests/vectors/published.json).

## Development

```sh
uv venv && uv pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

## License

MIT. The Solitaire algorithm itself was published freely by Bruce Schneier;
see <https://www.schneier.com/academic/solitaire/>.
