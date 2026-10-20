/* Section 06: measure the repeat-letter bias in the browser.
 *
 * The keystream comes from engine.js (checked against Python in CI); this file
 * only shuffles decks from a seeded source, counts adjacent repeated letters,
 * and draws the numbers. A baseline stream of letters drawn uniformly from the
 * same seeded pseudorandom generator is counted the same way, so the reader sees
 * what 1 in 26 looks like with sampling noise, side by side with Solitaire.
 *
 * Pairs inside one keystream are not independent, so every 95% interval is a
 * bootstrap over decks, as in solitaire_lab.analysis.bias. The headline number
 * is the difference between the two rates, resampled in pairs (deck i of each
 * run together), since that is the question: how much more often does
 * Solitaire repeat? */

import * as E from "./engine.js";

const LENGTH = 250;
const RESAMPLES = 1000;
const CHUNK = 50;
const IDEAL = 1 / 26;

const $ = (id) => document.getElementById(id);

/** mulberry32: a small seeded generator, so a run can be repeated exactly.
 * Fine for sampling decks; never for keying one. */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return (t ^ (t >>> 14)) >>> 0;
  };
}

const repeats = (letters) => {
  let n = 0;
  for (let i = 1; i < letters.length; i++) if (letters[i] === letters[i - 1]) n++;
  return n;
};

function interval(perDeck, next) {
  const n = perDeck.length;
  const pairs = n * (LENGTH - 1);
  const rates = [];
  for (let r = 0; r < RESAMPLES; r++) {
    let sum = 0;
    for (let i = 0; i < n; i++) sum += perDeck[E.uniformIndex(n, next)];
    rates.push(sum / pairs);
  }
  rates.sort((a, b) => a - b);
  return [rates[Math.floor(0.025 * RESAMPLES)], rates[Math.floor(0.975 * RESAMPLES) - 1]];
}

/** The Solitaire rate minus the baseline rate, with a paired deck bootstrap. */
function difference(solitaire, baseline, next) {
  const n = solitaire.length;
  const pairs = n * (LENGTH - 1);
  const diffs = [];
  for (let r = 0; r < RESAMPLES; r++) {
    let sum = 0;
    for (let i = 0; i < n; i++) {
      const j = E.uniformIndex(n, next);
      sum += solitaire[j] - baseline[j];
    }
    diffs.push(sum / pairs);
  }
  diffs.sort((a, b) => a - b);
  const total = solitaire.reduce((a, b) => a + b, 0) - baseline.reduce((a, b) => a + b, 0);
  return [total / pairs, diffs[Math.floor(0.025 * RESAMPLES)], diffs[Math.floor(0.975 * RESAMPLES) - 1]];
}

/** Seeds are whole numbers from 0 to 2^32 - 1, written as plain digits. Anything
 * else is refused rather than quietly coerced, so a shared seed means one run. */
export function parseSeed(text) {
  const t = String(text).trim();
  if (!/^\d+$/.test(t)) return null;
  const seed = Number(t);
  return seed <= 0xffffffff ? seed : null;
}

function summarize(perDeck, next) {
  const pairs = perDeck.length * (LENGTH - 1);
  const total = perDeck.reduce((a, b) => a + b, 0);
  const [lo, hi] = interval(perDeck, next);
  return { observed_rate: total / pairs, ci_low: lo, ci_high: hi, pairs_examined: pairs };
}

