import { splitSyllable, toneMarkLetters, zhuyinParts, zhuyinKeys, zhuyinText, KEYBOARD_ROWS, KEY_TO_ZHUYIN } from "./phonetics.js";
import { Records, settingKey } from "./records.js";
import { renderRecords } from "./records-view.js";
import { LEVELS, TEXT_LEVEL_MAX, describe, fmtTime, textLevelName } from "./labels.js";
import { renderReport } from "./report.js";

const HAN = /[㐀-鿿]/;
const ROUND = { word: 20, sentence: 5, passage: 1 };

const $ = id => document.getElementById(id);
const SETTINGS_KEY = "ctd:settings:v1";
const DEFAULTS = {
  script: "simp", input: "pinyin", length: "word", source: "hsk", level: 1, difficulty: "beginner",
  textBasis: "difficulty", textLevel: 1,
  showReading: true, showMeaning: true, autoSpeak: false, showKeyboard: true,
};
const S = (() => {
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") }; } catch { return { ...DEFAULTS }; }
})();
function saveSettings() { try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(S)); } catch {} }

// ---------- データ ----------
const cache = new Map();
async function fetchJSON(path) {
  if (!cache.has(path)) cache.set(path, fetch(path).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }));
  return cache.get(path);
}
const loadTexts = () => fetchJSON("data/texts/all.json");

// 例文は {s, t, p, ja, tw, d: 難易度, l: 長さ, hsk, tbcl, src: 時事の例文の出典}。単語と同じ配列の形にそろえる
function textMatches(o) {
  if (o.l !== S.length) return false;
  if (S.textBasis === "difficulty") return o.d === S.difficulty;
  return o[S.textBasis] === S.textLevel;
}
async function loadPool() {
  if (S.length === "word") return fetchJSON(`data/words/${S.source}-${S.level}.json`);
  const all = await loadTexts();
  return all.filter(textMatches).map(o => Object.assign([o.s, o.t, o.p, o.ja, o.tw], { hsk: o.hsk, tbcl: o.tbcl, src: o.src }));
}

function sample(arr, n) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a.slice(0, n);
}

// データの1件: [簡体字, 繁体字, 大陸の読み, 意味, 台湾の読み（大陸と違うときだけ）]
function buildItem(row) {
  const [simp, trad, cn, meaning, tw] = row;
  const text = S.script === "simp" ? simp : trad;
  const syls = (S.script === "trad" && tw ? tw : cn).split(" ");
  let k = 0;
  const cells = [...text].map(ch => {
    if (!HAN.test(ch)) return { ch, punct: true };
    const { base, tone } = splitSyllable(syls[k++]);
    const zy = zhuyinParts(base, tone);
    const target = S.input === "zhuyin" ? zhuyinKeys(base, tone) : S.input === "tone" ? base + tone : base;
    return { ch, base, tone, letters: toneMarkLetters(base, tone), zy, target };
  });
  const level = row.hsk ? `${textLevelName("hsk", row.hsk)}・${textLevelName("tbcl", row.tbcl)}` : "";
  return { text, meaning, cells, level, src: row.src };
}

// ---------- ラウンド ----------
let R = null;
let roundToken = 0;

async function newRound() {
  const token = ++roundToken;
  $("report").hidden = true;
  $("result").hidden = true;
  $("play").hidden = false;
  $("line").className = "line";
  $("line").innerHTML = '<p class="loading">読み込み中…</p>';
  let pool;
  try {
    pool = await loadPool();
  } catch {
    $("line").innerHTML = '<p class="loading">問題を読み込めませんでした。ページを再読み込みしてください。</p>';
    return;
  }
  if (token !== roundToken) return;
  const settings = {
    script: S.script, input: S.input, length: S.length, source: S.source, level: S.level,
    difficulty: S.difficulty, textBasis: S.textBasis, textLevel: S.textLevel,
  };
  if (!pool.length) {
    $("line").innerHTML = '<p class="loading">この条件の例文はまだありません。別の級を選んでください。</p>';
    R = null;
    return;
  }
  R = {
    settings, items: sample(pool, ROUND[S.length]).map(buildItem),
    qi: 0, ci: 0, pos: 0, keys: 0, misses: 0, chars: 0, start: null, end: null, weak: {},
  };
  $("courseTag").textContent = describe(settings);
  loadItem();
  renderStats();
  focusInput();
}

