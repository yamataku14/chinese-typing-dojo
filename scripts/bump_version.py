"""公開する前に実行する: CSS・JS・データの URL に版番号（?v=日時）を付け直す。

GitHub Pages はファイルをブラウザに10分ほどキャッシュさせるので、更新直後は新しいページと
古いプログラムが混ざって読み込まれることがある。URL に版番号を付けておけば、新しいページは
必ず同じ版のプログラムとデータを読み込む。

使い方:  python3 scripts/bump_version.py   （そのあとコミットして push）
"""
import datetime
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VER = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")

ASSET = re.compile(r"(assets/(?:css|js)/[\w.-]+\.(?:css|js))(?:\?v=\w+)?")
IMPORT = re.compile(r'(from\s+"\./[\w.-]+\.js)(?:\?v=\w+)?"')

changed = []
for path in ROOT.glob("*.html"):
    s = path.read_text(encoding="utf-8")
    t = ASSET.sub(rf"\1?v={VER}", s)
    if t != s:
        path.write_text(t, encoding="utf-8")
        changed.append(path.name)
for path in (ROOT / "assets/js").glob("*.js"):
    s = path.read_text(encoding="utf-8")
    t = IMPORT.sub(rf'\1?v={VER}"', s)
    if t != s:
        path.write_text(t, encoding="utf-8")
        changed.append(path.name)
(ROOT / "assets/js/version.js").write_text(
    f'// scripts/bump_version.py が書き換える。データの URL に付ける版番号\nexport const VERSION = "{VER}";\n', encoding="utf-8")
print(VER, "更新:", ", ".join(changed))