/** Run `decks` shuffled decks from `seed`, yielding to the page between chunks. */
export async function runExperiment(decks, seed, onProgress = () => {}) {
  const next = mulberry32(seed);
  const solitaire = [];
  const uniform = [];
  for (let i = 0; i < decks; i++) {
    const deck = E.shuffledDeck(next);
    const values = E.generate(deck, LENGTH, { trace: false }).values;
    solitaire.push(repeats(values.map(E.valueToLetter)));
    uniform.push(repeats(Array.from({ length: LENGTH }, () => E.uniformIndex(26, next))));
    if ((i + 1) % CHUNK === 0) {
      onProgress(i + 1);
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
  }
  const sol = summarize(solitaire, next);
  const baseline = summarize(uniform, next);
  const [excess, lo, hi] = difference(solitaire, uniform, next);
  return {
    ...sol,
    samples: decks,
    seed,
    ideal_rate: IDEAL,
    excess_ratio: sol.observed_rate / IDEAL,
    baseline,
    excess,
    excess_low: lo,
    excess_high: hi,
  };
}

const pct = (x) => (x * 100).toFixed(2) + "%";
const points = (x) => (x >= 0 ? "+" : "") + (x * 100).toFixed(2);

/** Draw a result: the recorded one from bias.json, or a live one. */
export function drawBias(d, { live = false } = {}) {
  $("bias-stats").innerHTML = `
    <div class="stat"><div class="n">${pct(d.ideal_rate)}</div><div class="l">ideal repeat rate (1 in 26)</div></div>
    <div class="stat"><div class="n warnish">${pct(d.observed_rate)}</div><div class="l">Solitaire, 95% interval ${pct(d.ci_low)} to ${pct(d.ci_high)}</div></div>
    <div class="stat"><div class="n warnish">${points(d.excess)} pts</div><div class="l">more repeats than ${d.baseline ? "the baseline run" : "1 in 26"}, 95% interval ${points(d.excess_low)} to ${points(d.excess_high)}</div></div>`;
  const rows = [["ideal stream", IDEAL, "ideal", ""]];
  if (d.baseline) rows.push(["uniform random", d.baseline.observed_rate, "ideal", `${pct(d.baseline.ci_low)} to ${pct(d.baseline.ci_high)}`]);
  rows.push(["Solitaire", d.observed_rate, "actual", `${pct(d.ci_low)} to ${pct(d.ci_high)}`]);
  const scale = Math.max(...rows.map((r) => r[1]), d.ci_high) * 1.2;
  $("bias-bars").innerHTML = rows
    .map(
      ([label, value, cls, range]) => `
    <div class="bar-row">
      <span class="bar-label">${label}</span>
      <span class="bar-track"><span class="bar-fill ${cls}" style="width:${(value / scale) * 100}%"></span></span>
      <span class="val">${pct(value)}${range ? `<span class="range"> (${range})</span>` : ""}</span>
    </div>`
    )
    .join("");
  $("bias-detail").textContent = live
    ? `Your run: ${d.samples.toLocaleString()} decks from seed ${d.seed}, ${d.pairs_examined.toLocaleString()} adjacent pairs, ` +
      `a repeat roughly every ${(1 / d.observed_rate).toFixed(1)} letters instead of every 26. ` +
      `The uniform row is ${d.samples.toLocaleString()} streams of letters drawn uniformly by the same seeded pseudorandom generator, counted the same way. ` +
      `Solitaire repeats ${d.excess_ratio.toFixed(2)} times as often as 1 in 26.`
    : `Recorded by the Python package: ${d.samples.toLocaleString()} randomly shuffled decks, ${d.pairs_examined.toLocaleString()} adjacent pairs, ` +
      `a repeat roughly every ${(1 / d.observed_rate).toFixed(1)} letters instead of every 26, ${d.excess_ratio.toFixed(2)} times as often. Run your own below.`;
}

export function initBias(recorded) {
  drawBias(recorded);
  const seedBox = $("bias-seed");
  seedBox.value = String(E.uniformIndex(1_000_000));
  $("bias-run").addEventListener("click", async (e) => {
    const decks = Number($("bias-decks").value);
    const seed = parseSeed(seedBox.value);
    if (seed === null) {
      $("bias-status").textContent = "The seed must be a whole number from 0 to 4294967295, digits only.";
      return;
    }
    seedBox.value = String(seed);
    e.target.disabled = true;
    const result = await runExperiment(decks, seed, (done) => {
      $("bias-status").textContent = `Running: ${done.toLocaleString()} of ${decks.toLocaleString()} decks`;
    });
    drawBias(result, { live: true });
    $("bias-status").textContent = `Done. Run seed ${seed} again and you get the same numbers.`;
    e.target.disabled = false;
  });
}