const item = () => R.items[R.qi];

// 時事の例文は、話題にした記事へのリンクを出す
function showSource(src) {
  const el = $("itemSrc");
  el.hidden = !src;
  if (!src) return;
  const a = el.querySelector("a");
  a.href = src;
  try { a.textContent = new URL(src).hostname; } catch { a.textContent = src; }
}

function skipPunct() {
  const cells = item().cells;
  while (R.ci < cells.length && cells[R.ci].punct) R.ci++;
}

function loadItem() {
  const it = item();
  R.ci = 0; R.pos = 0;
  skipPunct();
  const line = $("line");
  line.className = "line " + R.settings.length;
  line.innerHTML = "";
  for (const c of it.cells) {
    const el = document.createElement("div");
    el.className = "cell" + (c.punct ? " punct" : "");
    el.innerHTML = `<div class="rd${S.input === "zhuyin" ? " zy" : ""}"></div><div class="han"><span></span></div>`;
    el.querySelector(".han span").textContent = c.ch;
    line.appendChild(el);
  }
  $("stage").scrollTop = 0;
  $("meaning").textContent = it.meaning;
  $("itemLevel").textContent = it.level;
  $("itemLevel").hidden = !it.level;
  $("meaning").hidden = !S.showMeaning;
  showSource(it.src);
  const nx = R.items[R.qi + 1];
  $("next").innerHTML = "";
  if (nx) { $("next").append("次: "); const b = document.createElement("b"); b.textContent = nx.text.length > 16 ? nx.text.slice(0, 16) + "…" : nx.text; $("next").append(b); }
  $("count").textContent = `${R.qi + 1} / ${R.items.length}`;
  $("barFill").style.width = (R.qi / R.items.length * 100) + "%";
  renderCells(true);
  if (S.autoSpeak) speak(it.text);
}

let lastCur = -1;
function renderCells(all) {
  const it = item(), els = $("line").children;
  const from = all ? 0 : Math.max(0, Math.min(lastCur, R.ci) - 1);
  const to = all ? it.cells.length : Math.min(it.cells.length, R.ci + 1);
  for (let i = from; i < to; i++) renderCell(it.cells[i], els[i], i);
  if (lastCur !== R.ci) {
    lastCur = R.ci;
    const cur = els[R.ci];
    if (cur && R.settings.length === "passage") cur.scrollIntoView({ block: "nearest" });
  }
  renderKeyboard();
}

function renderCell(c, el, i) {
  const done = i < R.ci, cur = i === R.ci;
  el.className = "cell" + (c.punct ? " punct" : "") + (done ? " done" : "") + (cur && !c.punct ? " cur" : "");
  if (c.punct) return;
  const rd = el.firstChild;
  const typed = done ? Infinity : cur ? R.pos : 0;
  const show = S.showReading || done;
  if (S.input === "zhuyin") {
    const syms = c.zy.symbols;
    const parts = syms.map((s, j) => (j < typed ? `<span class="t">${s}</span>` : show ? s : ""));
    const mark = c.zy.mark && (show ? (done ? `<span class="t">${c.zy.mark}</span>` : c.zy.mark) : "");
    const html = c.tone === 5 ? (mark || "") + parts.join("") : parts.join("") + (mark || "");
    rd.innerHTML = html || "&nbsp;";
  } else if (show) {
    rd.innerHTML = c.letters.map((l, j) => (j < typed ? `<span class="t">${l}</span>` : l)).join("") +
      (S.input === "tone" && done ? `<span class="tone">${c.tone}</span>` : "");
  } else {
    const n = Math.min(typed, c.base.length);
    const shown = [...c.base.slice(0, n)].map(l => (l === "v" ? "ü" : l)).join("");
    rd.innerHTML = shown ? `<span class="t">${shown}</span>` : "&nbsp;";
  }
}

function weakKey(c) {
  return S.input === "zhuyin" ? (c.tone === 5 ? "˙" : "") + c.zy.symbols.join("") + (c.tone === 5 ? "" : c.zy.mark) : c.letters.join("");
}

