import { Records } from "./records.js?v=202610190848";
import { describe, fmtTime } from "./labels.js?v=202610190848";

const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function fmtDate(t) {
  const d = new Date(t);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// 直近の速度（字/分）の折れ線
function chart(sessions) {
  const pts = sessions.slice(-40);
  if (pts.length < 2) return '<p class="empty">2回以上練習すると、速度の推移がここに表示されます。</p>';
  const W = 640, H = 200, L = 40, R = 12, T = 12, B = 26;
  const max = Math.max(10, ...pts.map(p => p.cpm));
  const top = Math.ceil(max / 10) * 10;
  const x = i => L + (i / (pts.length - 1)) * (W - L - R);
  const y = v => T + (1 - v / top) * (H - T - B);
  const ticks = [0, top / 2, top];
  const line = pts.map((p, i) => `${x(i).toFixed(1)},${y(p.cpm).toFixed(1)}`).join(" ");
  const area = `${x(0)},${y(0)} ${line} ${x(pts.length - 1)},${y(0)}`;
  const last = pts[pts.length - 1];
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="直近${pts.length}回の速度の推移">
    ${ticks.map(t => `<line x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}" stroke="var(--line)" stroke-width="1"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end">${t}</text>`).join("")}
    <polygon points="${area}" fill="var(--jade-soft)"/>
    <polyline points="${line}" fill="none" stroke="var(--jade)" stroke-width="2" stroke-linejoin="round"/>
    <circle cx="${x(pts.length - 1)}" cy="${y(last.cpm)}" r="4" fill="var(--seal)"/>
    <text x="${L}" y="${H - 6}">${pts.length}回前</text>
    <text x="${W - R}" y="${H - 6}" text-anchor="end">最新 ${last.cpm} 字/分</text>
  </svg>`;
}

export function renderRecords(root) {
  const sessions = Records.sessions();
  const n = sessions.length;
  const totalChars = sessions.reduce((a, s) => a + (s.chars || 0), 0);
  const totalSecs = sessions.reduce((a, s) => a + (s.secs || 0), 0);
  const recent = sessions.slice(-10);
  const avg = recent.length ? Math.round(recent.reduce((a, s) => a + s.cpm, 0) / recent.length) : 0;
  const bestByKey = new Map();
  for (const s of sessions) if (s.acc >= 80 && (!bestByKey.has(s.key) || s.cpm > bestByKey.get(s.key).cpm)) bestByKey.set(s.key, s);
  const weak = Records.weakTop(16);

  root.innerHTML = `
  <div class="wrap">
    <div class="stats">
      <div class="stat"><span class="label">練習回数</span><span class="v">${n}<small>回</small></span></div>
      <div class="stat"><span class="label">入力した字数</span><span class="v">${totalChars.toLocaleString()}<small>字</small></span></div>
      <div class="stat"><span class="label">練習時間</span><span class="v">${fmtTime(totalSecs)}</span></div>
      <div class="stat"><span class="label">直近10回の平均</span><span class="v">${avg}<small>字/分</small></span></div>
    </div>

    <section class="panel chart"><h2>速度の推移</h2>${chart(sessions)}</section>

    <section class="panel">
      <h2>設定ごとの自己ベスト</h2>
      ${bestByKey.size ? `<div class="table-wrap"><table>
        <thead><tr><th>設定</th><th class="num">字/分</th><th class="num">正確率</th><th>日時</th></tr></thead>
        <tbody>${[...bestByKey.values()].sort((a, b) => b.cpm - a.cpm).map(s => `<tr><td>${esc(describe(s.settings))}</td><td class="num">${s.cpm}</td><td class="num">${s.acc}%</td><td>${fmtDate(s.at)}</td></tr>`).join("")}</tbody>
      </table></div>` : '<p class="empty">正確率80%以上で練習を終えると、ここに自己ベストが並びます。</p>'}
    </section>

    <section class="panel">
      <h2>苦手な音節</h2>
      ${weak.length ? `<div class="chips" style="justify-content:flex-start">${weak.map(([k, c]) => `<span>${esc(k)}<em>×${c}</em></span>`).join("")}</div>` : '<p class="empty">まだミスの記録はありません。</p>'}
    </section>

    <section class="panel">
      <h2>最近の練習</h2>
      ${n ? `<div class="table-wrap"><table>
        <thead><tr><th>日時</th><th>設定</th><th class="num">字/分</th><th class="num">キー/分</th><th class="num">正確率</th><th class="num">時間</th></tr></thead>
        <tbody>${sessions.slice(-30).reverse().map(s => `<tr><td>${fmtDate(s.at)}</td><td>${esc(describe(s.settings))}</td><td class="num">${s.cpm}</td><td class="num">${s.kpm}</td><td class="num">${s.acc}%</td><td class="num">${fmtTime(s.secs)}</td></tr>`).join("")}</tbody>
      </table></div>` : '<p class="empty">まだ記録がありません。「練習」タブで1回練習すると、ここに表示されます。</p>'}
    </section>

    <section class="panel">
      <h2>記録の保存先</h2>
      <p class="note">記録はこのブラウザの中だけに保存されています。ブラウザのデータを消したり、別の端末で開いたりすると見られません。端末を移るときは書き出したファイルを読み込んでください。</p>
      <div class="actions" style="justify-content:flex-start">
        <button type="button" class="secondary" id="exportBtn">記録を書き出す</button>
        <label class="secondary" style="cursor:pointer">記録を読み込む<input type="file" id="importFile" accept="application/json,.json" hidden></label>
        <button type="button" class="secondary danger" id="clearBtn">記録をすべて消す</button>
      </div>
      <div class="confirm" id="clearConfirm" hidden>
        <span>すべての記録を消します。元に戻せません。</span>
        <button type="button" class="primary" id="clearYes">消す</button>
        <button type="button" class="secondary" id="clearNo">やめる</button>
      </div>
      <p class="note" id="ioMsg" role="status"></p>
    </section>
  </div>`;

  const msg = t => { root.querySelector("#ioMsg").textContent = t; };
  root.querySelector("#exportBtn").addEventListener("click", () => {
    const blob = new Blob([Records.exportJSON()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `chinese-typing-records-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    msg("記録を書き出しました。");
  });
  root.querySelector("#importFile").addEventListener("change", async e => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      Records.importJSON(await f.text());
      renderRecords(root);
      root.querySelector("#ioMsg").textContent = "記録を読み込みました。";
    } catch (err) {
      msg(`読み込めませんでした: ${err.message}`);
    }
  });
  root.querySelector("#clearBtn").addEventListener("click", () => { root.querySelector("#clearConfirm").hidden = false; });
  root.querySelector("#clearNo").addEventListener("click", () => { root.querySelector("#clearConfirm").hidden = true; });
  root.querySelector("#clearYes").addEventListener("click", () => { Records.clear(); renderRecords(root); });
}
