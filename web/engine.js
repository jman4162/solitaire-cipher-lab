/* Solitaire Cipher Lab — the cipher, in JavaScript.
 *
 * This is the ONE file under web/ permitted to know how Solitaire works, and
 * it exists under protest. A second implementation of an algorithm is exactly
 * the drift risk this package was built to distrust.
 *
 * What makes it acceptable is that it does not merely compute the same answers
 * as src/solitaire_lab — it records the same *traces*. Every event carries the
 * same phase, the same affected indices and the same metadata keys as the
 * Python engine, so conformance is checked by deep equality on whole traces
 * across hundreds of generated decks in CI. If a joker lands one position off,
 * or a `wrapped` flag disagrees, the build fails.
 *
 * Mirrors: cards.py, deck.py, steps.py, keystream.py, codec.py, cipher.py,
 * keying.py. Keep the two in step; the conformance suite is what enforces it. */

const SUIT_OFFSET = { C: 0, D: 13, H: 26, S: 39 };
const RANK_VALUE = { A: 1, T: 10, J: 11, Q: 12, K: 13 };
const RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K"];
const SUITS = ["C", "D", "H", "S"];

export const JOKER_VALUE = 53;
export const DECK_SIZE = 54;

export const ORDERED_DECK = Object.freeze([
  ...SUITS.flatMap((suit) => RANKS.map((rank) => rank + suit)),
  "JA",
  "JB",
]);

export const isJoker = (code) => code === "JA" || code === "JB";

/** A card's Solitaire value: 1-52 in bridge order, 53 for either joker. */
export function cardValue(code) {
  if (isJoker(code)) return JOKER_VALUE;
  const rank = RANK_VALUE[code[0]] ?? Number(code[0]);
  return SUIT_OFFSET[code[1]] + rank;
}

/** Map a card value to a keystream letter. 27-52 wrap back round to A-Z. */
export function valueToLetter(value) {
  if (value === JOKER_VALUE) throw new Error("jokers produce no keystream letter");
  if (!(value >= 1 && value <= 52)) throw new Error(`value out of range: ${value}`);
  return String.fromCharCode(64 + (value > 26 ? value - 26 : value));
}

export const letterToValue = (letter) => letter.toUpperCase().charCodeAt(0) - 64;

/** Check that a deck is a genuine permutation of all 54 cards. */
export function validateDeck(deck) {
  if (!Array.isArray(deck) || deck.length !== DECK_SIZE) {
    throw new Error(`deck must hold ${DECK_SIZE} cards, got ${deck?.length ?? 0}`);
  }
  const seen = new Set(deck);
  const expected = new Set(ORDERED_DECK);
  const missing = [...expected].filter((c) => !seen.has(c)).sort();
  const duplicated = [...new Set(deck.filter((c, i) => deck.indexOf(c) !== i))].sort();
  const unknown = [...seen].filter((c) => !expected.has(c)).sort();
  if (missing.length || duplicated.length || unknown.length) {
    const parts = [];
    if (unknown.length) parts.push(`not a card: ${unknown.join(", ")}`);
    if (duplicated.length) parts.push(`duplicated: ${duplicated.join(", ")}`);
    if (missing.length) parts.push(`missing: ${missing.join(", ")}`);
    throw new Error(`deck is not a permutation of 54 cards (${parts.join("; ")})`);
  }
  return deck;
}

