"""ニュースの話題をもとにした例文を作り、content/news-cn.txt と news-tw.txt に足す（GitHub Actions から1日1回実行）。

使い方:
  ANTHROPIC_API_KEY=... python3 scripts/generate_news.py [--report 報告.md]
  python3 scripts/generate_news.py --sample 応答.json   # API を呼ばず、保存した応答で試す

流れ:
  1. FEEDS の RSS から見出しと概要だけを取る（本文は取らない）。
  2. 政治的に敏感な話題・事件・事故を BLOCK の語で除く。既に使った記事も除く。
  3. Claude に、記事の文を写さず事実だけを使ったオリジナルの短文と日本語訳を書かせる。
     同じ内容を、簡体字・大陸の普通話（大陸の発音）と、繁體字・台湾の国語（台湾の発音）の2通りで書く。
  4. 読みは辞書（CC-CEDICT。台湾の読みは Taiwan pr. 注記と TOCFL 詞語表も）で照合する。
     辞書で読みが1つに決まる語は辞書の読みにそろえ、決まらないのに食い違うものは「要確認」として残す。
  5. content/news-cn.txt・news-tw.txt の末尾に、出典 URL 付きで追記する。公開前に Pull Request で人が確認する。
"""
import argparse
import datetime
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_data import HAN, ROOT, TW_PR, citation, load_cedict, load_tbcl, norm_syl, to_zhuyin  # noqa: E402

NEWS = {"cn": ROOT / "content/news-cn.txt", "tw": ROOT / "content/news-tw.txt"}
MODEL = "claude-sonnet-5-5"

# 見出しと概要だけを使う。利用規約は各社のものを確認すること。
FEEDS = [
    ("https://www3.nhk.or.jp/rss/news/cat3.xml", "NHK 科学・医療"),
    ("https://www3.nhk.or.jp/rss/news/cat2.xml", "NHK 文化・エンタメ"),
    ("https://www3.nhk.or.jp/rss/news/cat5.xml", "NHK 経済"),
    ("https://www3.nhk.or.jp/rss/news/cat7.xml", "NHK スポーツ"),
]
MAX_CANDIDATES = 15

# 見出し・概要にこれらの語があれば使わない（政治・両岸関係・事件・事故・災害・病気など）
BLOCK = """
政治 政府 政権 首相 大統領 主席 総統 大臣 外相 防衛 議員 国会 議会 選挙 投票 与党 野党 党 外交 首脳 会談 制裁 関税 条約
中国 台湾 中台 両岸 香港 マカオ チベット ウイグル 尖閣 竹島 北方領土 北朝鮮 ロシア ウクライナ イスラエル パレスチナ ガザ イラン
軍 ミサイル 核 戦争 紛争 攻撃 空爆 テロ 銃 爆発 デモ 抗議
事件 事故 犯罪 捜査 警察 警視庁 トクリュウ 死亡 死去 死者 亡くな 遺体 殺 逮捕 容疑 被告 判決 裁判 起訴 詐欺 盗 暴行 虐待 性的 わいせつ 自殺 不祥事 不正
火災 火事 地震 津波 台風 豪雨 大雨 洪水 土砂 噴火 災害 避難 被害 行方不明 けが 負傷 重体 墜落 衝突 脱線 倒産
感染 ウイルス がん 病 患者 薬物 違法
""".split()

