# 中文打字道場

中国語タイピング練習サイト。簡体字／繁体字、ピンイン／注音（大千式）入力に対応。
ビルド不要の静的サイトで、GitHub Pages でそのまま公開できる。

## ファイル構成

| パス | 内容 |
| --- | --- |
| `index.html` | 練習画面と記録画面 |
| `about.html`, `privacy.html` | 運営者・出典、プライバシーポリシー（AdSense 審査に必要） |
| `assets/js/app.js` | 練習画面の本体 |
| `assets/js/phonetics.js` | ピンイン → 声調記号・注音・キー列の変換 |
| `assets/js/records.js` | 練習記録（今は localStorage。アカウント対応時はここを差し替える） |
| `assets/js/config.js` | AdSense の設定 |
| `content/texts-cn.txt` | 簡体字の例文（中国大陸の普通話・大陸の発音） |
| `content/texts-tw.txt` | 繁體字の例文（台湾の国語・台湾の発音） |
| `content/news-cn.txt`, `content/news-tw.txt` | 時事の例文（ニュースの話題から自動生成し、PR で確認して入れる） |
| `scripts/` | 公開データの取得と `data/` の生成 |
| `data/` | サイトが読む単語・例文データ（生成物） |
| `.github/workflows/news-texts.yml` | 時事の例文を毎日作って PR を出す |

## ローカルで確認

```sh
python3 -m http.server 8000
```

http://localhost:8000 を開く（`file://` では JSON を読めないので必ずサーバー経由で）。

## データを作り直す

```sh
sh scripts/fetch_sources.sh   # HSK・TOCFL・CC-CEDICT を sources/ にダウンロード
python3 scripts/build_data.py # data/ を生成。例文の読みの数が合わないとエラーで止まる
```

例文を足すときは、簡体字なら `content/texts-cn.txt`（大陸の言い方・大陸の発音）、繁體字なら `content/texts-tw.txt`（台湾の言い方・台湾の発音）に
`本文 | 数字ピンイン | 日本語訳` の形で1行追加して、`build_data.py` を実行する。2つのファイルは別々の文章で、互いに変換はしない。

## 読みの誤りを直す

利用者は練習画面の「誤りを報告」から報告できる。報告先は `assets/js/config.js` の `REPORT` で決まり、
Google フォームの設定が空なら GitHub の Issue 作成画面が開く。

報告を受けて単語の読みを直すときは、`content/corrections.tsv` に `繁体語<TAB>大陸の読み<TAB>台湾の読み` を1行足して
`python3 scripts/build_data.py` を実行する。例文の読みは `content/texts-cn.txt`・`content/texts-tw.txt` を直接直す。

読みの方針: 簡体字は大陸の標準音、繁體字は台湾の標準音。「一」「不」は変調前の本来の声調。

## 例文の級

`build_data.py` が例文を語に分け、語の9割がその級までの語彙表（旧HSK・TBCL）に入る最小の級を「〜級相当」として付ける。

## 時事の例文（ニュースの話題から自動で作る）

`.github/workflows/news-texts.yml` が毎日 6:00（日本時間）に `scripts/generate_news.py` を動かし、
確認用の Pull Request を作る。main には直接 push しないので、**マージするまでサイトには出ない**。

1. `generate_news.py` の `FEEDS` にある RSS から、見出しと概要だけを取る（本文は取らない）。
2. 政治・両岸関係・事件・事故・災害・病気などの語（`BLOCK`）を含む記事と、使用済みの記事を除く。
3. Claude（`claude-sonnet-5-5`）が、記事の文を写さずに事実だけを使ったオリジナルの一文（繁体字）と日本語訳を、
   初級・中級・上級で1〜2件ずつ書く。安全上の理由で断られたときはサーバー側の推奨モデルに切り替える（`fallbacks: "default"`）。
4. 読みは CC-CEDICT と語の単位で照合する。辞書で読みが1つに決まる語は辞書の読みにそろえ、決まらないのに食い違うものは
   `content/news-cn.txt`・`content/news-tw.txt` に `# 要確認:` の行を残す。漢字と音節の数が合わないもの・数字やローマ字を含むものは捨てる。
5. `content/news-cn.txt`・`content/news-tw.txt` に `繁体字 | 数字ピンイン | 日本語訳 | 出典URL` の形で追記し、`build_data.py` で `data/` を作り直す。
   出典は練習画面に「話題の出典」として表示される。

### 最初の設定（1回だけ）

1. [Anthropic Console](https://console.anthropic.com/) で API キーを作る。
2. GitHub のリポジトリで Settings → Secrets and variables → Actions → New repository secret を開き、
   Name に `ANTHROPIC_API_KEY`、Secret にキーを入れて保存する。
3. Settings → Actions → General → Workflow permissions で
   「Allow GitHub Actions to create and approve pull requests」にチェックを入れて保存する（PR を作るのに必要）。
4. Actions タブ →「時事の例文」→ Run workflow で手動実行して、PR ができるか確かめる。

### PR の確認

- PR の本文に、例文・読み・訳・出典の記事と「⚠️」の付いた要確認点が並ぶ。中国語の自然さ、話題が適切か、元記事の文章に似すぎていないかを見る。
- 直すときは PR のブランチで `content/news-cn.txt`・`content/news-tw.txt` を編集し、`python3 scripts/build_data.py` を実行して `data/` もコミットする。
  `# 要確認:` の行は確認したら消してよい。使わない例文は行ごと消す。
- 確認待ちの PR があるあいだは新しい PR を作らない（`data/` が衝突するため）。マージするか閉じると次の回から再開する。
- PR の `data/` には、その日に取り直した HSK・TBCL・CC-CEDICT の更新が混ざることがある。

### ローカルで試す

Anthropic の SDK（1.x）は Python 3.10 以上が必要。

```sh
pip3 install anthropic
ANTHROPIC_API_KEY=... python3 scripts/generate_news.py   # content/news-cn.txt・news-tw.txt に追記される
python3 scripts/build_data.py
```

API を呼ばずに流れだけ試すときは、Claude の応答の形の JSON を用意して `--sample 応答.json` を付ける。
フィードを足すときは `FEEDS` に追加する。各社の RSS の利用規約を確認すること。

## 公開（GitHub Pages）

1. GitHub でリポジトリを作り、このフォルダを push する。
2. リポジトリの Settings → Pages → Source を「Deploy from a branch」、Branch を `main` / `(root)` にする。
3. 数分で `https://<ユーザー名>.github.io/<リポジトリ名>/` に公開される。

## 広告（Google AdSense）

1. 独自ドメインを取得し、GitHub Pages の Custom domain に設定する（AdSense は `github.io` のサブドメインでは審査に通らないことが多い）。
2. `about.html` の運営者・連絡先と、`privacy.html` の制定日を記入する（`data-todo` の箇所）。
3. AdSense に申し込み、審査用コードの代わりに `assets/js/config.js` の `client` にパブリッシャーID を入れて公開する。
4. 承認後、AdSense が示す内容でルートに `ads.txt` を置く。広告ユニットを作ったら `slots` にIDを入れる。

## ライセンス

コードは MIT（予定）。データの出典とライセンスは `data/LICENSE.md` と `about.html` を参照。
