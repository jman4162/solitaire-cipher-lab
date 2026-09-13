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

## Status

Early development. The engine and trace layer are complete and verified against
published test vectors; renderers, CLI and the interactive explainer are in
progress.

| | |
|---|---|
| Engine (cards, deck, five steps, keystream, cipher, keying) | ✅ |
| Structured traces + JSON wire format + replay invariant | ✅ |
| Known-answer + property test suite (304 tests) | ✅ |
| Terminal visualizer and CLI | in progress |
| SVG renderer | planned |
| Cryptanalysis lab (key reuse, keystream bias) | planned |
| Interactive web explainer | planned |

## Verification

The correctness story is **known-answer tests**, not round trips — a broken
implementation decrypts its own incorrectly-generated ciphertext perfectly well.
The engine reproduces the published vectors exactly:

| Keying | Plaintext | Ciphertext |
|---|---|---|
| unkeyed (bridge order) | `AAAAAAAAAAAAAAA` | `EXKYIZSGEHUNTIQ` |
| passphrase `FOO` | `AAAAAAAAAAAAAAA` | `ITHZUJIWGRFARMW` |
| passphrase `CRYPTONOMICON` | `SOLITAIRE` | `KIRAKSFJAN` |

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
