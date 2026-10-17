// 設定の表示名など、練習画面と記録画面で共有するもの

export const LEVELS = {
  hsk: [1, 2, 3, 4, 5, 6].map(n => [n, `${n}級`]),
  // TOCFL の級。データは台湾の語彙基準（TBCL）の第1〜7級で、華測会の等級対照に従って TOCFL の級に当てている
  tocfl: [[1, "準備級"], [2, "入門級（1級）"], [3, "基礎級（2級）"], [4, "進階級（3級）"], [5, "高階級（4級）"], [6, "流利級（5級）"], [7, "精通級（6級）"]],
};
export const NAMES = {
  script: { simp: "簡体字", trad: "繁體字" },
  input: { pinyin: "ピンイン", tone: "ピンイン＋声調", zhuyin: "注音" },
  length: { word: "単語", sentence: "一文", passage: "長文" },
  difficulty: { beginner: "初級", intermediate: "中級", advanced: "上級", expert: "超級" },
  source: { hsk: "HSK", tocfl: "TOCFL" },
};
// 例文の級の表示（判定値が最大級を超えると「〜級超」）
export const TEXT_LEVEL_MAX = { hsk: 6, tbcl: 7 };
// 例文の級の内部名は "tbcl" のまま（記録との互換のため）。表示は TOCFL の級名
export function textLevelName(basis, lv) {
  if (basis === "tbcl") {
    const top = LEVELS.tocfl[LEVELS.tocfl.length - 1][1].replace(/（.*/, "");
    return lv > TEXT_LEVEL_MAX.tbcl ? `TOCFL ${top}超` : `TOCFL ${LEVELS.tocfl[lv - 1][1].replace(/（.*/, "")}相当`;
  }
  return lv > TEXT_LEVEL_MAX.hsk ? `HSK ${TEXT_LEVEL_MAX.hsk}級超` : `HSK ${lv}級相当`;
}

export function describe(s) {
  const what = s.length === "word"
    ? `${NAMES.source[s.source]} ${(LEVELS[s.source].find(l => l[0] === s.level) || [0, ""])[1]}`
    : `${NAMES.length[s.length]}・${!s.textBasis || s.textBasis === "difficulty" ? NAMES.difficulty[s.difficulty] : textLevelName(s.textBasis, s.textLevel)}`;
  return `${what}・${NAMES.script[s.script]}・${NAMES.input[s.input]}`;
}

export const fmtTime = s => { s = Math.floor(s); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
