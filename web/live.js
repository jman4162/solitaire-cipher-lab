/* The "Try it" section: encrypt your own message, in the browser.
 *
 * Everything the cipher does comes from engine.js; everything the reader sees
 * is drawn by player.js. This file is the wiring between them — a form, some
 * validation, and the second-message cancellation that is the whole reason
 * live execution is worth a second implementation. */

import * as E from "./engine.js";
import { withExplanations } from "./explain.js";
import { TracePlayer, renderDeck } from "./player.js";

const $ = (id) => document.getElementById(id);

const state = { deck: null, deckSource: "", first: null, player: null };

/* ---- key selection ---- */

function currentDeck() {
  const mode = document.querySelector('input[name="keymode"]:checked').value;
  if (mode === "passphrase") {
    const phrase = $("live-passphrase").value;
    if (!E.normalize(phrase)) throw new Error("Enter a passphrase — letters only, everything else is ignored.");
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
  if (!E.normalize(message)) return fail("Enter a message — letters only, everything else is ignored.");

  state.deck = deck;
  showDeck(deck);

  const result = E.encrypt(message, deck);
  state.first = { plaintext: E.pad(E.normalize(message)), ciphertext: result.text, keystream: result.keystream };

  $("live-layers").replaceChildren(layersTable(state.first.plaintext, result.keystream, result.text));
  $("live-cipher").textContent = E.group(result.text);
  $("live-summary").textContent =
    `${result.text.length} letters, keyed with ${state.deckSource}. ` +
    `Padded with X to a whole number of five-letter groups.`;
  $("live-results").hidden = false;

  // A fresh player over the reader's own trace. Explanations come from
  // explain.js because this trace did not exist at build time.
  state.player?.stop();
  state.player = new TracePlayer($("live-player"), withExplanations(result.trace));
  $("live-player-wrap").hidden = false;
  $("live-reuse-wrap").hidden = false;
  $("live-reuse-out").hidden = true;
}

/** The payoff: a second message under the same deck, and the key cancels. */
function runReuse() {
  const second = $("live-second").value;
  if (!state.first) return;
  $("live-error").hidden = true;
  if (!E.normalize(second)) return fail("Enter a second message to send under the same deck.");

  const p1 = state.first.plaintext;
  const p2 = E.pad(E.normalize(second));
  const width = Math.min(p1.length, p2.length);
  const keys = state.first.keystream.slice(0, width).map((k) => k % 26 || 26);
  const val = (s) => [...s.slice(0, width)].map((c) => c.charCodeAt(0) - 64);
  const chr = (vs) => vs.map((v) => String.fromCharCode(64 + v)).join("");

  const c1 = val(p1).map((p, i) => E.addMod26(p, keys[i]));
  const c2 = val(p2).map((p, i) => E.addMod26(p, keys[i]));
  const cipherDiff = c1.map((a, i) => E.subtractMod26(a, c2[i]));
  const plainDiff = val(p1).map((a, i) => E.subtractMod26(a, val(p2)[i]));

  const rows = [
    ["P1", p1.slice(0, width), "p"],
    ["P2", p2.slice(0, width), "p"],
    ["K", chr(keys), "k"],
    ["C1", chr(c1), "c"],
    ["C2", chr(c2), "c"],
    ["C1 − C2", chr(cipherDiff), "p"],
    ["P1 − P2", chr(plainDiff), "p"],
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
  const cancelled = chr(cipherDiff) === chr(plainDiff);
  $("live-reuse-verdict").textContent = cancelled
    ? "The last two rows are identical. Subtracting the ciphertexts cancelled the key exactly — an attacker who never saw your deck now knows the difference between your two messages."
    : "Something is wrong: the rows should match.";
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
      e.target.textContent = "Copied";
    } catch {
      e.target.textContent = "Link in address bar";
    }
    setTimeout(() => (e.target.textContent = "Link to this deck"), 1600);
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