function typeChar(ch) {
  if (!R || R.end) return;
  ch = ch.toLowerCase();
  if (S.input !== "zhuyin" && (ch === " " || ch === "'")) return;
  const it = item(), c = it.cells[R.ci];
  if (!c) return;
  if (!R.start) R.start = performance.now();
  R.keys++;
  if (ch === c.target[R.pos]) {
    R.pos++;
    if (R.pos === c.target.length) {
      R.chars++; R.ci++; R.pos = 0; skipPunct();
      if (R.ci >= it.cells.length) return advance();
    }
  } else {
    R.misses++;
    const k = weakKey(c);
    R.weak[k] = (R.weak[k] || 0) + 1;
    const el = $("line").children[R.ci];
    el.classList.remove("miss"); void el.offsetWidth; el.classList.add("miss");
    setTimeout(() => el.classList.remove("miss"), 260);
  }
  renderCells(false);
  renderStats();
}

function advance() {
  R.qi++;
  if (R.qi >= R.items.length) return finish();
  lastCur = -1;
  loadItem();
  renderStats();
}

// ---------- 数値 ----------
const elapsed = () => (R && R.start ? ((R.end || performance.now()) - R.start) / 1000 : 0);
const perMin = n => { const s = elapsed(); return s > 1 ? Math.round(n / (s / 60)) : 0; };
const accuracy = () => (R && R.keys ? Math.round((R.keys - R.misses) / R.keys * 1000) / 10 : 100);

function renderStats() {
  if (!R) return;
  $("sCpm").innerHTML = `${perMin(R.chars)}<small>字/分</small>`;
  $("sKpm").innerHTML = `${perMin(R.keys - R.misses)}<small>キー/分</small>`;
  $("sAcc").innerHTML = `${accuracy()}<small>%・ミス${R.misses}</small>`;
  $("sTime").textContent = fmtTime(elapsed());
}
setInterval(() => { if (R && R.start && !R.end) renderStats(); }, 250);

function finish() {
  R.end = performance.now();
  $("barFill").style.width = "100%";
  renderStats();
  const cpm = perMin(R.chars), kpm = perMin(R.keys - R.misses), acc = accuracy(), secs = Math.round(elapsed());
  const key = settingKey(R.settings);
  const prev = Records.best(key);
  const entry = Records.add({ settings: R.settings, chars: R.chars, keys: R.keys, misses: R.misses, secs, cpm, kpm, acc, weak: R.weak });
  const isNew = acc >= 80 && (!prev || cpm > prev.cpm);
  const weak = Object.entries(R.weak).sort((a, b) => b[1] - a[1]).slice(0, 8);

  $("play").hidden = true;
  const res = $("result");
  res.hidden = false;
  const cheer = weak.length === 0 || isNew;
  // ダーバオのひとこと
  const headline = isNew && prev ? "自己ベスト更新！ ダーバオも大喜び" : weak.length === 0 ? "ノーミス、すごい！" : acc >= 95 ? "いい調子！ この調子で打とう" : "おつかれさま！ もう一回いこう";
  res.innerHTML = `
    <img class="result-mascot${cheer ? " cheer" : ""}" src="assets/img/mascot.png" alt="ダーバオ" width="520" height="491">
    <h2>${headline}</h2>
    <div class="big">
      <div><span class="v">${cpm}</span><span class="k">字/分</span></div>
      <div><span class="v">${kpm}</span><span class="k">キー/分</span></div>
      <div><span class="v">${acc}%</span><span class="k">正確率</span></div>
      <div><span class="v">${fmtTime(secs)}</span><span class="k">時間</span></div>
    </div>
    <p class="best ${isNew ? "new" : ""}">${
      acc < 80 ? "正確率80%以上で自己ベストの対象になります"
      : isNew ? (prev ? `自己ベスト更新（前回のベスト ${prev.cpm} 字/分）` : "この設定での初めての記録です")
      : `自己ベスト ${prev.cpm} 字/分`}</p>
    <p class="note">${describe(R.settings)}</p>
    ${weak.length
      ? `<div><p class="label" style="margin:0 0 8px">ミスの多かった音節</p><div class="chips">${weak.map(([k, n]) => `<span>${k}<em>×${n}</em></span>`).join("")}</div></div>`
      : ""}
    <div class="actions">
      <button type="button" class="primary" id="again">もう一度（Enter）</button>
      <button type="button" class="secondary" id="toRecords">記録を見る</button>
      <button type="button" class="secondary" id="reportFromResult">誤りを報告</button>
    </div>
    ${Records.available() ? "" : '<p class="note">このブラウザでは記録を保存できない設定になっています（プライベートモードなど）。</p>'}`;
  $("again").addEventListener("click", newRound);
  $("toRecords").addEventListener("click", () => { location.hash = "records"; });
  $("reportFromResult").addEventListener("click", openReport);
  $("again").focus();
  void entry;
}

