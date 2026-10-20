/* The key-reuse lesson, run by the browser engine, must match the Python one.
 *
 * web/data/reuse.json is built by solitaire_lab.analysis.reuse from two real
 * Python encryptions. The page's live version encrypts with engine.js instead,
 * so this checks that both engines agree on the reset case (the key cancels)
 * and the continued case (it does not).
 *
 * Run:  node --test tests/conformance/*.test.mjs */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import * as E from "../../web/engine.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const data = JSON.parse(readFileSync(join(ROOT, "web", "data", "reuse.json"), "utf8"));

const start = E.passphraseDeck(data.passphrase, { trace: false }).deck;
const first = E.encrypt(data.message_1, start, { trace: false, padMessage: false });
const width = data.plaintext_1.length;

test("a reset deck reproduces both Python ciphertexts", () => {
  const reset = E.encrypt(data.message_2, start, { trace: false, padMessage: false });
  assert.equal(first.text.slice(0, width), data.ciphertext_1);
  assert.equal(reset.text.slice(0, width), data.ciphertext_2);
  assert.deepEqual(reset.keystream.slice(0, width), first.keystream.slice(0, width));
});

test("continuing from the final deck matches Python's continued case", () => {
  const continued = E.encrypt(data.message_2, first.finalDeck, { trace: false, padMessage: false });
  assert.equal(continued.text.slice(0, width), data.continued.ciphertext_2);
  assert.equal(continued.keystream.slice(0, width).map(E.valueToLetter).join(""), data.continued.keystream);
  assert.equal(data.continued.key_cancelled, false);
});
