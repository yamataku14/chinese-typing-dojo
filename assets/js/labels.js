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
  source: { hsk: "HSK", tocfl: "TOCFL" },
};
export function describe(s) {
  const what = s.length === "word"
    ? `${NAMES.source[s.source]} ${(LEVELS[s.source].find(l => l[0] === s.level) || [0, ""])[1]}`
    : `${NAMES.length[s.length]}・${NAMES.difficulty[s.difficulty]}`;
  return `${what}・${NAMES.script[s.script]}・${NAMES.input[s.input]}`;
}

export const fmtTime = s => { s = Math.floor(s); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
