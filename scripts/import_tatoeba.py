"""Tatoeba のネイティブの例文を content/tatoeba-cn.txt・tatoeba-tw.txt に取り込む。

使い方:  sh scripts/fetch_sources.sh && python3 scripts/import_tatoeba.py && python3 scripts/build_data.py

選ぶ文:
  - 中国語（cmn）を母語（レベル5）と登録している利用者が書いた文で、日本語訳が付いているもの
  - 漢字5〜30字の一文。ローマ字・数字・かなを含まない
  - 政治・暴力・性・罵り言葉などの語を含まない
字体と地域:
  - 簡体字だけの文 → 簡体字（大陸）の例文、繁體字だけの文 → 繁體字（台湾）の例文
  - どちらでも同じ字の文は両方に入れ、読みはそれぞれ大陸音・台湾音にする。両方の字体が混ざった文は捨てる
読み:
  - 語に分け、旧HSK・TOCFL 詞語表・CC-CEDICT から読みを決める。文脈がないと読みが決まらない字
    （得・地・長・行 など）が単独で出てくる文は、間違えるより捨てる
級と難易度:
  - build_data.py と同じ方法で級を判定し、初級（HSK1〜2・TOCFL準備〜入門）・中級・上級に振り分ける
直すとき:
  - 不自然な文や読みの誤りは、文の ID を content/tatoeba-exclude.txt に1行ずつ書いて外す
  - このスクリプトは content/tatoeba-*.txt を毎回作り直すので、そのファイルを直接直さない
ライセンス: Tatoeba の文は CC BY 2.0 FR。各文に元の文へのリンクを付ける。
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_data import (HAN, ROOT, SRC, TW_PR, citation, grade, load_cedict, load_hsk, load_tbcl,  # noqa: E402
                        to_zhuyin, vocab_levels)

T = SRC / "tatoeba"
MIN_HAN, MAX_HAN = 5, 30

BLOCK = """
政治 政府 政党 政黨 共产党 共產黨 国民党 國民黨 总统 總統 主席 总理 總理 选举 選舉 投票 民主 独裁 獨裁 革命 抗议 抗議
台独 台獨 统一 統一 两岸 兩岸 大陆 天安门 天安門 西藏 新疆 香港 习近平 習近平 毛泽东 毛澤東 蒋介石 蔣介石
战争 戰爭 军队 軍隊 士兵 枪 槍 炸弹 炸彈 恐怖 杀 殺 死 尸 屍 血 自杀 自殺 打架 强奸 強姦 绑架 綁架 犯罪 监狱 監獄 警察
毒品 吸毒 赌 賭 酒鬼 妓 色情 性 裸 屁 屎 尿 他妈 他媽 操 婊 傻逼 笨蛋 混蛋 滚 滾 去死 讨厌你 討厭你 恨 宗教 上帝 神
""".split()

# 単独で出てきたとき、文脈がないと読みが決まらない字（簡体字・繁體字）
AMBIGUOUS = set("得地长長种種干幹乾重行只隻数數处處差应應为為背调調传傳假藏降朝乐樂曾冲衝倒漂强強散薄弹彈参參卷捲结結系係繫")

# 語として見つからなかった1字に使う読み（ほぼこの読みでしか使われない字）
DEFAULT_CHAR = {
    "了": "le5", "的": "de5", "着": "zhe5", "著": "zhe5", "还": "hai2", "還": "hai2", "都": "dou1", "和": "he2",
    "好": "hao3", "要": "yao4", "看": "kan4", "大": "da4", "中": "zhong1", "便": "bian4", "分": "fen1",
    "难": "nan2", "難": "nan2", "少": "shao3", "发": "fa1", "發": "fa1", "相": "xiang1", "将": "jiang1", "將": "jiang1",
    "当": "dang1", "當": "dang1", "空": "kong1", "教": "jiao1", "觉": "jue2", "覺": "jue2", "没": "mei2", "沒": "mei2",
    "哪": "na3", "那": "na4", "吗": "ma5", "嗎": "ma5", "呢": "ne5", "吧": "ba5", "啊": "a5", "们": "men5", "們": "men5",
    "个": "ge4", "個": "ge4", "给": "gei3", "給": "gei3", "会": "hui4", "會": "hui4", "得": None,
}

# 台湾の標準音（教育部國語辭典）で、語の単位で台湾音にならなかった字に使う
TW_CHAR = {"期": {"qi1": "qi2"}, "危": {"wei1": "wei2"}, "微": {"wei1": "wei2"}, "企": {"qi3": "qi4"},
           "擁": {"yong1": "yong3"}, "暫": {"zan4": "zhan4"}, "綜": {"zong1": "zong4"}, "質": {"zhi4": "zhi2"},
           "液": {"ye4": "yi4"}, "究": {"jiu1": "jiu4"}, "攜": {"xie2": "xi1"}, "識": {"shi2": "shi4", "shi5": "shi4"},
           "和": {"he2": "han4"}}


def load_tatoeba(exclude):
    native = set()
    for line in (T / "user_languages.csv").open(encoding="utf-8"):
        c = line.rstrip("\n").split("\t")
        if len(c) >= 3 and c[0] == "cmn" and c[1] == "5":
            native.add(c[2])
    links = defaultdict(list)
    for line in (T / "cmn-jpn_links.tsv").open():
        a, b = line.split()
        links[a].append(b)
    cmn = []
    for line in (T / "cmn_sentences_detailed.tsv").open(encoding="utf-8"):
        c = line.rstrip("\n").split("\t")
        if c[0] in links and c[3] in native and c[0] not in exclude:
            cmn.append((c[0], c[2].strip()))
    want = {j for i, _ in cmn for j in links[i]}
    jpn = {}
    for line in (T / "jpn_sentences.tsv").open(encoding="utf-8"):
        c = line.rstrip("\n").split("\t")
        if c[0] in want:
            jpn[c[0]] = c[2].strip()
    return [(i, zh, next((jpn[j] for j in links[i] if j in jpn), None)) for i, zh in cmn]


class Reader:
    def __init__(self):
        self.words_t, self.char_rs, self.char_s, self.readings = load_cedict()
        rev = {}
        for syl in sorted({s for rs in self.readings.values() for s in rs}):
            try:
                rev.setdefault(to_zhuyin(syl), syl)
            except ValueError:
                pass
        self.tbcl, _ = load_tbcl(rev)
        self.hsk = load_hsk(self.tbcl)
        # 大陸の読み: 簡体語 -> 読み
        self.cn = {}
        for rows in self.hsk.values():
            for simp, _, syls, _ in rows:
                self.cn.setdefault(simp, [syls])
        cedict_s = defaultdict(list)
        for trad, entries in self.words_t.items():
            for simp, syls, _, proper in entries:
                if not proper and syls not in cedict_s[simp]:
                    cedict_s[simp].append(syls)
        for w, rs in cedict_s.items():
            self.cn.setdefault(w, rs)
        # 台湾の読み: 繁體語 -> 読み（TOCFL 詞語表の低い級 → CC-CEDICT の台湾音注記 → CC-CEDICT）
        self.tw = {}
        for lv, rows in sorted(self.tbcl.items()):
            for trad, tw in rows:
                self.tw.setdefault(trad, [tw])
        for trad, entries in self.words_t.items():
            rs = []
            for _, syls, _, proper in entries:
                tw = TW_PR.get((trad, tuple(syls)), syls)
                if not proper and tw not in rs:
                    rs.append(tw)
            self.tw.setdefault(trad, rs)
        # 字体の判定に使う: 簡体字にしかない字・繁體字にしかない字
        simp_chars, trad_chars = set(), set()
        for trad, entries in self.words_t.items():
            for simp, *_ in entries:
                if len(trad) == 1 and simp != trad:
                    simp_chars.add(simp)
                    trad_chars.add(trad)
        self.simp_only = simp_chars - trad_chars
        self.trad_only = trad_chars - simp_chars

    def script(self, text):
        han = set(HAN.findall(text))
        s, t = han & self.simp_only, han & self.trad_only
        if s and t:
            return None
        return "cn" if s else "tw" if t else "both"

    def lookup(self, w, variant):
        table = self.cn if variant == "cn" else self.tw
        return [r for r in table.get(w, []) if len(r) == len(w)]

    def word_reading(self, w, variant):
        """語（1字のことも）の読み。決められなければ None。"""
        rs = self.lookup(w, variant)
        if len(w) == 1:
            if w in AMBIGUOUS:
                return None
            if w in DEFAULT_CHAR and DEFAULT_CHAR[w] and (variant == "cn" or w not in TW_CHAR):
                return [DEFAULT_CHAR[w]]
            if not rs or (len({r[0] for r in rs}) > 1 and w not in DEFAULT_CHAR):
                return None
            return rs[0]
        if len({tuple(x) for x in rs}) > 1 and w not in self.hsk_words(variant):
            return None
        # 「一天又一天地」の「天地」のように、副詞の「地」「得」を語の一部と取り違えやすいので、
        # 語彙表にない語で「地」「得」で終わるものは使わない
        if w[-1] in "地得" and w not in self.hsk_words(variant):
            return None
        return rs[0] if rs else None

    def segment(self, run, variant, backward=False):
        """最長一致で語に分ける。backward なら後ろから。"""
        words, i, j = [], 0, len(run)
        while (j > 0) if backward else (i < len(run)):
            for n in range(min(6, (j if backward else len(run) - i)), 0, -1):
                w = run[j - n:j] if backward else run[i:i + n]
                if n == 1 or self.lookup(w, variant):
                    break
            if backward:
                words.insert(0, w)
                j -= n
            else:
                words.append(w)
                i += n
        return words

    def read(self, text, variant):
        """漢字1字に1音節の読み。決められなければ None。
        句読点で区切った範囲ごとに、前からと後ろからの最長一致で語に分け、読みが食い違えば捨てる。"""
        out = []
        for run in re.findall(r"[\u3400-\u9fff]+", text):
            results = []
            for backward in (False, True):
                syls = []
                for w in self.segment(run, variant, backward):
                    r = self.word_reading(w, variant)
                    if r is None:
                        return None
                    syls += r
                results.append(citation(run, syls))
            if results[0] != results[1]:
                return None
            out += results[0]
        han = HAN.findall(text)
        if variant == "tw":
            out = [TW_CHAR.get(ch, {}).get(s, s) for ch, s in zip(han, out)]
        return out

    def hsk_words(self, variant):
        if not hasattr(self, "_hsk_words"):
            self._hsk_words = {
                "cn": {simp for rows in self.hsk.values() for simp, *_ in rows},
                "tw": {trad for rows in self.tbcl.values() for trad, _ in rows},
            }
        return self._hsk_words[variant]


DIFFICULTY = {
    "cn": {1: "初級", 2: "初級", 3: "中級", 4: "中級", 5: "上級", 6: "上級"},           # 旧HSK
    "tw": {1: "初級", 2: "初級", 3: "中級", 4: "中級", 5: "上級", 6: "上級", 7: "上級"},  # TOCFL 準備級〜精通級
}

HEADER = {
    "cn": "# Tatoeba（https://tatoeba.org/ 、CC BY 2.0 FR）の、中国語を母語とする人が書いた例文（簡体字）。\n",
    "tw": "# Tatoeba（https://tatoeba.org/ 、CC BY 2.0 FR）の、中国語を母語とする人が書いた例文（繁體字）。\n",
}
COMMON = """# scripts/import_tatoeba.py が作るファイル。直接直さず、外したい文は content/tatoeba-exclude.txt に ID を書く。
# 書式: 本文 | 数字ピンイン（自動。{reading}） | 日本語訳（Tatoeba の訳） | 元の文の URL
"""


def main():
    ex_path = ROOT / "content/tatoeba-exclude.txt"
    exclude = set()
    if ex_path.exists():
        exclude = {l.split()[0] for l in ex_path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    rows = load_tatoeba(exclude)
    rd = Reader()
    vocab = {
        "cn": (vocab_levels({lv: [[r[0]] for r in rs] for lv, rs in rd.hsk.items()}, 0), 7),
        "tw": (vocab_levels({lv: [[t] for t, _ in rs] for lv, rs in rd.tbcl.items()}, 0), 8),
    }
    out = {"cn": defaultdict(list), "tw": defaultdict(list)}
    seen = {"cn": set(), "tw": set()}
    stats = defaultdict(int)
    for sid, zh, ja in rows:
        han = HAN.findall(zh)
        if not ja or not (MIN_HAN <= len(han) <= MAX_HAN):
            stats["長さ・訳なし"] += 1
            continue
        if re.search(r"[A-Za-z0-9０-９Ａ-Ｚａ-ｚ぀-ヿ|]", zh) or "|" in ja:
            stats["ローマ字・数字・かな"] += 1
            continue
        if any(b in zh for b in BLOCK):
            stats["話題"] += 1
            continue
        if not re.search(r"[。！？…」”]$", zh):
            zh += "。"
        sc = rd.script(zh)
        if sc is None:
            stats["字体が混在"] += 1
            continue
        for variant in (("cn", "tw") if sc == "both" else (sc,)):
            if zh in seen[variant]:
                continue
            py = rd.read(zh, variant)
            if not py:
                stats[f"読みが決まらない({variant})"] += 1
                continue
            vc, beyond = vocab[variant]
            lv = grade(zh, vc, beyond)
            d = DIFFICULTY[variant].get(lv)
            if not d:
                stats[f"級外({variant})"] += 1
                continue
            seen[variant].add(zh)
            out[variant][d].append(f"{zh} | {' '.join(py)} | {ja} | https://tatoeba.org/ja/sentences/show/{sid}")
    for variant, reading in (("cn", "大陸の標準音"), ("tw", "台湾の標準音")):
        lines = [HEADER[variant] + COMMON.format(reading=reading)]
        for d in ("初級", "中級", "上級"):
            lines.append(f"\n## {d} 一文")
            lines += sorted(out[variant][d], key=len)
        (ROOT / f"content/tatoeba-{variant}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(variant, {d: len(v) for d, v in out[variant].items()})
    print("除外:", dict(stats))


if __name__ == "__main__":
    main()
