"""sources/ の公開データと content/ の自作例文から、サイトが読む data/*.json を作る。

使い方:  sh scripts/fetch_sources.sh && python3 scripts/build_data.py

出力（どれも [簡体字, 繁体字, 数字ピンイン, 意味] の配列）:
  単語の意味は content/glossary-ja.tsv に日本語訳があればそれを、なければ CC-CEDICT の英語を使う。
  data/words/hsk-1.json … hsk-6.json     旧HSK 1〜6級
  data/words/tocfl-1.json … tocfl-7.json TOCFL 詞語表 第1〜7級
  data/texts/{beginner,intermediate,advanced,expert}.json  一文・長文
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


# ---------- CC-CEDICT ----------
CEDICT_LINE = re.compile(r"^(\S+) (\S+) \[([^\]]+)\] /(.+)/$")


def load_cedict():
    words_t = defaultdict(list)          # 繁体語 -> [(簡体, ピンイン, 定義)]
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
        words_t[trad].append((simp, syls, defs, py[:1].isupper()))
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
    """読みが一致すれば日本語訳に置き換える。軽声だけ違うものは訳が1つに決まるときだけ使う。"""
    hit = 0
    for it in items:
        cands = gl.get(it[1], {})
        ja = cands.get(it[2])
        if not ja:
            near = {v for py, v in cands.items() if same_but_neutral(py, it[2])}
            ja = near.pop() if len(near) == 1 else None
        if ja:
            it[3] = ja
            hit += 1
    return hit


# ---------- HSK（旧HSK 1〜6級） ----------
def build_hsk(words_t):
    out = {}
    for lv in range(1, 7):
        items, seen = [], set()
        for e in json.loads((SRC / f"hsk/old-{lv}.json").read_text(encoding="utf-8")):
            simp = e["simplified"]
            f = e["forms"][0]
            trad = f["traditional"]
            try:
                syls = [norm_syl(x) for x in f["transcriptions"]["numeric"].split()]
            except ValueError:
                continue
            if not ALL_HAN.fullmatch(simp) or len(simp) != len(syls) or len(trad) != len(simp) or simp in seen:
                continue
            seen.add(simp)
            mean = gloss("/".join(f["meanings"])) or cedict_gloss(trad, syls, words_t)
            items.append([simp, trad, " ".join(syls), mean])
        out[lv] = items
    return out


# ---------- TOCFL 詞語表 ----------
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


def build_tocfl(rev, words_t, char_rs, char_s):
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
        simp = t2s(trad, syls, words_t, char_rs, char_s)
        out[r["tocfl_level"]].append([simp, trad, " ".join(syls), cedict_gloss(trad, syls, words_t)])
    return out, skipped


# ---------- 自作の例文 ----------
LEVELS = {"初級": "beginner", "中級": "intermediate", "上級": "advanced", "超級": "expert"}
LENGTHS = {"一文": "sentence", "長文": "passage"}


def build_texts(words_t, char_rs, char_s, readings):
    """content/texts.txt を読む。書式:
        ## 初級 一文
        繁体字の本文 | 数字ピンイン（漢字1字に1音節） | 日本語訳
    """
    out = {v: {"sentence": [], "passage": []} for v in LEVELS.values()}
    level = length = None
    errors, warnings = [], []
    for n, raw in enumerate((ROOT / "content/texts.txt").read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") and not line.startswith("##"):
            continue
        if line.startswith("##"):
            lv, ln = line[2:].split()
            level, length = LEVELS[lv], LENGTHS[ln]
            continue
        trad, py, ja = [x.strip() for x in line.split("|")]
        han = HAN.findall(trad)
        try:
            syls = [norm_syl(x) for x in py.split()]
        except ValueError as e:
            errors.append(f"{n}: 読みの書式 {e}")
            continue
        if len(han) != len(syls):
            errors.append(f"{n}: 漢字 {len(han)} 字に対して読みが {len(syls)} 音節  {trad}")
            continue
        for ch, syl in zip(han, syls):
            rs = readings.get(ch)
            if rs and syl not in rs and syl[:-1] + "5" not in rs and not syl.endswith("5"):
                warnings.append(f"{n}: {ch} を {syl} と読んでいる（辞書: {'/'.join(sorted(rs))}）")
        simp = t2s_text(trad, syls, char_rs, char_s)
        out[level][length].append([simp, trad, " ".join(syls), ja])
    return out, errors, warnings


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

    glossary = load_glossary()
    ja_hits = []
    manifest = {"hsk": {}, "tocfl": {}, "texts": {}}
    for lv, items in build_hsk(words_t).items():
        ja_hits.append(f"HSK{lv} {apply_glossary(items, glossary)}/{len(items)}")
        write(OUT / f"words/hsk-{lv}.json", items)
        manifest["hsk"][lv] = len(items)
    tocfl, skipped = build_tocfl(rev, words_t, char_rs, char_s)
    for lv, items in sorted(tocfl.items()):
        ja_hits.append(f"TOCFL{lv} {apply_glossary(items, glossary)}/{len(items)}")
        write(OUT / f"words/tocfl-{lv}.json", items)
        manifest["tocfl"][lv] = len(items)

    texts, errors, warnings = build_texts(words_t, char_rs, char_s, readings)
    for lv, d in texts.items():
        write(OUT / f"texts/{lv}.json", d)
        manifest["texts"][lv] = {k: len(v) for k, v in d.items()}
    write(OUT / "manifest.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False))
    print(f"TOCFL: 読みを揃えられず除外 {skipped} 語")
    print("日本語訳:", "  ".join(ja_hits))
    for w in warnings:
        print("注意", w)
    for e in errors:
        print("エラー", e)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