SYSTEM = """あなたは中国語学習サイトの例文作家です。日本人の学習者がタイピング練習に使う、短い中国語の例文を書きます。

与えられるのはニュースの見出しと概要だけです。次を守ってください。
- 記事の文章を写したり、見出しをそのまま訳したりしない。使ってよいのは事実（誰が・何を・いつ）だけで、文は自分の言葉で書く。
  例:「聽說今年秋天有新的太空望遠鏡要升空。」のように、学習者が会話や日記で言いそうな文にする。
- 政治・外交・両岸関係・領土・軍事・選挙・政治家、事件・事故・犯罪・災害・死・病気、個人の私生活に関わる話題は使わない。
  迷ったら使わない。使える話題がなければ items を空にしてよい。
- 同じ内容の文を2通り書く。
  zh_cn: 簡体字で、中国大陸の普通話の語彙・言い回し（例: 地铁、出租车、软件、视频、信息）。句読点は全角（，。？！、“”）。
  zh_tw: 繁體字（台湾の標準字形）で、台湾の国語の語彙・言い回し（例: 捷運、計程車、軟體、影片、資訊）。句読点は全角（，。？！、「」）。
  直訳の書き換えではなく、それぞれの地域の人が自然に言う文にする。
- 本文にアラビア数字やローマ字を入れない。数は漢字で書き（例: 三十），外国の固有名詞や略語は中国語の言い方にするか避ける。
- 一文だけ。初級は HSK1〜2級程度の語で15字以内、中級は HSK3〜4級程度で30字以内、上級は HSK5〜6級程度で45字以内。
- 初級・中級・上級をそれぞれ1〜2件。1件ごとに、もとにした記事の id を source に入れる。
- pinyin_cn は zh_cn の、大陸の標準音（現代漢語詞典）の数字ピンイン。
  pinyin_tw は zh_tw の、台湾の標準音（教育部國語辭典。例: 星期 xing1 qi2、垃圾 le4 se4）の数字ピンイン。
  どちらも漢字1字に1音節（句読点には付けない）。軽声は5、ü は v。「一」は yi1、「不」は bu4 と変調前の本来の声調で書く。
- ja は自然な日本語訳。"""

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": ["初級", "中級", "上級"]},
                    "source": {"type": "integer"},
                    "zh_cn": {"type": "string"},
                    "pinyin_cn": {"type": "string"},
                    "zh_tw": {"type": "string"},
                    "pinyin_tw": {"type": "string"},
                    "ja": {"type": "string"},
                },
                "required": ["level", "source", "zh_cn", "pinyin_cn", "zh_tw", "pinyin_tw", "ja"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


# ---------- RSS ----------
def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": "chinese-typing-dojo/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    for it in root.iter("item"):
        yield {
            "title": strip_tags(it.findtext("title")),
            "summary": strip_tags(it.findtext("description"))[:300],
            "link": (it.findtext("link") or "").strip(),
        }


def used_links():
    return {link for path in NEWS.values() if path.exists()
            for link in re.findall(r"https?://\S+", path.read_text(encoding="utf-8"))}


def candidates():
    """各フィードから順番に1件ずつ取り、話題が偏らないようにする。"""
    used = used_links()
    per_feed = []
    for url, label in FEEDS:
        try:
            items = list(fetch_feed(url))
        except Exception as e:  # 1つのフィードが落ちていても続ける
            print(f"フィードを読めない: {label} {e}", file=sys.stderr)
            items = []
        ok = [dict(x, feed=label) for x in items
              if x["link"] and x["link"] not in used
              and not any(w in x["title"] + x["summary"] for w in BLOCK)]
        per_feed.append(ok)
    out = []
    while len(out) < MAX_CANDIDATES and any(per_feed):
        for lst in per_feed:
            if lst and len(out) < MAX_CANDIDATES:
                out.append(lst.pop(0))
    for i, c in enumerate(out, 1):
        c["id"] = i
    return out


# ---------- Claude ----------
def ask_claude(cands):
    import anthropic  # Actions でだけ入れる（ローカルの --sample では不要）

    client = anthropic.Anthropic()
    articles = "\n\n".join(f"[id {c['id']}] {c['title']}\n{c['summary']}" for c in cands)
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"今日のニュースの見出しと概要です。\n\n{articles}"}],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        # 安全上の理由で断られたときは、サーバー側で推奨モデルに切り替えて続ける
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        print("Claude が生成を断った", file=sys.stderr)
        return {"items": []}
    text = "".join(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


# ---------- 読みの照合 ----------
def loose_eq(a, b):
    return len(a) == len(b) and all(x == y or (x[:-1] == y[:-1] and "5" in (x[-1], y[-1])) for x, y in zip(a, b))


class Checker:
    """variant "cn" は簡体字・大陸の読み、"tw" は繁體字・台湾の読みで照合する。"""

    def __init__(self):
        self.words_t, _, _, self.readings = load_cedict()
        self.words_s = {}
        for trad, entries in self.words_t.items():
            for simp, syls, _, proper in entries:
                self.words_s.setdefault(simp, []).append((simp, syls, None, proper))
        self.chars = {"cn": {w for w in self.words_s if len(w) == 1}, "tw": {w for w in self.words_t if len(w) == 1}}
        # 台湾の読み: TOCFL 詞語表の注音（sources/ がなければ使わない）
        self.tbcl = {}
        try:
            rev = {}
            for syl in sorted({x for rs in self.readings.values() for x in rs}):
                try:
                    rev.setdefault(to_zhuyin(syl), syl)
                except ValueError:
                    pass
            tbcl, _ = load_tbcl(rev)
            for rows in tbcl.values():
                for trad, tw in rows:
                    self.tbcl.setdefault(trad, []).append(tw)
        except OSError:
            pass

    def word_readings(self, w, variant):
        """固有名詞でない見出しの読みの一覧（重複なし）。台湾は台湾の読みに置き換える。"""
        out = []
        if variant == "cn":
            for _, syls, _, proper in self.words_s.get(w, []):
                if not proper and syls not in out:
                    out.append(syls)
            return out
        for tw in self.tbcl.get(w, []):
            if tw not in out:
                out.append(tw)
        for _, syls, _, proper in self.words_t.get(w, []):
            tw = TW_PR.get((w, tuple(syls)), syls)
            if not proper and tw not in out:
                out.append(tw)
        return out

    def check(self, zh, pinyin, variant):
        """(直した読み, 要確認の一覧)。読めない・数が合わないときは読みを None で返す。"""
        notes = []
        han = HAN.findall(zh)
        if re.search(r"[A-Za-z0-9０-９Ａ-Ｚａ-ｚ]", zh):
            return None, ["本文にローマ字か数字がある"]
        try:
            syls = [norm_syl(x) for x in pinyin.split()]
        except ValueError as e:
            return None, [f"読みの書式: {e}"]
        if len(han) != len(syls):
            return None, [f"漢字 {len(han)} 字に対して読みが {len(syls)} 音節"]
        syls = citation(zh, syls)
        kind = "簡体字" if variant == "cn" else "繁體字"
        for ch in han:
            if ch not in self.chars[variant]:
                notes.append(f"「{ch}」は{kind}の見出しにない（字体が混ざっているかも）")
        # 最長一致で語に分け、語ごとに辞書の読みと照らす
        i = 0
        while i < len(han):
            for n in range(min(6, len(han) - i), 0, -1):
                w = "".join(han[i:i + n])
                cands = self.word_readings(w, variant)
                if cands or n == 1:
                    break
            got = syls[i:i + n]
            if cands:
                exact = [c for c in cands if c == got]
                near = [c for c in cands if loose_eq(c, got)]
                if exact:
                    pass
                elif len(near) == 1:
                    syls[i:i + n] = near[0]
                elif variant == "tw" and any([x[:-1] for x in c] == [x[:-1] for x in got] for c in cands):
                    # 声調だけ違う: 台湾の標準音は大陸の辞書と声調が違うことが多いので、直さずに確認を促す
                    notes.append(f"「{w}」を台湾音 {' '.join(got)} としている（辞書: {' / '.join(' '.join(c) for c in cands)}）")
                elif len(cands) == 1:
                    notes.append(f"「{w}」を {' '.join(got)} → 辞書の {' '.join(cands[0])} に直した")
                    syls[i:i + n] = cands[0]
                else:
                    notes.append(f"「{w}」を {' '.join(got)} と読んでいる（辞書: {' / '.join(' '.join(c) for c in cands)}）")
            elif n == 1 and w not in self.readings:
                notes.append(f"「{w}」は辞書にない")
            i += n
        return syls, notes


# ---------- 書き出し ----------
HEADER = {
    "cn": """# 時事の例文・簡体字（中国大陸の普通話。ニュースの話題をもとにしたオリジナル。scripts/generate_news.py が追記する）
# 書式は texts-cn.txt と同じで、4列目に話題の出典（元記事の URL）を書く:
#   簡体字 | 数字ピンイン（大陸の標準音） | 日本語訳 | 出典 URL
# 記事の文章は写さず、見出しと概要の事実だけを使っている。公開前に Pull Request で確認すること。
# 「# 要確認:」の行は読みの照合で気になった点。確認したら消してよい。
""",
    "tw": """# 時事の例文・繁體字（台湾の国語。ニュースの話題をもとにしたオリジナル。scripts/generate_news.py が追記する）
# 書式は texts-tw.txt と同じで、4列目に話題の出典（元記事の URL）を書く:
#   繁體字 | 数字ピンイン（台湾の標準音） | 日本語訳 | 出典 URL
# 記事の文章は写さず、見出しと概要の事実だけを使っている。公開前に Pull Request で確認すること。
# 「# 要確認:」の行は読みの照合で気になった点。確認したら消してよい。
""",
}


def write_news(entries, today, variant):
    blocks = [f"\n# ---- {today} 自動生成 ----"]
    for level in ("初級", "中級", "上級"):
        rows = [e for e in entries if e["level"] == level]
        if not rows:
            continue
        blocks.append(f"## {level} 一文")
        for e in rows:
            blocks += [f"# 要確認: {n}" for n in e["notes"]]
            blocks.append(f"{e['zh']} | {' '.join(e['syls'])} | {e['ja']} | {e['link']}")
    path = NEWS[variant]
    text = path.read_text(encoding="utf-8") if path.exists() else HEADER[variant]
    path.write_text(text.rstrip("\n") + "\n" + "\n".join(blocks) + "\n", encoding="utf-8")


def report(entries, dropped, today):
    lines = [f"{today} のニュースの話題から作った例文です（モデル: {MODEL}）。",
             "マージする前に、中国語の自然さ（簡体字は大陸の言い方、繁體字は台湾の言い方になっているか）・訳・読み・話題の適切さを確認してください。", ""]
    for e in entries:
        label = "簡体字" if e["variant"] == "cn" else "繁體字"
        lines.append(f"- **{e['level']}・{label}** {e['zh']}  \n  {' '.join(e['syls'])}  \n  {e['ja']}  \n  出典: [{e['title']}]({e['link']})")
        lines += [f"  - ⚠️ {n}" for n in e["notes"]]
    if dropped:
        lines += ["", "読みが合わず除いたもの:"]
        lines += [f"- {d['zh']}（{'; '.join(d['notes'])}）" for d in dropped]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", help="API を呼ばず、この JSON を Claude の応答として使う")
    ap.add_argument("--report", help="Pull Request の本文を書き出すファイル")
    args = ap.parse_args()

    cands = candidates()
    print(f"候補の記事 {len(cands)} 件")
    if not cands:
        return
    result = json.loads(Path(args.sample).read_text(encoding="utf-8")) if args.sample else ask_claude(cands)
    by_id = {c["id"]: c for c in cands}

    checker = Checker()
    entries, dropped = [], []
    for it in result.get("items", []):
        src = by_id.get(it["source"])
        if not src:
            continue
        for variant in ("cn", "tw"):
            zh = it[f"zh_{variant}"].strip().replace("|", "｜")
            if not zh:
                continue
            syls, notes = checker.check(zh, it[f"pinyin_{variant}"], variant)
            e = {"level": it["level"], "variant": variant, "zh": zh, "ja": it["ja"].strip().replace("|", "｜"),
                 "link": src["link"], "title": src["title"], "syls": syls, "notes": notes}
            (entries if syls else dropped).append(e)

    today = datetime.date.today().isoformat()
    for variant in ("cn", "tw"):
        rows = [e for e in entries if e["variant"] == variant]
        if rows:
            write_news(rows, today, variant)
    text = report(entries, dropped, today)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    print(f"追加 {len(entries)} 件、除外 {len(dropped)} 件")


if __name__ == "__main__":
    main()
