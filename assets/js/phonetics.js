// 数字声調ピンイン（"lv4"）を、声調記号つきピンイン・注音・キー入力列に変換する。
// 変換規則は scripts/phonetics.py と同じ。どちらかを変えたら両方そろえること。

const TONE_VOWELS = { a: "āáǎàa", e: "ēéěèe", i: "īíǐìi", o: "ōóǒòo", u: "ūúǔùu", v: "ǖǘǚǜü" };

const INITIALS = [
  ["zh", "ㄓ"], ["ch", "ㄔ"], ["sh", "ㄕ"],
  ["b", "ㄅ"], ["p", "ㄆ"], ["m", "ㄇ"], ["f", "ㄈ"], ["d", "ㄉ"], ["t", "ㄊ"],
  ["n", "ㄋ"], ["l", "ㄌ"], ["g", "ㄍ"], ["k", "ㄎ"], ["h", "ㄏ"],
  ["j", "ㄐ"], ["q", "ㄑ"], ["x", "ㄒ"], ["r", "ㄖ"], ["z", "ㄗ"], ["c", "ㄘ"], ["s", "ㄙ"],
];
const FINALS = {
  a: "ㄚ", o: "ㄛ", e: "ㄜ", ai: "ㄞ", ei: "ㄟ", ao: "ㄠ", ou: "ㄡ",
  an: "ㄢ", en: "ㄣ", ang: "ㄤ", eng: "ㄥ", er: "ㄦ", ong: "ㄨㄥ",
  i: "ㄧ", ia: "ㄧㄚ", ie: "ㄧㄝ", iao: "ㄧㄠ", iu: "ㄧㄡ", ian: "ㄧㄢ",
  in: "ㄧㄣ", iang: "ㄧㄤ", ing: "ㄧㄥ", iong: "ㄩㄥ", io: "ㄧㄛ",
  u: "ㄨ", ua: "ㄨㄚ", uo: "ㄨㄛ", uai: "ㄨㄞ", ui: "ㄨㄟ", uan: "ㄨㄢ",
  un: "ㄨㄣ", uang: "ㄨㄤ", ueng: "ㄨㄥ",
  v: "ㄩ", ve: "ㄩㄝ", van: "ㄩㄢ", vn: "ㄩㄣ", ue: "ㄩㄝ",
};
const ZERO = {
  yi: "ㄧ", ya: "ㄧㄚ", ye: "ㄧㄝ", yao: "ㄧㄠ", you: "ㄧㄡ", yan: "ㄧㄢ",
  yin: "ㄧㄣ", yang: "ㄧㄤ", ying: "ㄧㄥ", yong: "ㄩㄥ", yo: "ㄧㄛ",
  yu: "ㄩ", yue: "ㄩㄝ", yuan: "ㄩㄢ", yun: "ㄩㄣ",
  wu: "ㄨ", wa: "ㄨㄚ", wo: "ㄨㄛ", wai: "ㄨㄞ", wei: "ㄨㄟ", wan: "ㄨㄢ",
  wen: "ㄨㄣ", wang: "ㄨㄤ", weng: "ㄨㄥ", e: "ㄜ",
};
const ZHUYIN_TONES = ["", "ˊ", "ˇ", "ˋ", "˙"];

// 大千式（台湾の標準）注音キー配列
export const ZHUYIN_KEYS = {
  "ㄅ": "1", "ㄆ": "q", "ㄇ": "a", "ㄈ": "z", "ㄉ": "2", "ㄊ": "w", "ㄋ": "s", "ㄌ": "x",
  "ㄍ": "e", "ㄎ": "d", "ㄏ": "c", "ㄐ": "r", "ㄑ": "f", "ㄒ": "v", "ㄓ": "5", "ㄔ": "t",
  "ㄕ": "g", "ㄖ": "b", "ㄗ": "y", "ㄘ": "h", "ㄙ": "n", "ㄧ": "u", "ㄨ": "j", "ㄩ": "m",
  "ㄚ": "8", "ㄛ": "i", "ㄜ": "k", "ㄝ": ",", "ㄞ": "9", "ㄟ": "o", "ㄠ": "l", "ㄡ": ".",
  "ㄢ": "0", "ㄣ": "p", "ㄤ": ";", "ㄥ": "/", "ㄦ": "-",
  "ˉ": " ", "ˊ": "6", "ˇ": "3", "ˋ": "4", "˙": "7",
};
export const KEYBOARD_ROWS = [
  "1234567890-".split(""),
  "qwertyuiop".split(""),
  "asdfghjkl;".split(""),
  "zxcvbnm,./".split(""),
];
export const KEY_TO_ZHUYIN = Object.fromEntries(Object.entries(ZHUYIN_KEYS).map(([z, k]) => [k, z]));

export function splitSyllable(numeric) {
  const m = /^([a-zü:]+)([1-5])$/.exec(numeric);
  if (!m) throw new Error("bad syllable " + numeric);
  return { base: m[1].replace("u:", "v").replace("ü", "v"), tone: +m[2] };
}

// 声調記号つきピンインを1文字ずつの配列で返す（base の各文字と1対1に対応）
export function toneMarkLetters(base, tone) {
  let idx = base.indexOf("a");
  if (idx < 0) idx = base.indexOf("e");
  if (idx < 0 && base.includes("ou")) idx = base.indexOf("o");
  if (idx < 0) for (let i = base.length - 1; i >= 0; i--) if ("iouv".includes(base[i])) { idx = i; break; }
  return [...base].map((c, i) => (i === idx ? TONE_VOWELS[c][tone - 1] : c === "v" ? "ü" : c));
}

function baseToZhuyin(base) {
  if (ZERO[base]) return ZERO[base];
  if (base === "r") return "ㄦ";
  for (const [ini, sym] of INITIALS) {
    if (!base.startsWith(ini)) continue;
    let fin = base.slice(ini.length);
    if (fin === "i" && ["zh", "ch", "sh", "r", "z", "c", "s"].includes(ini)) return sym;
    if (["j", "q", "x"].includes(ini) && fin.startsWith("u")) fin = "v" + fin.slice(1);
    if (FINALS[fin]) return sym + FINALS[fin];
    break;
  }
  if (FINALS[base]) return FINALS[base];
  throw new Error("no zhuyin for " + base);
}

// 注音の記号列（声調記号を含まない）と声調記号
export function zhuyinParts(base, tone) {
  return { symbols: [...baseToZhuyin(base)], mark: ZHUYIN_TONES[tone - 1] };
}

// 表示用の注音文字列（軽声は前に˙）
export function zhuyinText(base, tone) {
  const { symbols, mark } = zhuyinParts(base, tone);
  return tone === 5 ? "˙" + symbols.join("") : symbols.join("") + mark;
}

// 注音入力で打つキー列（記号 → 声調キー。一声はスペース）
export function zhuyinKeys(base, tone) {
  const { symbols } = zhuyinParts(base, tone);
  return symbols.map(s => ZHUYIN_KEYS[s]).join("") + ZHUYIN_KEYS[["ˉ", "ˊ", "ˇ", "ˋ", "˙"][tone - 1]];
}