// ---------- 誤りの報告 ----------
function readingOf(it) {
  const han = it.cells.filter(c => !c.punct);
  const py = han.map(c => c.letters.join("")).join(" ");
  const zy = han.map(c => zhuyinText(c.base, c.tone)).join(" ");
  return `${py} ／ ${zy}`;
}

function openReport() {
  if (!R) return;
  const entries = R.items.map(it => ({
    label: it.text.length > 24 ? it.text.slice(0, 24) + "…" : it.text,
    item: it.meaning ? `${it.text}（${it.meaning}）` : it.text,
    reading: readingOf(it),
  }));
  renderReport($("report"), {
    entries,
    index: R.end ? 0 : R.qi,
    settings: describe(R.settings),
    onClose: focusInput,
  });
  $("report").scrollIntoView({ block: "nearest" });
}
$("reportBtn").addEventListener("click", openReport);

// ---------- 注音キーボード ----------
function buildKeyboard() {
  const kbd = $("kbd");
  kbd.innerHTML = "";
  for (const row of KEYBOARD_ROWS) {
    const r = document.createElement("div");
    r.className = "kbd-row";
    for (const k of row) {
      const z = KEY_TO_ZHUYIN[k] || "";
      r.insertAdjacentHTML("beforeend", `<div class="key" data-k="${k}"><b>${z}</b><small>${k.toUpperCase()}</small></div>`);
    }
    kbd.appendChild(r);
  }
  kbd.insertAdjacentHTML("beforeend", `<div class="kbd-row"><div class="key space" data-k=" "><b>ˉ</b><small>SPACE 一声</small></div></div>`);
}
buildKeyboard();

function renderKeyboard() {
  const on = S.input === "zhuyin" && S.showKeyboard && R && !R.end;
  $("kbd").hidden = !on;
  if (!on) return;
  const c = item().cells[R.ci];
  const next = c ? c.target[R.pos] : null;
  for (const el of $("kbd").querySelectorAll(".key")) el.classList.toggle("on", el.dataset.k === next);
}

