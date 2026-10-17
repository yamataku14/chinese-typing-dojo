"""sources/ の公開データと content/ の自作例文から、サイトが読む data/*.json を作る。

使い方:  sh scripts/fetch_sources.sh && python3 scripts/build_data.py

出力（どれも [簡体字, 繁体字, 大陸の読み, 意味, 台湾の読み] の配列。台湾の読みは大陸と同じなら省く）:
  読みは数字ピンイン。「一」「不」は変調前の本来の声調にそろえる。
  台湾の読みは TBCL の注音、CC-CEDICT の「Taiwan pr.」注記の順で決める。
  単語の意味は content/glossary-ja.tsv に日本語訳があればそれを、なければ CC-CEDICT の英語を使う。
  data/words/hsk-1.json … hsk-6.json     旧HSK 1〜6級
  data/words/tocfl-1.json … tocfl-7.json TBCL 詞語表 第1〜7級（TOCFLの基準。内部名は tocfl のまま）
  data/texts/all.json  一文・長文（content/texts.txt と、時事の例文 content/news.txt）
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from phonetics import split, to_zhuyin  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = ROOT / "data"
HAN = re.compile(r"[㐀-鿿]")
ALL_HAN = re.compile(r"[㐀-鿿]+")


def norm_syl(s):
    s = s.lower().replace("u:", "v").replace("ü", "v")
    base, tone = split(s)
    return f"{base}{tone}"


# ---------- 読みの正規化 ----------
def citation(text, syls):
    """「一」「不」の変調（yi2, yi4, bu2）を本来の声調（yi1, bu4）に戻す。"""
    han = [c for c in text if HAN.match(c)]
    if len(han) != len(syls):
        return syls
    out = []
    for ch, s in zip(han, syls):
        if ch == "一" and s[:-1] == "yi":
            s = "yi1"
        elif ch == "不" and s[:-1] == "bu":
            s = "bu4"
        out.append(s)
    return out


def eq_loose(a, b):
    """同じ読みか。軽声（5）と本来の声調の違いは同じとみなす。"""
    return len(a) == len(b) and all(x == y or (x[:-1] == y[:-1] and "5" in (x[-1], y[-1])) for x, y in zip(a, b))


def bases(syls):
    return [s[:-1] for s in syls]


# ---------- CC-CEDICT ----------
TAIWAN_PR = re.compile(r"Taiwan pr\. \[([^\]]+)\]")
PY_SYL = re.compile(r"[a-zü:]+[1-5]")
TW_PR = {}                                # (繁体語, 大陸の読み) -> 台湾の読み
CEDICT_LINE = re.compile(r"^(\S+) (\S+) \[([^\]]+)\] /(.+)/$")


def load_cedict():
    words_t = defaultdict(list)          # 繁体語 -> [(簡体, ピンイン, 定義, 固有名詞か)]
    char_rs = {}                          # (繁体字, 音節) -> 簡体字
    char_s = {}                           # 繁体字 -> 簡体字（読みを問わない）
    readings = defaultdict(set)           # 漢字 -> 読みの集合
    for line in (SRC / "cedict/cedict.txt").open(encoding="utf-8"):
        if line.startswith("#"):
            continue
        m = CEDICT_LINE.match(line.strip())
        if not m:
            continue
        trad, simp, py, defs = m.groups()
        try:
            syls = [norm_syl(x) for x in py.split()]
        except ValueError:
            continue
        syls = citation(trad, syls)
        words_t[trad].append((simp, syls, defs, py[:1].isupper()))
        for tw in TAIWAN_PR.findall(defs):
            tws = PY_SYL.findall(tw.lower())
            try:
                tws = citation(trad, [norm_syl(x) for x in tws])
            except ValueError:
                continue
            if len(tws) == len(syls):
                TW_PR[(trad, tuple(syls))] = tws
        if len(trad) == 1 and len(syls) == 1:
            char_rs.setdefault((trad, syls[0]), simp)
            char_s.setdefault(trad, simp)
            readings[trad].add(syls[0])
            readings[simp].add(syls[0])
    return words_t, char_rs, char_s, readings


def t2s(trad, syls, words_t, char_rs, char_s):
    """繁体字を簡体字に。語として辞書にあればそれを、なければ読みを手がかりに1字ずつ。"""
    for simp, wsyls, *_ in words_t.get(trad, []):
        if [s.rstrip("5") for s in wsyls] == [s.rstrip("5") for s in syls] or len(words_t[trad]) == 1:
            if len(simp) == len(trad):
                return simp
    out, k = [], 0
    for ch in trad:
        if HAN.match(ch):
            syl = syls[k] if k < len(syls) else None
            k += 1
            out.append(char_rs.get((ch, syl)) or char_s.get(ch, ch))
        else:
            out.append(ch)
    return "".join(out)


def gloss(defs, limit=70):
    parts = [d for d in defs.split("/") if d and not d.startswith(("variant of", "old variant", "see ", "CL:", "surname"))]
    text = "; ".join(parts[:3])
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def cedict_gloss(trad, syls, words_t):
    """読みが一致し、固有名詞でない見出しを優先して英語の意味を返す。"""
    cands = words_t.get(trad, [])
    tiers = [
        [c for c in cands if c[1] == syls and not c[3]],
        [c for c in cands if [s[:-1] for s in c[1]] == [s[:-1] for s in syls] and not c[3]],
        [c for c in cands if not c[3]],
        cands,
    ]
    for tier in tiers:
        for c in tier:
            g = gloss(c[2])
            if g:
                return g
    return ""


# ---------- 日本語訳 ----------
def load_glossary():
    """content/glossary-ja.tsv を読む。書式: 繁体字 \t 数字ピンイン \t 日本語の意味"""
    gl = defaultdict(dict)                # 繁体字 -> {数字ピンイン: 日本語}
    path = ROOT / "content/glossary-ja.tsv"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                trad, py, ja = line.split("\t")
                gl[trad][py] = ja
    return gl


def same_but_neutral(a, b):
    """軽声（5）の有無だけが違う読みか。"""
    a, b = a.split(), b.split()
    return len(a) == len(b) and all(x == y or x[:-1] == y[:-1] and "5" in (x[-1], y[-1]) for x, y in zip(a, b))


def apply_glossary(items, gl):
    """読みが一致すれば日本語訳に置き換える（大陸・台湾どちらの読みでもよい）。
    軽声だけ違うものは訳が1つに決まるときだけ使う。"""
    hit = 0
    for it in items:
        cands = gl.get(it[1], {})
        readings = [it[2]] + ([it[4]] if len(it) > 4 else [])
        ja = next((cands[r] for r in readings if r in cands), None)
        if not ja:
            near = {v for py, v in cands.items() for r in readings if same_but_neutral(py, r)}
            ja = near.pop() if len(near) == 1 else None
        if ja:
            it[3] = ja
            hit += 1
    return hit


# ---------- HSK（旧HSK 1〜6級） ----------
MINOR_SENSE = ("surname", "variant of", "old variant", "unofficial variant", "used in", "see ")


def pick_hsk_form(simp, forms, tbcl_tw):
    """複数の読みがある語から主な読みを選ぶ。
    固有名詞・異体字・「〜に使う」だけの読みを除き、台湾の TBCL の読みと合うもの、
    なければ語義の多いものを選ぶ。"""
    cands = []
    for f in forms:
        py = f["transcriptions"]["numeric"]
        try:
            syls = citation(f["traditional"], [norm_syl(x) for x in py.split()])
        except ValueError:
            continue
        minor = py[:1].isupper() or all(m.startswith(MINOR_SENSE) for m in f["meanings"])
        cands.append((f, syls, minor))
    if not cands:
        return None
    major = [c for c in cands if not c[2]] or cands
    # TBCL で同じ字に複数の読みがあれば、低い級（基本的な読み）を優先する
    trads = {f["traditional"] for f, _, _ in major}
    tws = [tw for _, tw in sorted(x for t in trads for x in tbcl_tw.get(t, []))]
    for match in (lambda f, syls, tw: syls == tw or TW_PR.get((f["traditional"], tuple(syls))) == tw,
                  lambda f, syls, tw: eq_loose(tw, syls)):
        for tw in tws:
            for f, syls, _ in major:
                if match(f, syls, tw):
                    return f, syls
    f, syls, _ = max(major, key=lambda c: len(c[0]["meanings"]))
    return f, syls


def load_hsk(tbcl):
    """{級: [(簡体, 繁体, 読み, 意味)]}。読みは大陸の読み。"""
    tbcl_tw = defaultdict(list)
    for lv, rows in tbcl.items():
        for trad, tw in rows:
            tbcl_tw[trad].append((lv, tw))
    out = {}
    for lv in range(1, 7):
        rows, seen = [], set()
        for e in json.loads((SRC / f"hsk/old-{lv}.json").read_text(encoding="utf-8")):
            simp = e["simplified"]
            picked = pick_hsk_form(simp, e["forms"], tbcl_tw)
            if not picked:
                continue
            f, syls = picked
            trad = f["traditional"]
            if not ALL_HAN.fullmatch(simp) or len(simp) != len(syls) or len(trad) != len(simp) or simp in seen:
                continue
            seen.add(simp)
            rows.append((simp, trad, syls, "/".join(f["meanings"])))
        out[lv] = rows
    return out


# ---------- TBCL 詞語表（ファイル名・内部名は tocfl） ----------
ZY_SYL = re.compile(r"˙?[ㄅ-ㄙ]?[ㄧㄨㄩ]?[ㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ]?[ˊˇˋ]?")


def zy_tokens(zy):
    toks = []
    for chunk in zy.split():
        pos = 0
        while pos < len(chunk):
            m = ZY_SYL.match(chunk, pos)
            if not m or m.end() == pos:
                return None
            toks.append(m.group())
            pos = m.end()
    return toks


def load_tbcl(rev):
    """{級: [(繁体, 台湾の読み)]} と、読みを揃えられず除いた語数。"""
    out = defaultdict(list)
    skipped = 0
    for line in (SRC / "tocfl/tocfl_words.json").open(encoding="utf-8"):
        r = json.loads(line)
        trad = r["text"]
        toks = zy_tokens(r["zhuyin"]) if ALL_HAN.fullmatch(trad) else None
        syls = [rev.get(t) for t in toks] if toks else None
        if not syls or None in syls or len(syls) != len(trad):
            skipped += 1
            continue
        out[r["tocfl_level"]].append((trad, citation(trad, syls)))
    return out, skipped


# ---------- 大陸の読みと台湾の読み ----------
class Readings:
    """語ごとに大陸の読みと台湾の読みを対応づける。

    大陸の読み: 旧HSK → CC-CEDICT（Taiwan pr. 注記・音節の一致から逆引き）
    台湾の読み: TBCL の注音 → CC-CEDICT の Taiwan pr. 注記 → 大陸と同じ
    """

    def __init__(self, hsk, tbcl, words_t):
        self.words_t = words_t
        self.hsk_cn = {}                      # 繁体語 -> 大陸の読み
        for rows in hsk.values():
            for _, trad, syls, _ in rows:
                self.hsk_cn.setdefault(trad, syls)
        self.tbcl_tw = defaultdict(list)      # 繁体語 -> [(台湾の読み, 対応する大陸の読み)]
        for rows in tbcl.values():
            for trad, tw in rows:
                if all(tw != x[0] for x in self.tbcl_tw[trad]):
                    self.tbcl_tw[trad].append((tw, self.cn_for_tw(trad, tw)))

    def cn_for_tw(self, trad, tw):
        if trad in self.hsk_cn and len(self.hsk_cn[trad]) == len(tw):
            cn = self.hsk_cn[trad]
            if bases(cn) == bases(tw) or TW_PR.get((trad, tuple(cn))) == tw:
                return cn
        cands = [c for c in self.words_t.get(trad, []) if not c[3] and len(c[1]) == len(tw)]
        for c in cands:
            if c[1] == tw:
                return tw
        for c in cands:
            if TW_PR.get((trad, tuple(c[1]))) == tw:
                return c[1]
        same = [c for c in cands if bases(c[1]) == bases(tw)]
        if same:
            return max(same, key=lambda c: sum(x == y for x, y in zip(c[1], tw)))[1]
        if trad in self.hsk_cn and len(self.hsk_cn[trad]) == len(tw):
            return self.hsk_cn[trad]
        return tw

    def tw_for_cn(self, trad, cn):
        """大陸の読みに対応する台湾の読み。見つからなければ None。"""
        for tw, tcn in self.tbcl_tw.get(trad, []):
            if eq_loose(tcn, cn):
                return tw
        return TW_PR.get((trad, tuple(cn)))

    def text_tw(self, trad, cn):
        """例文（1字ずつの大陸の読み）を、語の単位で台湾の読みに置き換える。最長一致。"""
        han = [c for c in trad if HAN.match(c)]
        out, i = list(cn), 0
        while i < len(han):
            for n in range(min(6, len(han) - i), 0, -1):
                tw = self.tw_for_cn("".join(han[i:i + n]), cn[i:i + n])
                if tw:
                    out[i:i + n] = tw
                    i += n
                    break
            else:
                i += 1
        return out


# ---------- 読みの訂正 ----------
def load_corrections():
    """content/corrections.tsv を読む。書式: 繁体語 \t 大陸の読み \t 台湾の読み（大陸と同じなら空）
    報告を受けて読みを直すときはここに1行足す。単語データのすべての級に効く。"""
    out = {}
    path = ROOT / "content/corrections.tsv"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                cols = line.split("\t") + [""]
                trad, cn, tw = cols[0].strip(), cols[1].strip(), cols[2].strip()
                out[trad] = (citation(trad, cn.split()), citation(trad, tw.split()) if tw else None)
    return out


def apply_corrections(items, corr):
    n = 0
    for it in items:
        if it[1] in corr:
            cn, tw = corr[it[1]]
            del it[4:]
            it[2] = " ".join(cn)
            if tw and tw != cn:
                it.append(" ".join(tw))
            n += 1
    return n


def word_item(simp, trad, cn, tw, meaning):
    item = [simp, trad, " ".join(cn), meaning]
    if tw and tw != cn:
        item.append(" ".join(tw))
    return item


def build_hsk(hsk, rd, words_t):
    out = {}
    for lv, rows in hsk.items():
        out[lv] = [
            word_item(simp, trad, cn, rd.tw_for_cn(trad, cn), gloss(meanings) or cedict_gloss(trad, cn, words_t))
            for simp, trad, cn, meanings in rows
        ]
    return out


def build_tocfl(tbcl, rd, words_t, char_rs, char_s):
    out = {}
    for lv, rows in tbcl.items():
        items = []
        for trad, tw in rows:
            cn = rd.cn_for_tw(trad, tw)
            simp = t2s(trad, cn, words_t, char_rs, char_s)
            items.append(word_item(simp, trad, cn, tw, cedict_gloss(trad, cn, words_t)))
        out[lv] = items
    return out


# ---------- 自作の例文 ----------
LEVELS = {"初級": "beginner", "中級": "intermediate", "上級": "advanced", "超級": "expert"}
LENGTHS = {"一文": "sentence", "長文": "passage"}


TEXT_FILES = ["content/texts.txt", "content/news.txt"]


def text_lines():
    """(ファイル名:行番号, 行) を順に返す。news.txt はなくてもよい。"""
    for name in TEXT_FILES:
        path = ROOT / name
        if path.exists():
            for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                yield f"{path.name}:{n}", raw


def build_texts(rd, char_rs, char_s, readings):
    """content/texts.txt と content/news.txt を読む。書式:
        ## 初級 一文
        繁体字の本文 | 数字ピンイン（大陸の読み。漢字1字に1音節） | 日本語訳 [| 出典 URL]
    台湾の読みは語の単位で自動で付ける。4列目の出典（時事の例文）は src として出力する。
    返す例文は (配列, 出典) の組。
    """
    out = {v: {"sentence": [], "passage": []} for v in LEVELS.values()}
    level = length = None
    errors, warnings = [], []
    for n, raw in text_lines():
        line = raw.strip()
        if not line or line.startswith("#") and not line.startswith("##"):
            continue
        if line.startswith("##"):
            lv, ln = line[2:].split()
            level, length = LEVELS[lv], LENGTHS[ln]
            continue
        cols = [x.strip() for x in line.split("|")]
        if len(cols) not in (3, 4):
            errors.append(f"{n}: 列の数が {len(cols)}（3 か 4 にする）")
            continue
        trad, py, ja = cols[:3]
        src = cols[3] if len(cols) == 4 else None
        if src is not None and not re.fullmatch(r"https?://\S+", src):
            errors.append(f"{n}: 出典は http(s) の URL にする  {src}")
            continue
        han = HAN.findall(trad)
        try:
            syls = [norm_syl(x) for x in py.split()]
        except ValueError as e:
            errors.append(f"{n}: 読みの書式 {e}")
            continue
        if len(han) != len(syls):
            errors.append(f"{n}: 漢字 {len(han)} 字に対して読みが {len(syls)} 音節  {trad}")
            continue
        syls = citation(trad, syls)
        for ch, syl in zip(han, syls):
            rs = readings.get(ch)
            if rs and syl not in rs and syl[:-1] + "5" not in rs and not syl.endswith("5"):
                warnings.append(f"{n}: {ch} を {syl} と読んでいる（辞書: {'/'.join(sorted(rs))}）")
        simp = t2s_text(trad, syls, char_rs, char_s)
        item = [simp, trad, " ".join(syls), ja]
        tw = rd.text_tw(trad, syls)
        if tw != syls:
            item.append(" ".join(tw))
        out[level][length].append((item, src))
    return out, errors, warnings


# ---------- 例文の級の自動判定 ----------
COVERAGE = 0.9   # 語の9割がその級までの語彙で書けていれば「その級相当」とする
NUMERALS = set("零一二三四五六七八九十百千萬万兩两")
# 固有名詞は級の判定に数えない（1級扱い）
PROPER_NOUNS = {"台灣", "台湾", "臺灣", "臺北", "台北", "東京", "东京", "田中", "王明", "臺北市", "台北市"}


def vocab_levels(items_by_level, key):
    """{語: いちばん低い級} と {字: その字を含む語のいちばん低い級}"""
    words, chars = {}, {}
    for lv, items in sorted(items_by_level.items()):
        for it in items:
            words.setdefault(it[key], lv)
            for ch in it[key]:
                chars.setdefault(ch, lv)
    for w in PROPER_NOUNS:
        words[w] = 1
    return words, chars


def grade(text, vocab, beyond):
    """本文を最長一致で語に分け、語の COVERAGE 割をカバーする最小の級を返す。
    語彙表にない1字は、その字を含む語のいちばん低い級で数え、それもなければ beyond（級外）。
    数字は1級扱い。"""
    vocab, chars = vocab
    levels = []
    for run in re.findall(r"[㐀-鿿]+", text):
        i = 0
        while i < len(run):
            for n in range(min(6, len(run) - i), 0, -1):
                w = run[i:i + n]
                if w in vocab:
                    levels.append(vocab[w])
                    break
                if n == 1:
                    levels.append(1 if w in NUMERALS else chars.get(w, beyond))
            i += n
    if not levels:
        return 1
    for lv in range(1, beyond + 1):
        if sum(x <= lv for x in levels) >= COVERAGE * len(levels):
            return lv
    return beyond


def t2s_text(trad, syls, char_rs, char_s):
    out, k = [], 0
    for ch in trad:
        if HAN.match(ch):
            syl = syls[k]
            k += 1
            out.append(char_rs.get((ch, syl)) or char_rs.get((ch, syl[:-1] + "5")) or char_s.get(ch, ch))
        else:
            out.append(ch)
    return "".join(out).replace("「", "“").replace("」", "”").replace("『", "‘").replace("』", "’")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    words_t, char_rs, char_s, readings = load_cedict()
    all_syls = {s for rs in readings.values() for s in rs}
    rev = {}
    for syl in sorted(all_syls):
        try:
            rev.setdefault(to_zhuyin(syl), syl)
        except ValueError:
            pass

    tbcl, skipped = load_tbcl(rev)
    hsk = load_hsk(tbcl)
    rd = Readings(hsk, tbcl, words_t)

    glossary = load_glossary()
    corrections = load_corrections()
    ja_hits, tw_diff = [], []
    manifest = {"hsk": {}, "tocfl": {}, "texts": {}}
    for lv, items in build_hsk(hsk, rd, words_t).items():
        apply_corrections(items, corrections)
        ja_hits.append(f"HSK{lv} {apply_glossary(items, glossary)}/{len(items)}")
        tw_diff.append(f"HSK{lv} {sum(len(i) > 4 for i in items)}")
        write(OUT / f"words/hsk-{lv}.json", items)
        manifest["hsk"][lv] = len(items)
    for lv, items in sorted(build_tocfl(tbcl, rd, words_t, char_rs, char_s).items()):
        apply_corrections(items, corrections)
        ja_hits.append(f"TBCL{lv} {apply_glossary(items, glossary)}/{len(items)}")
        tw_diff.append(f"TBCL{lv} {sum(len(i) > 4 for i in items)}")
        write(OUT / f"words/tocfl-{lv}.json", items)
        manifest["tocfl"][lv] = len(items)

    texts, errors, warnings = build_texts(rd, char_rs, char_s, readings)
    hsk_vocab = vocab_levels({lv: build for lv, build in ((lv, [[r[0]] for r in rows]) for lv, rows in hsk.items())}, 0)
    tbcl_vocab = vocab_levels({lv: [[t] for t, _ in rows] for lv, rows in tbcl.items()}, 0)
    all_texts = []
    for diff, d in texts.items():
        for length, items in d.items():
            for it, src in items:
                obj = {"s": it[0], "t": it[1], "p": it[2], "ja": it[3], "d": diff, "l": length,
                       "hsk": grade(it[0], hsk_vocab, 7), "tbcl": grade(it[1], tbcl_vocab, 8)}
                if len(it) > 4:
                    obj["tw"] = it[4]
                if src:
                    obj["src"] = src
                all_texts.append(obj)
        manifest["texts"][diff] = {k: len(v) for k, v in d.items()}
    write(OUT / "texts/all.json", all_texts)
    for old in (OUT / "texts").glob("*.json"):
        if old.name != "all.json":
            old.unlink()
    from collections import Counter
    grid = Counter((o["l"], o["d"], o["hsk"], o["tbcl"]) for o in all_texts)
    print("例文の級（長さ, 難易度, HSK, TBCL）:", sorted(grid.items()))
    write(OUT / "manifest.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False))
    print(f"TBCL: 読みを揃えられず除外 {skipped} 語")
    print("日本語訳:", "  ".join(ja_hits))
    print("台湾の読みが大陸と違う語:", "  ".join(tw_diff))
    for w in warnings:
        print("注意", w)
    for e in errors:
        print("エラー", e)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