/** Parse whitespace- or comma-separated card codes into a deck. */
export function parseDeck(text) {
  const codes = text
    .replace(/,/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((token) => {
      const code = token.toUpperCase();
      if (isJoker(code)) return code;
      if (code.length !== 2 || !(code[0] in RANK_VALUE || /^[2-9]$/.test(code[0])) || !(code[1] in SUIT_OFFSET)) {
        throw new Error(`unparseable card code: ${token}`);
      }
      return code;
    });
  return validateDeck(codes);
}

function jokerIndices(deck) {
  const found = [];
  for (let i = 0; i < deck.length; i++) if (isJoker(deck[i])) found.push(i);
  if (found.length !== 2) throw new Error(`expected exactly 2 jokers, found ${found.length}`);
  return found;
}

const range = (start, stop) => Array.from({ length: Math.max(0, stop - start) }, (_, i) => start + i);

/* ---- the five steps (steps.py) ---- */

/** Move a joker down `count` positions, wrapping to just BELOW the top card. */
export function moveJokerDown(deck, joker, count) {
  const cards = deck.slice();
  const target = joker === "A" ? "JA" : "JB";
  let index = cards.indexOf(target);
  const start = index;
  let wrapped = false;
  for (let i = 0; i < count; i++) {
    if (index === cards.length - 1) {
      cards.splice(index, 1);
      cards.splice(1, 0, target);
      index = 1;
      wrapped = true;
    } else {
      [cards[index], cards[index + 1]] = [cards[index + 1], cards[index]];
      index += 1;
    }
  }
  return {
    deck: cards,
    phase: joker === "A" ? "move_joker_a" : "move_joker_b",
    affected: [index],
    meta: { joker, positions: count, from_index: start, to_index: index, wrapped },
    output: null,
  };
}

export const moveJokerA = (deck) => moveJokerDown(deck, "A", 1);
export const moveJokerB = (deck) => moveJokerDown(deck, "B", 2);

/** Swap the cards above the first joker with those below the second. */
export function tripleCut(deck) {
  const [first, second] = jokerIndices(deck);
  const top = deck.slice(0, first);
  const middle = deck.slice(first, second + 1);
  const bottom = deck.slice(second + 1);
  const newDeck = [...bottom, ...middle, ...top];
  return {
    deck: newDeck,
    phase: "triple_cut",
    affected: [...range(0, bottom.length), ...range(bottom.length + middle.length, newDeck.length)],
    meta: {
      first_joker_index: first,
      second_joker_index: second,
      top_len: top.length,
      middle_len: middle.length,
      bottom_len: bottom.length,
    },
    output: null,
  };
}

/** Cut `count` cards from the top to just above the bottom card, which stays put. */
export function countCut(deck, count) {
  const bottom = deck[deck.length - 1];
  const explicit = count !== undefined && count !== null;
  const n = explicit ? count : cardValue(bottom);
  if (!(n >= 0 && n <= JOKER_VALUE)) throw new Error(`count cut out of range: ${n}`);
  return {
    deck: [...deck.slice(n, -1), ...deck.slice(0, n), bottom],
    phase: "count_cut",
    affected: range(deck.length - 1 - n, deck.length - 1),
    meta: {
      count: n,
      bottom_card: bottom,
      from_letter: explicit,
      identity: n === 0 || n === JOKER_VALUE,
    },
    output: null,
  };
}

/** Read an output card without changing the deck. A joker means no output. */
export function outputCard(deck) {
  const top = deck[0];
  const index = cardValue(top);
  const card = deck[index];
  const joker = isJoker(card);
  return {
    deck,
    phase: "output",
    affected: [0, index],
    meta: {
      top_card: top,
      count: cardValue(top),
      output_index: index,
      output_card: card,
      is_joker: joker,
      output_value: joker ? null : cardValue(card),
      output_letter: joker ? null : valueToLetter(cardValue(card)),
    },
    output: joker ? null : card,
  };
}

/* ---- keystream (keystream.py) ---- */

function pushEvent(events, round, result) {
  const event = {
    round,
    phase: result.phase,
    after: result.deck.slice(),
    affected: result.affected,
    meta: result.meta,
  };
  if (result.output !== null && result.output !== undefined) event.output = result.output;
  events.push(event);
}

/**
 * Produce `length` keystream values from `deck`, recording a schema-1 trace.
 * A round landing on a joker produces no output and is simply run again.
 */
export function generate(deck, length, { trace = true } = {}) {
  validateDeck(deck);
  const initial = deck.slice();
  const values = [];
  const events = [];
  let current = deck;
  let round = 0;

  while (values.length < length) {
    round += 1;
    for (const step of [moveJokerA, moveJokerB, tripleCut, countCut]) {
      const result = step(current);
      current = result.deck;
      if (trace) pushEvent(events, round, result);
    }
    const result = outputCard(current);
    if (trace) pushEvent(events, round, result);
    if (result.output !== null) values.push(cardValue(result.output));
  }

  return {
    values,
    finalDeck: current,
    trace: trace ? { schema: 1, initial_deck: initial, events, output: values.slice() } : null,
  };
}

/* ---- text handling (codec.py) ---- */

export const normalize = (text) => text.toUpperCase().replace(/[^A-Z]/g, "");

export function pad(text, size = 5, character = "X") {
  const remainder = text.length % size;
  return remainder === 0 ? text : text + character.repeat(size - remainder);
}

export const group = (text, size = 5) => (text.match(new RegExp(`.{1,${size}}`, "g")) || []).join(" ");

export const addMod26 = (a, b) => ((a + b - 1) % 26) + 1;
export const subtractMod26 = (a, b) => (((a - b - 1) % 26) + 26) % 26 + 1;

/* ---- the cipher (cipher.py) ---- */

function run(message, deck, combine, doPad, trace) {
  let text = normalize(message);
  if (doPad) text = pad(text);
  const result = generate(deck, text.length, { trace });
  const out = [...text].map((ch, i) => {
    const k = result.values[i] % 26 || 26;
    return combine(ch.charCodeAt(0) - 64, k);
  });
  return {
    text: out.map((v) => String.fromCharCode(64 + v)).join(""),
    keystream: result.values,
    finalDeck: result.finalDeck,
    trace: result.trace,
  };
}

export const encrypt = (plaintext, deck, { trace = true, padMessage = true } = {}) =>
  run(plaintext, deck, addMod26, padMessage, trace);

export const decrypt = (ciphertext, deck, { trace = true } = {}) =>
  run(ciphertext, deck, subtractMod26, false, trace);

/* ---- keying (keying.py) ---- */

/** Key the deck with a passphrase: four steps per letter, then a letter-valued cut. */
export function passphraseDeck(passphrase, { deck = ORDERED_DECK, trace = true } = {}) {
  let current = validateDeck(deck.slice());
  const initial = current.slice();
  const letters = normalize(passphrase);
  if (!letters) throw new Error("passphrase must contain at least one letter A-Z");

  const events = [];
  [...letters].forEach((letter, i) => {
    const round = i + 1;
    for (const step of [moveJokerA, moveJokerB, tripleCut, countCut]) {
      const result = step(current);
      current = result.deck;
      if (trace) pushEvent(events, round, result);
    }
    const result = countCut(current, letterToValue(letter));
    current = result.deck;
    if (trace) {
      result.meta = { ...result.meta, letter };
      pushEvent(events, round, result);
    }
  });

  return {
    deck: current,
    trace: trace ? { schema: 1, initial_deck: initial, events, output: [] } : null,
  };
}

const cryptoUint32 = () => crypto.getRandomValues(new Uint32Array(1))[0];

/** A uniform integer in [0, n). Plain `% n` would favour small values whenever
 * n does not divide 2^32, so draws from the short top range are rejected. */
export function uniformIndex(n, nextUint32 = cryptoUint32) {
  const limit = 2 ** 32 - (2 ** 32 % n);
  let x;
  do x = nextUint32();
  while (x >= limit);
  return x % n;
}

/** A Fisher-Yates shuffle. The default source is crypto.getRandomValues; never
 * Math.random for a key. The bias experiment passes a seeded source instead,
 * so a run can be repeated. */
export function shuffledDeck(nextUint32 = cryptoUint32) {
  const cards = ORDERED_DECK.slice();
  for (let i = cards.length - 1; i > 0; i--) {
    const j = uniformIndex(i + 1, nextUint32);
    [cards[i], cards[j]] = [cards[j], cards[i]];
  }
  return cards;
}
