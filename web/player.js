/* Solitaire Cipher Lab — trace player.
 *
 * This file contains NO cipher logic. It cannot encrypt anything, and it does
 * not know how Solitaire works. It replays traces: the ones the Python engine
 * recorded at build time, and the ones web/engine.js makes for a reader's own
 * key, which CI checks against Python trace for trace.
 *
 * It does not even phrase the steps: explanations come from the Python
 * renderer at build time, or from explain.js (tested to match it character for
 * character) for live traces. All this file knows is how to draw a card. */

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
      <div class="deck compact" role="img" aria-label="The deck after this step"></div>
      <p class="explain" aria-live="polite"></p>
      <div class="controls">
        <button class="first" title="Back to the start">&#8676;</button>
        <button class="prev">&#8592; Prev</button>
        <button class="primary play">Play</button>
        <button class="next">Next &#8594;</button>
        <input class="progress" type="range" min="0" step="1" aria-label="Step" />
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
    // One controller per player, so destroy() removes the root listener that a
    // rebuilt player on the same element would otherwise stack on top of.
    this.abort = new AbortController();
    this.root.addEventListener("keydown", (e) => {
      // The slider handles its own arrow keys; stepping here as well would skip one.
      if (e.target === this.els.progress) return;
      if (e.key === "ArrowRight") { this.stop(); this.go(this.index + 1); }
      if (e.key === "ArrowLeft") { this.stop(); this.go(this.index - 1); }
    }, { signal: this.abort.signal });
    this.root.tabIndex = 0;
  }

  go(index) {
    this.index = Math.max(0, Math.min(this.events.length - 1, Math.trunc(index)));
    this.render();
    this.onChange(this);
  }

  toggle() {
    this.timer ? this.stop() : this.play();
  }

  play() {
    if (this.index >= this.events.length - 1) this.go(0);
    this.els.play.textContent = "Pause";
    this.timer = setInterval(() => {
      if (this.index >= this.events.length - 1) return this.stop();
      this.go(this.index + 1);
    }, 900);
  }

  destroy() {
    this.stop();
    this.abort.abort();
  }

  stop() {
    clearInterval(this.timer);
    this.timer = null;
    this.els.play.textContent = "Play";
  }

  render() {
    const event = this.events[this.index];
    const words = (this.trace.explanations || [])[this.index] || {};
    // The renderer may point at a smaller, clearer set of cards than `affected`.
    renderDeck(this.els.deck, event.after, words.focus || event.affected);
    this.els.round.textContent = `Round ${event.round}`;
    this.els.title.textContent = words.headline || HEADLINES[event.phase] || event.phase;
    this.els.explain.textContent = words.text || "";
    this.els.deck.setAttribute("aria-label", `Deck after round ${event.round}, ${this.els.title.textContent}. ${words.text || ""}`.trim());
    this.els.progress.setAttribute(
      "aria-valuetext",
      `step ${this.index + 1} of ${this.events.length}, ${this.els.title.textContent}`
    );
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
      if (e.meta.output_letter) parts.push(e.meta.output_letter);
      else skipped++;
    }
    this.els.out.innerHTML = parts.length
      ? `keystream so far &nbsp;<b>${parts.join(" ")}</b>` +
        (skipped ? ` &nbsp;<span class="skip">(${skipped} round${skipped > 1 ? "s" : ""} discarded on a joker)</span>` : "")
      : `<span class="note">no keystream letter yet</span>`;
  }
}

export { renderDeck, cardLabel };
