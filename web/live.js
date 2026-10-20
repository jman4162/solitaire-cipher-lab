/* The "Try it" section: encrypt your own message, in the browser.
 *
 * Everything the cipher does comes from engine.js; everything the reader sees
 * is drawn by player.js. This file is the wiring between them: a form, some
 * validation, and the second-message comparison that is the whole reason live
 * execution is worth a second implementation. */

import * as E from "./engine.js";
import { withExplanations } from "./explain.js";
import { TracePlayer, renderDeck } from "./player.js";

const $ = (id) => document.getElementById(id);

const state = { deck: null, deckSource: "", first: null, player: null };

// A full trace keeps five 54-card snapshots per letter and the table draws a
// cell per letter, so the page caps what it traces. The CLI has no cap.
const MAX_LETTERS = 250;

/* ---- key selection ---- */

function currentDeck() {
  const mode = document.querySelector('input[name="keymode"]:checked').value;
  if (mode === "passphrase") {
    const phrase = $("live-passphrase").value;
    if (!E.normalize(phrase)) throw new Error("Enter a passphrase. Letters only; everything else is ignored.");
    state.deckSource = `passphrase "${E.normalize(phrase)}"`;
    return E.passphraseDeck(phrase, { trace: false }).deck;
  }
  if (mode === "paste") {
    state.deckSource = "a deck you pasted";
    return E.parseDeck($("live-deck").value);
  }
  if (!state.shuffled) throw new Error("Click Shuffle to deal a deck first.");
  state.deckSource = "a randomly shuffled deck";
  return state.shuffled;
}

function syncKeyMode() {
  const mode = document.querySelector('input[name="keymode"]:checked').value;
  for (const [id, want] of [["key-passphrase", "passphrase"], ["key-shuffle", "shuffle"], ["key-paste", "paste"]]) {
    $(id).hidden = mode !== want;
  }
}

function showDeck(deck) {
  renderDeck($("live-deck-preview"), deck, []);
  $("live-deck-preview").hidden = false;
}

/* ---- running it ---- */

function layersTable(plaintext, keystream, ciphertext) {
  const rows = [
    ["plaintext", [...plaintext], "p"],
    ["", [...plaintext].map((c) => c.charCodeAt(0) - 64), "v"],
    ["keystream", keystream.map((k) => E.valueToLetter(k)), "k"],
    ["", keystream.map((k) => k % 26 || 26), "v"],
    ["ciphertext", [...ciphertext], "c"],
  ];
  const table = document.createElement("table");
  table.className = "layers";
  rows.forEach(([label, cells, cls], i) => {
    const tr = table.insertRow();
    if (i === 4) tr.className = "sum";
    const th = document.createElement("th");
    th.textContent = label;
    tr.appendChild(th);
    for (const value of cells) {
      const td = tr.insertCell();
      td.className = cls;
      td.textContent = value;
    }
  });
  return table;
}

function fail(message) {
  const box = $("live-error");
  box.textContent = message;
  box.hidden = false;
}

function run() {
  $("live-error").hidden = true;
  let deck;
  try {
    deck = currentDeck();
  } catch (err) {
    return fail(err.message);
  }
  const message = $("live-message").value;
  if (!E.normalize(message)) return fail("Enter a message. Letters only; everything else is ignored.");
  if (E.normalize(message).length > MAX_LETTERS) {
    return fail(`This page traces up to ${MAX_LETTERS} letters. For longer text, use solitaire-lab encrypt.`);
  }

  state.deck = deck;
  showDeck(deck);

  const result = E.encrypt(message, deck);
  state.first = {
    plaintext: E.pad(E.normalize(message)),
    ciphertext: result.text,
    keystream: result.keystream,
    startDeck: deck,
    finalDeck: result.finalDeck,
  };

  $("live-layers").replaceChildren(layersTable(state.first.plaintext, result.keystream, result.text));
  $("live-cipher").textContent = E.group(result.text);
  $("live-summary").textContent =
    `${result.text.length} letters, keyed with ${state.deckSource}. ` +
    `Padded with X to a whole number of five-letter groups.`;
  $("live-results").hidden = false;

  // A fresh player over the reader's own trace. Explanations come from
  // explain.js because this trace did not exist at build time.
  state.player?.destroy();
  state.player = new TracePlayer($("live-player"), withExplanations(result.trace));
  $("live-player-wrap").hidden = false;
  $("live-reuse-wrap").hidden = false;
  $("live-reuse-out").hidden = true;
}

/** The payoff: a second message, from the reset deck or from where the deck ended.
 *
 * Both cases run the real cipher. Reset and the keystream cancels in C1 - C2;
 * continue and it does not. */
