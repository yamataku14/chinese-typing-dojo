// 設定の表示名など、練習画面と記録画面で共有するもの

export const LEVELS = {
  hsk: [1, 2, 3, 4, 5, 6].map(n => [n, `${n}級`]),
  tocfl: [[1, "第1級（基礎）"], [2, "第2級（基礎）"], [3, "第3級（基礎）"], [4, "第4級（進階）"], [5, "第5級（進階）"], [6, "第6級（精熟）"], [7, "第7級（精熟）"]],
};
export const NAMES = {
  script: { simp: "簡体字", trad: "繁體字" },
  input: { pinyin: "ピンイン", tone: "ピンイン＋声調", zhuyin: "注音" },
  length: { word: "単語", sentence: "一文", passage: "長文" },
  difficulty: { beginner: "初級", intermediate: "中級", advanced: "上級", expert: "超級" },
  source: { hsk: "HSK", tocfl: "TBCL" },
};
// 例文の級の表示（判定値が最大級を超えると「〜級超」）
export const TEXT_LEVEL_MAX = { hsk: 6, tbcl: 7 };
export function textLevelName(basis, lv) {
  const name = NAMES.source[basis === "tbcl" ? "tocfl" : "hsk"];
  return lv > TEXT_LEVEL_MAX[basis] ? `${name} ${TEXT_LEVEL_MAX[basis]}級超` : `${name} ${lv}級相当`;
}

export function describe(s) {
  const what = s.length === "word"
    ? `${NAMES.source[s.source]} ${(LEVELS[s.source].find(l => l[0] === s.level) || [0, ""])[1]}`
    : `${NAMES.length[s.length]}・${!s.textBasis || s.textBasis === "difficulty" ? NAMES.difficulty[s.difficulty] : textLevelName(s.textBasis, s.textLevel)}`;
  return `${what}・${NAMES.script[s.script]}・${NAMES.input[s.input]}`;
}

export const fmtTime = s => { s = Math.floor(s); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
