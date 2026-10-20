/* The page's live bias experiment: repeatable, and it finds the bias.
 *
 * Run:  node --test tests/conformance/*.test.mjs */

import assert from "node:assert/strict";
import test from "node:test";

globalThis.requestAnimationFrame ??= (resolve) => setImmediate(resolve);
const { parseSeed, runExperiment } = await import("../../web/bias.js");

test("the same seed gives the same numbers", async () => {
  const a = await runExperiment(100, 7);
  const b = await runExperiment(100, 7);
  assert.deepEqual(a, b);
});

test("Solitaire repeats more than a uniform stream, beyond both intervals", async () => {
  const r = await runExperiment(400, 2026);
  assert.ok(r.baseline.ci_high < r.ci_low, JSON.stringify(r));
  assert.ok(r.baseline.ci_low < 1 / 26 && 1 / 26 < r.baseline.ci_high, JSON.stringify(r.baseline));
});

test("the difference interval excludes zero", async () => {
  const r = await runExperiment(400, 2026);
  assert.ok(r.excess_low > 0, JSON.stringify(r));
  assert.ok(r.excess_low <= r.excess && r.excess <= r.excess_high);
});

test("seeds are plain digits within 32 bits, never coerced", () => {
  assert.equal(parseSeed("123"), 123);
  assert.equal(parseSeed(" 0 "), 0);
  assert.equal(parseSeed("4294967295"), 4294967295);
  for (const bad of ["123abc", "12.5", "-1", "1e3", "", "4294967296", "0x10"]) {
    assert.equal(parseSeed(bad), null, bad);
  }
});
