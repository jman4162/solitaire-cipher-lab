/* Solitaire Cipher Lab — trace player.
 *
 * This file contains NO cipher logic. It cannot encrypt anything, and it does
 * not know how Solitaire works. It replays trace files recorded by the Python
 * engine, which is what guarantees the page shows what the implementation
 * actually does rather than an idealised retelling of it.
 *
 * The only thing it does author is wording: a trace records structured facts,
 * and phrasing them is a rendering concern, exactly as it is in the Python
 * renderer. */

const SUIT_SYMBOL = { C: "♣", D: "♦", H: "♥", S: "♠" };
const RED_SUITS = new Set(["D", "H"]);

const PHASES = [
  ["move_joker_a", "Joker A"],
  ["move_joker_b", "Joker B"],
  ["triple_cut", "Triple cut"],
  ["count_cut", "Count cut"],
  ["output", "Output"],
];

const HEADLINES = {
  move_joker_a: "Move joker A down one",
  move_joker_b: "Move joker B down two",
  triple_cut: "Triple cut",
  count_cut: "Count cut",
  output: "Read the output card",
};

function cardLabel(code) {
  if (code === "JA") return { text: "JA", cls: "joker" };
  if (code === "JB") return { text: "JB", cls: "joker" };
  const rank = code[0] === "T" ? "10" : code[0];
  const suit = code[1];
  return { text: rank + SUIT_SYMBOL[suit], cls: RED_SUITS.has(suit) ? "red" : "" };
}

/** Phrase a trace event. Mirrors solitaire_lab/render/explain.py. */
function explain(event) {
  const m = event.meta || {};
  switch (event.phase) {
    case "move_joker_a":
    case "move_joker_b": {
      const positions = m.positions === 1 ? "one position" : `${m.positions} positions`;
      if (m.wrapped) {
        return `Joker ${m.joker} moves down ${positions}. It ran off the bottom, so it wraps round to
          just below the top card — not to the top itself — and ends at position ${m.to_index + 1}.`;
      }
      return `Joker ${m.joker} moves down ${positions}, from position ${m.from_index + 1} to ${m.to_index + 1}.`;
    }
    case "triple_cut":
      if (m.top_len === 0 && m.bottom_len === 0) {
        return "The jokers are already at the very top and bottom, so there is nothing outside them to swap.";
      }
      return `Everything outside the two jokers switches sides: the ${m.top_len} card(s) above the first
        joker and the ${m.bottom_len} below the second trade places. The ${m.middle_len} cards from one
        joker to the other stay exactly as they were.`;
    case "count_cut":
      if (m.from_letter) {
        const src = m.letter ? `the passphrase letter ${m.letter} (worth ${m.count})` : `a count of ${m.count}`;
        return `An extra count cut driven by ${src}: move that many cards from the top to just above the bottom card.`;
      }
      if (m.identity) {
        return `The bottom card is ${m.bottom_card}, a joker, worth 53. Cutting 53 of the 54 cards to just
          above the bottom card puts every one of them straight back — the deck is unchanged.`;
      }
      return `The bottom card is ${m.bottom_card}, worth ${m.count}. Move ${m.count} card(s) from the top
        to just above it. The bottom card itself never moves.`;
    case "output":
      if (m.is_joker) {
        return `The top card is ${m.top_card}, worth ${m.count}. Counting ${m.count} down lands on
          ${m.output_card} — a joker. Jokers produce no output, so this round is discarded and the whole
          thing runs again.`;
      }
      return `The top card is ${m.top_card}, worth ${m.count}. Counting ${m.count} down lands on
        ${m.output_card}. That card's value is this round's keystream number. The deck is not changed here.`;
    default:
      return "";
  }
}

function renderDeck(el, codes, highlight) {
  const marked = new Set(highlight || []);
  el.replaceChildren(
    ...codes.map((code, i) => {
      const { text, cls } = cardLabel(code);
      const div = document.createElement("div");
      div.className = "card " + cls + (marked.has(i) ? " hl" : "");
      div.textContent = text;
      return div;
    })
  );
}

export class TracePlayer {
  constructor(root, trace, options = {}) {
    this.root = root;
    this.trace = trace;
    this.index = 0;
    this.timer = null;
    this.key = options.key || "t";
    this.onChange = options.onChange || (() => {});
    this.build();
    this.render();
  }

  get events() {
    return this.trace.events;
  }

