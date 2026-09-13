/* Conformance: the JavaScript engine must reproduce the Python engine's traces.
 *
 * Not its ciphertexts — its traces. Deep equality on the whole schema-1
 * document, event for event, including affected indices and every metadata
 * key. That is a much tighter net than comparing outputs: a joker landing one
 * position off still produces a plausible-looking keystream, but it cannot
 * produce the same trace.
 *
 * Run:  node --test tests/conformance/*.test.mjs
 *
 * Uses tests/conformance/vectors.json when present (generated in CI by
 * scripts/gen_conformance.py), otherwise the committed smoke.json, so this
 * suite runs offline with no Python step. */

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import * as E from "../../web/engine.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const FULL = join(HERE, "vectors.json");
const SMOKE = join(HERE, "smoke.json");
const SOURCE = existsSync(FULL) ? FULL : SMOKE;
const { cases } = JSON.parse(readFileSync(SOURCE, "utf8"));

console.log(`conformance: ${cases.length} cases from ${SOURCE.endsWith("vectors.json") ? "full set" : "smoke set"}`);

/** Report the first divergence precisely, rather than dumping two 54-card decks. */
function assertTraceEqual(actual, expected, label) {
  assert.equal(actual.schema, expected.schema, `${label}: schema version`);
  assert.deepStrictEqual(actual.initial_deck, expected.initial_deck, `${label}: initial deck`);
  assert.equal(actual.events.length, expected.events.length, `${label}: event count`);

  for (let i = 0; i < expected.events.length; i++) {
    const a = actual.events[i];
    const b = expected.events[i];
    const where = `${label}: event ${i} (round ${b.round}, ${b.phase})`;
    assert.equal(a.phase, b.phase, `${where}: phase`);
    assert.equal(a.round, b.round, `${where}: round`);
    assert.deepStrictEqual(a.affected, b.affected, `${where}: affected indices`);
    for (const key of Object.keys(b.meta)) {
      assert.deepStrictEqual(a.meta[key], b.meta[key], `${where}: meta.${key}`);
    }
    assert.deepStrictEqual(
      Object.keys(a.meta).sort(),
      Object.keys(b.meta).sort(),
      `${where}: metadata keys must match exactly`,
    );
    assert.deepStrictEqual(a.after, b.after, `${where}: resulting deck`);
    assert.equal(a.output ?? null, b.output ?? null, `${where}: output card`);
  }
  assert.deepStrictEqual(actual.output, expected.output, `${label}: keystream output`);
  assert.deepStrictEqual(actual, expected, `${label}: whole trace`);
}

const by = (kind) => cases.filter((c) => c.kind === kind);

test("keystream traces match Python event for event", () => {
  const group = by("keystream");
  assert.ok(group.length > 0, "no keystream cases");
  for (const c of group) {
    const result = E.generate(c.deck, c.length);
    assert.deepStrictEqual(result.values, c.values, `${c.name}: keystream values`);
    assertTraceEqual(result.trace, c.trace, c.name);
  }
});

test("passphrase keying matches Python, deck and trace", () => {
  const group = by("keying");
  assert.ok(group.length > 0, "no keying cases");
  for (const c of group) {
    const result = E.passphraseDeck(c.passphrase);
    assert.deepStrictEqual(result.deck, c.deck, `${c.name}: keyed deck`);
    assertTraceEqual(result.trace, c.trace, c.name);
  }
});

test("encryption matches Python, ciphertext, keystream and trace", () => {
  const group = by("encrypt");
  assert.ok(group.length > 0, "no encryption cases");
  for (const c of group) {
    const result = E.encrypt(c.plaintext, c.deck);
    assert.equal(result.text, c.ciphertext, `${c.name}: ciphertext`);
    assert.deepStrictEqual(result.keystream, c.keystream, `${c.name}: keystream`);
    assertTraceEqual(result.trace, c.trace, c.name);
  }
});

test("decryption reverses encryption", () => {
  for (const c of by("encrypt")) {
    const back = E.decrypt(c.ciphertext, c.deck, { trace: false });
    assert.equal(back.text, E.pad(E.normalize(c.plaintext)), `${c.name}: round trip`);
  }
});

test("published vectors reproduce from the JavaScript engine alone", () => {
  const group = by("published");
  assert.ok(group.length >= 3, "expected the three published message vectors");
  for (const c of group) {
    assert.equal(E.encrypt(c.plaintext, c.deck, { trace: false }).text, c.ciphertext, c.name);
  }
  for (const c of by("published-keystream")) {
    const result = E.generate(c.deck, c.length, { trace: false });
    assert.deepStrictEqual(result.values, c.values, `${c.name}: values`);
    assert.equal(result.values.map(E.valueToLetter).join(""), c.letters, `${c.name}: letters`);
  }
});

test("edge decks are covered", () => {
  const edges = by("keystream").filter((c) => c.name.startsWith("edge:"));
  assert.ok(edges.length >= 12, `expected joker edge cases, found ${edges.length}`);
});

/* ---- behaviour the vectors cannot express ---- */

test("validateDeck rejects malformed decks with a useful message", () => {
  assert.throws(() => E.validateDeck(E.ORDERED_DECK.slice(0, 53)), /must hold 54 cards/);
  const dup = E.ORDERED_DECK.slice();
  dup[5] = dup[4];
  assert.throws(() => E.validateDeck(dup), /duplicated: 5C/);
  assert.throws(() => E.validateDeck(dup), /missing: 6C/);
});

test("parseDeck round-trips and rejects junk", () => {
  assert.deepStrictEqual(E.parseDeck(E.ORDERED_DECK.join(" ")), [...E.ORDERED_DECK]);
  assert.deepStrictEqual(E.parseDeck(E.ORDERED_DECK.join(",\n").toLowerCase()), [...E.ORDERED_DECK]);
  assert.throws(() => E.parseDeck("AC 2C ZZ"), /unparseable card code: ZZ/);
});

test("card values follow bridge order", () => {
  assert.equal(E.cardValue("AC"), 1);
  assert.equal(E.cardValue("KC"), 13);
  assert.equal(E.cardValue("AD"), 14);
  assert.equal(E.cardValue("AH"), 27);
  assert.equal(E.cardValue("KS"), 52);
  assert.equal(E.cardValue("JA"), 53);
  assert.equal(E.cardValue("JB"), 53);
});

test("values above 26 wrap to a letter", () => {
  assert.equal(E.valueToLetter(1), "A");
  assert.equal(E.valueToLetter(26), "Z");
  assert.equal(E.valueToLetter(27), "A");
  assert.equal(E.valueToLetter(52), "Z");
  assert.throws(() => E.valueToLetter(53), /no keystream letter/);
});

test("jokers never appear in a keystream", () => {
  const values = E.generate(E.ORDERED_DECK, 300, { trace: false }).values;
  assert.ok(values.every((v) => v >= 1 && v <= 52), "a joker leaked into the keystream");
});

test("shuffledDeck produces valid, differing decks", () => {
  const a = E.shuffledDeck();
  const b = E.shuffledDeck();
  E.validateDeck(a);
  E.validateDeck(b);
  assert.notDeepStrictEqual(a, b, "two shuffles produced identical decks");
});

test("an empty passphrase is rejected", () => {
  assert.throws(() => E.passphraseDeck("   "), /at least one letter/);
});
