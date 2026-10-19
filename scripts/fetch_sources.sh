#!/bin/sh
# 公開データを sources/ にダウンロードする（リポジトリには含めない）。
set -eu
cd "$(dirname "$0")/.."
mkdir -p sources/hsk sources/tocfl sources/cedict

# 旧HSK 1〜6級 — drkameleon/complete-hsk-vocabulary（MIT）
for i in 1 2 3 4 5 6; do
  curl -sfL -o "sources/hsk/old-$i.json" \
    "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/main/wordlists/exclusive/old/$i.json"
done

# TOCFL 詞語表（2022年版） — pseitz/tocfl が公式 xlsx から変換したもの（MIT）
curl -sfL -o sources/tocfl/tocfl_words.json \
  "https://raw.githubusercontent.com/pseitz/tocfl/HEAD/tocfl_words.json"

# CC-CEDICT（CC BY-SA 4.0）
curl -sfL -o sources/cedict/cedict.txt.gz \
  "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
gunzip -f sources/cedict/cedict.txt.gz

# Tatoeba の例文（CC BY 2.0 FR）— 中国語の文・日本語の文・その対応・利用者の母語
mkdir -p sources/tatoeba
T=https://downloads.tatoeba.org/exports
curl -sfL -o sources/tatoeba/cmn_sentences_detailed.tsv.bz2 "$T/per_language/cmn/cmn_sentences_detailed.tsv.bz2"
curl -sfL -o sources/tatoeba/jpn_sentences.tsv.bz2 "$T/per_language/jpn/jpn_sentences.tsv.bz2"
curl -sfL -o sources/tatoeba/cmn-jpn_links.tsv.bz2 "$T/per_language/cmn/cmn-jpn_links.tsv.bz2"
curl -sfL -o sources/tatoeba/user_languages.tar.bz2 "$T/user_languages.tar.bz2"
(cd sources/tatoeba && bunzip2 -f ./*.tsv.bz2 && tar -xjf user_languages.tar.bz2 && rm user_languages.tar.bz2)

echo "done"