// ---------- 読み上げ ----------
let voices = [];
function loadVoices() { try { voices = speechSynthesis.getVoices(); } catch {} }
if ("speechSynthesis" in window) { loadVoices(); speechSynthesis.onvoiceschanged = loadVoices; }
function speak(text) {
  try {
    if (!("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const want = S.script === "trad" ? /zh[-_]TW/i : /zh[-_]CN/i;
    u.voice = voices.find(v => want.test(v.lang)) || voices.find(v => /^zh/i.test(v.lang)) || null;
    u.lang = S.script === "trad" ? "zh-TW" : "zh-CN";
    u.rate = 0.85;
    speechSynthesis.speak(u);
  } catch {}
}

// ---------- 入力 ----------
function focusInput() {
  if (!R || R.end || !$("recordsView").hidden || !$("report").hidden) return;
  $("typer").focus({ preventScroll: true });
}
function setHint() {
  const h = $("hint");
  h.classList.remove("warn");
  if (document.activeElement !== $("typer")) { h.textContent = "ここをクリックすると入力を始められます"; return; }
  h.textContent = S.input === "zhuyin"
    ? "IMEはオフ（英数）で、大千式の配列どおりにキーを押します。声調キーで音節が確定します"
    : "IMEはオフ（英数）で入力します。ü は v";
}
function warn(msg) { const h = $("hint"); h.textContent = msg; h.classList.add("warn"); }

const typer = $("typer");
typer.addEventListener("input", e => {
  if (e.isComposing) return;
  const v = typer.value; typer.value = "";
  for (const ch of v) typeChar(ch);
});
typer.addEventListener("keydown", e => {
  // スペースは input イベントで拾えない環境があるので keydown で扱う
  if (e.key === " " && S.input === "zhuyin" && !e.isComposing) { e.preventDefault(); typeChar(" "); }
});
typer.addEventListener("compositionstart", () => warn("IMEがオンになっています。英数入力に切り替えてください"));
typer.addEventListener("compositionend", () => { typer.value = ""; });
typer.addEventListener("focus", setHint);
typer.addEventListener("blur", setHint);

$("desk").addEventListener("click", e => { if (!e.target.closest("button, a, .report")) focusInput(); });
$("speakBtn").addEventListener("click", () => { if (R) speak(item().text); focusInput(); });

document.addEventListener("keydown", e => {
  if (!$("recordsView").hidden || e.target.closest?.(".report")) return;
  if (e.key === "Escape") { e.preventDefault(); newRound(); }
  else if (e.key === "Enter" && R && R.end && document.activeElement?.id !== "toRecords") { e.preventDefault(); newRound(); }
});

// ---------- 設定 ----------
function syncControls() {
  for (const seg of document.querySelectorAll(".seg[data-key]")) {
    for (const b of seg.children) b.setAttribute("aria-pressed", String(b.dataset.v === S[seg.dataset.key]));
  }
  const sel = $("levelSel");
  sel.innerHTML = LEVELS[S.source].map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  if (!LEVELS[S.source].some(l => l[0] === S.level)) S.level = 1;
  sel.value = String(S.level);
  $("wordGroup").hidden = S.length !== "word";
  $("diffGroup").hidden = S.length === "word";
  $("diffSeg").hidden = S.textBasis !== "difficulty";
  $("textLevelSel").hidden = S.textBasis === "difficulty";
  if (S.textBasis !== "difficulty") fillTextLevels();
  $("kbdToggle").hidden = S.input !== "zhuyin";
  for (const k of ["showReading", "showMeaning", "autoSpeak", "showKeyboard"]) $(k).checked = S[k];
  setHint();
}

document.querySelectorAll(".seg[data-key]").forEach(seg => seg.addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b || S[seg.dataset.key] === b.dataset.v) return;
  S[seg.dataset.key] = b.dataset.v;
  saveSettings(); syncControls(); newRound();
}));
$("levelSel").addEventListener("change", e => { S.level = +e.target.value; saveSettings(); newRound(); });
$("textLevelSel").addEventListener("change", e => { S.textLevel = +e.target.value; saveSettings(); newRound(); });

// HSK級・TOCFL級の選択肢に、その級の例文の数を添える
async function fillTextLevels() {
  const all = await loadTexts().catch(() => []);
  const basis = S.textBasis, max = TEXT_LEVEL_MAX[basis] + 1;
  const counts = {};
  for (const o of all) if (o.l === S.length) counts[o[basis]] = (counts[o[basis]] || 0) + 1;
  const sel = $("textLevelSel");
  sel.innerHTML = Array.from({ length: max }, (_, i) => i + 1)
    .map(lv => `<option value="${lv}" ${counts[lv] ? "" : "disabled"}>${textLevelName(basis, lv)}（${counts[lv] || 0}件）</option>`).join("");
  if (!counts[S.textLevel]) {
    const first = Object.keys(counts).map(Number).sort((a, b) => a - b)[0];
    if (first && first !== S.textLevel) { S.textLevel = first; saveSettings(); sel.value = String(first); return newRound(); }
  }
  sel.value = String(S.textLevel);
}
for (const k of ["showReading", "showMeaning", "autoSpeak", "showKeyboard"]) {
  $(k).addEventListener("change", e => {
    S[k] = e.target.checked; saveSettings();
    if (R && !R.end) { $("meaning").hidden = !S.showMeaning; renderCells(true); }
    focusInput();
  });
}

// ---------- 画面切り替え ----------
function route() {
  const records = location.hash === "#records";
  $("practiceView").hidden = records;
  $("recordsView").hidden = !records;
  for (const a of document.querySelectorAll(".nav a[data-view]")) {
    if ((a.dataset.view === "records") === records) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  if (records) { renderRecords($("recordsBody")); window.scrollTo(0, 0); }
  else focusInput();
}
window.addEventListener("hashchange", route);

syncControls();
route();
newRound();
