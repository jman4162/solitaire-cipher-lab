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

Sections 1-3 replay trace files recorded by the Python engine, so they cannot
show anything the implementation does not do. Section 4 runs the cipher live in
the browser, which needs a second implementation — see below for how that is
kept honest. `player.js` still contains no cipher code at all; a test enforces
it, and another asserts the committed traces match a fresh build.

```sh
python scripts/build_web.py     # regenerate the page's data from the engine
python -m http.server -d web    # then open http://localhost:8000
```

## The JavaScript engine, and why it is allowed to exist

Letting readers encrypt their own messages means shipping a second
implementation of Solitaire — precisely the drift this package was built to
distrust. `web/engine.js` is tolerated because it is not checked against
ciphertexts. It is checked against **traces**:

```sh
python scripts/gen_conformance.py            # 517 cases from the Python engine
node --test tests/conformance/*.test.mjs     # every trace must deep-equal
```

Every event, every `affected` index and every metadata key must match what
Python recorded, across 300 random decks, 100 passphrase keyings, 100
encryptions, the published vectors and 13 decks that put the jokers exactly
where implementations go wrong. A joker landing one position off fails the
build — and so does a single wrong metadata flag on an otherwise correct
keystream, which is the point of comparing traces rather than outputs.
`tests/test_conformance_harness.py` proves the net has no holes by mutating the
engine four ways and asserting the suite goes red each time.

The full vector set (~24 MB) is generated in CI, not committed;
`tests/conformance/smoke.json` holds 28 cases so `node --test` runs offline.

Cipher knowledge is confined to `engine.js` by an architecture test. The one
other duplication is wording: `web/explain.js` mirrors
`solitaire_lab.render.explain` for traces made in the browser, and
`tests/test_js_explain.py` renders the same events through both and fails if a
single character differs.

## Status

| | |
|---|---|
| Engine (cards, deck, five steps, keystream, cipher, keying) | ✅ |
| Structured traces + JSON wire format + replay invariant | ✅ |
| Terminal visualizer and CLI (`teach`, `worksheet`, `export`) | ✅ |
| Cryptanalysis lab (key reuse, keystream bias) | ✅ |
| Interactive web explainer | ✅ |
| Standalone SVG renderer for static figures (`solitaire-lab render`) | ✅ |
| Test suite — known-answer, property, CLI, architecture, page data (392 tests) | ✅ |
| Live "encrypt your own message" in the browser | ✅ |
| JS engine conformance against Python traces (517 cases) | ✅ |

## Command line

```sh
solitaire-lab teach --ordered-deck --step        # walk a round at a time
solitaire-lab encrypt -p "CRYPTONOMICON" "DO NOT USE PC" --show-work
solitaire-lab worksheet -p "SECRET" -r 20        # printable hand-execution sheet
solitaire-lab analyze reuse                      # watch the key cancel out
solitaire-lab analyze bias --samples 5000        # measure the keystream bias
solitaire-lab export -p "SECRET" -m "HELLO" -o trace.json
solitaire-lab render rounds --ordered-deck -r 2 -o figure.svg   # a blog-ready figure
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
  3.85% of the time. Measured over 373,500 adjacent pairs from 1,500 shuffled
  decks, Solitaire repeats 4.46% of the time, a repeat roughly every 22.4
  letters instead of every 26.
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
