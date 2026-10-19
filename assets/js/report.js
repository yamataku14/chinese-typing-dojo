// 誤りの報告。静的サイトなので自前では受け取らず、
// Google フォーム（設定があれば）か GitHub の Issue 作成画面を、内容を入れた状態で開く。
import { REPORT } from "./config.js?v=202610190854";

const KINDS = ["読み・声調", "漢字・字体", "意味・訳", "その他"];

export function reportURL({ item, reading, kind, comment, settings }) {
  const gf = REPORT.googleForm;
  if (gf.url && gf.fields.item) {
    const q = new URLSearchParams({ usp: "pp_url" });
    const put = (field, v) => { if (field) q.set(field, v); };
    put(gf.fields.item, item);
    put(gf.fields.reading, reading);
    put(gf.fields.kind, kind);
    put(gf.fields.comment, comment);
    put(gf.fields.settings, settings);
    return `${gf.url}?${q}`;
  }
  const title = `【${kind}】${item.length > 20 ? item.slice(0, 20) + "…" : item}`;
  const body = [
    `**対象**: ${item}`,
    `**表示されていた読み**: ${reading}`,
    `**種類**: ${kind}`,
    `**設定**: ${settings}`,
    "",
    "**正しいと思う内容・コメント**",
    comment || "（なし）",
  ].join("\n");
  const q = new URLSearchParams({ title, body, labels: "読みの誤り報告" });
  return `https://github.com/${REPORT.githubRepo}/issues/new?${q}`;
}

export const usesGitHub = () => !(REPORT.googleForm.url && REPORT.googleForm.fields.item);

// 報告パネルを root の中に描く。entries: [{label, item, reading}], index: 最初に選んでおく番号
export function renderReport(root, { entries, index, settings, onClose }) {
  root.hidden = false;
  root.innerHTML = `
    <div class="report-head">
      <h3>誤りを報告</h3>
      <button type="button" class="pill-btn" data-close>閉じる</button>
    </div>
    <label class="field"><span class="label">対象</span>
      <select id="repItem">${entries.map((e, i) => `<option value="${i}">${escapeHTML(e.label)}</option>`).join("")}</select>
    </label>
    <p class="note" id="repReading"></p>
    <fieldset class="field"><legend class="label">種類</legend>
      <div class="toggles">${KINDS.map((k, i) => `<label class="toggle"><input type="radio" name="repKind" value="${k}" ${i === 0 ? "checked" : ""}> ${k}</label>`).join("")}</div>
    </fieldset>
    <label class="field"><span class="label">正しいと思う内容・コメント（任意）</span>
      <textarea id="repComment" rows="3" placeholder="例: 「星期」の繁體字の読みは xīngqí ではなく…"></textarea>
    </label>
    <div class="actions" style="justify-content:flex-start">
      <a class="primary" id="repSend" target="_blank" rel="noopener">報告ページを開く</a>
    </div>
    <p class="note">${usesGitHub()
      ? "GitHub の報告ページ（Issue）が新しいタブで開きます。内容は入力済みなので、GitHub にログインして「Create」を押すと送信されます。"
      : "報告フォームが新しいタブで開きます。内容は入力済みなので、確認して送信してください。"}
      個人情報は書かないでください。</p>`;

  const sel = root.querySelector("#repItem");
  sel.value = String(index);
  const send = root.querySelector("#repSend");
  const update = () => {
    const e = entries[+sel.value];
    root.querySelector("#repReading").textContent = `表示中の読み: ${e.reading}`;
    send.href = reportURL({
      item: e.item,
      reading: e.reading,
      kind: root.querySelector("input[name=repKind]:checked").value,
      comment: root.querySelector("#repComment").value.trim(),
      settings,
    });
  };
  root.addEventListener("input", update);
  root.addEventListener("change", update);
  root.querySelector("[data-close]").addEventListener("click", () => { root.hidden = true; onClose?.(); });
  send.addEventListener("click", () => setTimeout(() => { root.hidden = true; onClose?.(); }, 300));
  update();
  sel.focus();
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
