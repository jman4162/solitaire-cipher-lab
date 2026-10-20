/* The browser shuffle must be uniform, not merely random.
 *
 * Run:  node --test tests/conformance/*.test.mjs */

import assert from "node:assert/strict";
import test from "node:test";

import * as E from "../../web/engine.js";

test("uniformIndex rejects draws from the short top range", () => {
  // 2^32 % 54 = 4, so the top four values would favour indices 0-3 under plain %.
  const draws = [2 ** 32 - 1, 2 ** 32 - 4, 7];
  assert.equal(E.uniformIndex(54, () => draws.shift()), 7);
  assert.equal(draws.length, 0);
});

test("a seeded shuffle is a valid deck and repeats exactly", () => {
  const source = (seed) => () => (seed = (Math.imul(seed, 1103515245) + 12345) >>> 0);
  const a = E.shuffledDeck(source(42));
  const b = E.shuffledDeck(source(42));
  E.validateDeck(a);
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, E.ORDERED_DECK);
});
