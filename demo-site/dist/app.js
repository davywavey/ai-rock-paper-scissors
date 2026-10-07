"use strict";

// The browser demo uses the same history-based strategy as main.py.
const moves = ["ROCK", "PAPER", "SCISSORS"];
const counters = { ROCK: "PAPER", PAPER: "SCISSORS", SCISSORS: "ROCK" };
const icons = { ROCK: "✊", PAPER: "✋", SCISSORS: "✌️" };
const state = { history: [], you: 0, ai: 0, round: 1, streak: 0, best: 0,
  done: false, matchDone: false, busy: false, sound: false, countdownTimer: null, generation: 0 };
const $ = id => document.getElementById(id);
const moveButtons = [...document.querySelectorAll("[data-move]")];
let audioContext;

function randomChoice(items) { return items[Math.floor(Math.random() * items.length)]; }
function aiMove(history) {
  if (history.length < 2 || Math.random() < 0.35) return randomChoice(moves);
  const recent = history.slice(-8);
  const counts = moves.map(move => recent.filter(value => value === move).length);
  const max = Math.max(...counts);
  return counters[randomChoice(moves.filter((_, index) => counts[index] === max))];
}
function winner(you, ai) {
  if (you === ai) return "draw";
  return counters[ai] === you ? "win" : "lose";
}
function sound(frequency = 600, duration = 0.09) {
  if (!state.sound) return;
  try {
    audioContext ??= new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === "suspended") audioContext.resume();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0.10, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + duration);
    oscillator.connect(gain); gain.connect(audioContext.destination);
    oscillator.start(); oscillator.stop(audioContext.currentTime + duration);
  } catch { /* The game also works on devices without audio support. */ }
}
function renderStats() {
  $("player-score").textContent = state.you;
  $("ai-score").textContent = state.ai;
  $("round-label").textContent = `ROUND ${String(state.round).padStart(2, "0")}`;
  $("streak").textContent = state.streak;
  $("best").textContent = state.best;
  $("ai-status").textContent = state.history.length < 2 ? "AI 正在学习" : "AI 预测已启用";
  moveButtons.forEach(button => { button.disabled = state.done || state.busy; });
  $("next-button").disabled = !state.done || state.busy;
  $("next-button").textContent = state.matchDone ? "新比赛 · SPACE" : "下一轮 · SPACE";
}
function clearArena() {
  $("game").classList.remove("win", "lose", "draw");
  $("player-hand").textContent = "?"; $("ai-hand").textContent = "?";
  $("player-move").textContent = "YOUR MOVE"; $("ai-move").textContent = "AI MOVE";
  $("phase-label").textContent = "READY TO PLAY";
  $("result").textContent = "选一拳，开局。";
  $("round-hint").textContent = "点击下方手势，与 AI 对决";
  $("particles").replaceChildren();
}
function burst() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const fragment = document.createDocumentFragment();
  for (let i = 0; i < 38; i++) {
    const particle = document.createElement("span");
    particle.className = "particle";
    particle.style.left = `${30 + Math.random() * 40}%`;
    particle.style.setProperty("--dx", `${(Math.random() - 0.5) * 450}px`);
    particle.style.setProperty("--dy", `${100 + Math.random() * 330}px`);
    particle.style.background = i % 2 ? "#dfff68" : "#8cbcff";
    particle.addEventListener("animationend", () => particle.remove(), { once: true });
    fragment.append(particle);
  }
  $("particles").replaceChildren(fragment);
}
function play(move) {
  if (state.busy || state.done || !moves.includes(move)) return;
  // Choose from past moves only, before adding the current move. AI cannot peek.
  const opponent = aiMove(state.history);
  state.history.push(move);
  const outcome = winner(move, opponent);
  if (outcome === "win") state.you++;
  if (outcome === "lose") state.ai++;
  state.done = true;
  state.matchDone = state.you === 2 || state.ai === 2;
  $("player-hand").textContent = icons[move]; $("ai-hand").textContent = icons[opponent];
  $("player-move").textContent = move; $("ai-move").textContent = opponent;
  $("game").classList.add(outcome);
  $("phase-label").textContent = state.matchDone ? "MATCH COMPLETE" : "ROUND COMPLETE";
  $("result").textContent = { win: "YOU WIN!", lose: "YOU LOSE!", draw: "DRAW!" }[outcome];
  $("round-hint").textContent = outcome === "draw" ? "平局不加分，再来一拳。" : "下一轮，换个思路？";
  if (state.matchDone) {
    if (state.you === 2) {
      state.streak++; state.best = Math.max(state.best, state.streak);
      $("round-hint").textContent = "YOU BEAT THE AI! · 继续挑战连胜";
    } else {
      state.streak = 0;
      $("round-hint").textContent = "AI 赢下本场 · 换种出拳节奏再挑战";
    }
  }
  if (outcome === "win") burst();
  sound(outcome === "win" ? 880 : outcome === "lose" ? 220 : 500, 0.2);
  renderStats();
}
function nextRound() {
  if (!state.done || state.busy) return;
  if (state.matchDone) { state.you = 0; state.ai = 0; state.round = 1; }
  else state.round++;
  state.done = false; state.matchDone = false; state.busy = true;
  clearArena(); renderStats();
  $("phase-label").textContent = "GET READY";
  $("round-hint").textContent = "倒计时结束后选择你的出拳";
  let count = 3;
  const generation = ++state.generation;
  $("result").textContent = count; sound();
  state.countdownTimer = window.setInterval(() => {
    if (generation !== state.generation) return;
    count--;
    if (count === 0) {
      window.clearInterval(state.countdownTimer); state.countdownTimer = null;
      state.busy = false;
      $("phase-label").textContent = "SHOW NOW";
      $("result").textContent = "出拳！";
      $("round-hint").textContent = "点击手势，或按 1 / 2 / 3";
      renderStats(); sound(780);
    } else { $("result").textContent = count; sound(); }
  }, 1000);
}
function reset() {
  state.generation++;
  window.clearInterval(state.countdownTimer); state.countdownTimer = null;
  Object.assign(state, { history: [], you: 0, ai: 0, round: 1, streak: 0, best: 0, done: false, matchDone: false, busy: false });
  clearArena(); renderStats();
}
moveButtons.forEach(button => button.addEventListener("click", () => play(button.dataset.move)));
$("next-button").addEventListener("click", nextRound);
$("reset-button").addEventListener("click", reset);
$("sound-button").addEventListener("click", () => {
  state.sound = !state.sound;
  $("sound-button").textContent = state.sound ? "声音：开" : "声音：关";
  $("sound-button").setAttribute("aria-pressed", String(state.sound)); sound();
});
document.addEventListener("keydown", event => {
  if (event.repeat || event.ctrlKey || event.altKey || event.metaKey) return;
  if (/INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
  if (event.code === "Space") {
    // On a focused button leave Space to the button's native click event.
    if (event.target.tagName === "BUTTON") return;
    event.preventDefault(); nextRound();
  } else if (event.key.toLowerCase() === "r") reset();
  else if (["1", "2", "3"].includes(event.key)) play(moves[Number(event.key) - 1]);
});
renderStats();

// Optional WebMCP integration; ordinary browsers continue to use the buttons.
if (document.modelContext?.registerTool) {
  const lifecycle = new AbortController();
  const register = tool => {
    try { Promise.resolve(document.modelContext.registerTool(tool, { signal: lifecycle.signal })).catch(() => {}); }
    catch { /* Browser support is optional. */ }
  };
  register({
    name: "read_rps_game", title: "读取猜拳比分",
    description: "Read the current match score and whether a round is ready to play.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, untrustedContentHint: false },
    execute: () => ({ you: state.you, ai: state.ai, streak: state.streak, best: state.best, ready: !state.done && !state.busy, matchDone: state.matchDone })
  });
  register({
    name: "play_rps_move", title: "出拳",
    description: "Play one rock, paper, or scissors move in the current ready round, updating the score.",
    inputSchema: { type: "object", properties: { move: { type: "string", enum: moves } }, required: ["move"], additionalProperties: false },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    execute: input => {
      if (!input || !moves.includes(input.move)) throw new Error("Choose ROCK, PAPER, or SCISSORS.");
      if (state.busy || state.done) throw new Error("The round is not ready.");
      play(input.move);
      return { you: state.you, ai: state.ai, result: $("result").textContent, matchDone: state.matchDone };
    }
  });
  window.addEventListener("pagehide", () => lifecycle.abort(), { once: true });
}