function runReuse() {
  const second = $("live-second").value;
  if (!state.first) return;
  $("live-error").hidden = true;
  if (!E.normalize(second)) return fail("Enter a second message.");
  if (E.normalize(second).length > MAX_LETTERS) {
    return fail(`This page traces up to ${MAX_LETTERS} letters. For longer text, use solitaire-lab encrypt.`);
  }

  const mode = document.querySelector('input[name="reusemode"]:checked').value;
  const p1 = state.first.plaintext;
  const p2 = E.pad(E.normalize(second));
  const width = Math.min(p1.length, p2.length);
  const start = mode === "reset" ? state.first.startDeck : state.first.finalDeck;
  const c2 = E.encrypt(p2, start, { trace: false });

  const diff = (a, b) =>
    [...a.slice(0, width)]
      .map((ch, i) => String.fromCharCode(64 + E.subtractMod26(ch.charCodeAt(0) - 64, b.charCodeAt(i) - 64)))
      .join("");
  const cipherDiff = diff(state.first.ciphertext, c2.text);
  const plainDiff = diff(p1, p2);

  const rows = [
    ["P1", p1.slice(0, width), "p"],
    ["P2", p2.slice(0, width), "p"],
    ["K1", state.first.keystream.slice(0, width).map(E.valueToLetter).join(""), "k"],
    ["K2", c2.keystream.slice(0, width).map(E.valueToLetter).join(""), "k"],
    ["C1", state.first.ciphertext.slice(0, width), "c"],
    ["C2", c2.text.slice(0, width), "c"],
    ["C1 − C2", cipherDiff, "p"],
    ["P1 − P2", plainDiff, "p"],
  ];
  const table = document.createElement("table");
  table.className = "layers";
  for (const [label, text, cls] of rows) {
    const tr = table.insertRow();
    const th = document.createElement("th");
    th.textContent = label;
    tr.appendChild(th);
    for (const ch of text) {
      const td = tr.insertCell();
      td.className = cls;
      td.textContent = ch;
    }
  }
  $("live-reuse-table").replaceChildren(table);
  const cancelled = cipherDiff === plainDiff;
  $("live-reuse-verdict").textContent =
    mode === "reset"
      ? cancelled
        ? "K1 and K2 are the same, and the last two rows are identical. Subtracting the ciphertexts cancelled the key exactly. An attacker who never saw your deck now knows the difference between your two messages."
        : "Something is wrong: a reset deck should reproduce the same keystream."
      : cancelled
        ? "The rows happen to match, which a continued keystream makes vanishingly unlikely. Try a longer message."
        : "K2 is the next stretch of keystream, so the last two rows differ and nothing cancels. Continuing the deck avoids this leak.";
  $("live-reuse-out").hidden = false;
}

/* ---- wiring ---- */

export function initLive() {
  for (const radio of document.querySelectorAll('input[name="keymode"]')) {
    radio.addEventListener("change", syncKeyMode);
  }
  syncKeyMode();

  $("live-shuffle").addEventListener("click", () => {
    state.shuffled = E.shuffledDeck();
    showDeck(state.shuffled);
    $("live-shuffle-note").textContent = "Dealt with crypto.getRandomValues. Encrypt to use it.";
  });

  $("live-paste-ordered").addEventListener("click", () => {
    $("live-deck").value = E.ORDERED_DECK.join(" ");
  });

  $("live-run").addEventListener("click", run);
  $("live-message").addEventListener("keydown", (e) => {
    if (e.key === "Enter") run();
  });
  $("live-reuse-run").addEventListener("click", runReuse);
  $("live-second").addEventListener("keydown", (e) => {
    if (e.key === "Enter") runReuse();
  });

  $("live-copy-deck").addEventListener("click", async (e) => {
    if (!state.deck) return;
    const hash = `#deck=${state.deck.join("-")}`;
    history.replaceState(null, "", hash);
    try {
      await navigator.clipboard.writeText(location.origin + location.pathname + hash);
      e.target.textContent = "Copied. Anyone with the link has the key.";
    } catch {
      e.target.textContent = "Link in address bar";
    }
    setTimeout(() => (e.target.textContent = "Share this deck (the link contains the key)"), 2400);
  });

  // A deck permalink loads into the paste field. Messages are never put in a URL.
  const params = new URLSearchParams(location.hash.slice(1));
  const shared = params.get("deck");
  if (shared) {
    try {
      const deck = E.parseDeck(shared.replace(/-/g, " "));
      document.querySelector('input[name="keymode"][value="paste"]').checked = true;
      syncKeyMode();
      $("live-deck").value = deck.join(" ");
      showDeck(deck);
    } catch {
      /* a malformed link should not break the page */
    }
  }
}