  build() {
    this.root.innerHTML = `
      <div class="player-head">
        <div class="step-name"><span class="round"></span> <span class="title"></span></div>
        <div class="phases"></div>
      </div>
      <div class="deck compact"></div>
      <p class="explain"></p>
      <div class="controls">
        <button class="first" title="Back to the start">&#8676;</button>
        <button class="prev">&#8592; Prev</button>
        <button class="primary play">Play</button>
        <button class="next">Next &#8594;</button>
        <input class="progress" type="range" min="0" step="1" />
        <span class="counter"></span>
      </div>
      <div class="keystream-out"></div>`;
    this.els = {
      round: this.root.querySelector(".round"),
      title: this.root.querySelector(".title"),
      phases: this.root.querySelector(".phases"),
      deck: this.root.querySelector(".deck"),
      explain: this.root.querySelector(".explain"),
      first: this.root.querySelector(".first"),
      prev: this.root.querySelector(".prev"),
      play: this.root.querySelector(".play"),
      next: this.root.querySelector(".next"),
      progress: this.root.querySelector(".progress"),
      counter: this.root.querySelector(".counter"),
      out: this.root.querySelector(".keystream-out"),
    };
    this.els.progress.max = String(this.events.length - 1);

    this.els.first.addEventListener("click", () => this.go(0));
    this.els.prev.addEventListener("click", () => this.go(this.index - 1));
    this.els.next.addEventListener("click", () => this.go(this.index + 1));
    this.els.play.addEventListener("click", () => this.toggle());
    this.els.progress.addEventListener("input", (e) => {
      this.stop();
      this.go(Number(e.target.value));
    });
    this.root.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { this.stop(); this.go(this.index + 1); }
      if (e.key === "ArrowLeft") { this.stop(); this.go(this.index - 1); }
    });
    this.root.tabIndex = 0;
  }

  go(index) {
    this.index = Math.max(0, Math.min(this.events.length - 1, index));
    this.render();
    this.onChange(this);
  }

  toggle() {
    this.timer ? this.stop() : this.play();
  }

  play() {
    if (this.index >= this.events.length - 1) this.index = 0;
    this.els.play.textContent = "Pause";
    this.timer = setInterval(() => {
      if (this.index >= this.events.length - 1) return this.stop();
      this.go(this.index + 1);
    }, 900);
  }

  stop() {
    clearInterval(this.timer);
    this.timer = null;
    this.els.play.textContent = "Play";
  }

  render() {
    const event = this.events[this.index];
    renderDeck(this.els.deck, event.after, event.affected);
    this.els.round.textContent = `Round ${event.round}`;
    this.els.title.textContent = HEADLINES[event.phase] || event.phase;
    this.els.explain.textContent = explain(event).replace(/\s+/g, " ").trim();
    this.els.progress.value = String(this.index);
    this.els.counter.textContent = `${this.index + 1} / ${this.events.length}`;
    this.els.prev.disabled = this.index === 0;
    this.els.next.disabled = this.index === this.events.length - 1;

    this.els.phases.replaceChildren(
      ...PHASES.map(([phase, label]) => {
        const chip = document.createElement("span");
        const order = PHASES.findIndex(([p]) => p === event.phase);
        const mine = PHASES.findIndex(([p]) => p === phase);
        chip.className = "phase-chip" + (phase === event.phase ? " on" : mine < order ? " done" : "");
        chip.textContent = label;
        return chip;
      })
    );

    // Keystream produced so far, with discarded rounds called out.
    const parts = [];
    let skipped = 0;
    for (let i = 0; i <= this.index; i++) {
      const e = this.events[i];
      if (e.phase !== "output") continue;
      if (e.output) parts.push(valueLetter(e.meta.output_value ?? cardValue(e.output)));
      else skipped++;
    }
    this.els.out.innerHTML = parts.length
      ? `keystream so far &nbsp;<b>${parts.join(" ")}</b>` +
        (skipped ? ` &nbsp;<span class="skip">(${skipped} round${skipped > 1 ? "s" : ""} discarded on a joker)</span>` : "")
      : `<span class="note">no keystream letter yet</span>`;
  }
}

const SUIT_OFFSET = { C: 0, D: 13, H: 26, S: 39 };
const RANK_VALUE = { A: 1, T: 10, J: 11, Q: 12, K: 13 };

function cardValue(code) {
  if (code === "JA" || code === "JB") return 53;
  const rank = RANK_VALUE[code[0]] ?? Number(code[0]);
  return SUIT_OFFSET[code[1]] + rank;
}

function valueLetter(value) {
  const v = value > 26 ? value - 26 : value;
  return String.fromCharCode(64 + v);
}

export { renderDeck, explain, cardValue, valueLetter, cardLabel };
