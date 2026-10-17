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
| `content/texts.txt` | 一文・長文の例文（繁体字で書く） |
| `scripts/` | 公開データの取得と `data/` の生成 |
| `data/` | サイトが読む単語・例文データ（生成物） |

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

例文を足すときは `content/texts.txt` に `繁体字 | 数字ピンイン | 日本語訳` の形で1行追加して、`build_data.py` を実行する。

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
