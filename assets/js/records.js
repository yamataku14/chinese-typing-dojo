// 練習記録の保存。今はブラウザの localStorage だけに保存する。
// 将来アカウントを作るときは、この Records の中身をサーバー同期に差し替えればよい
// （画面側は Records の関数だけを使っている）。

const KEY = "ctd:records:v1";
const MAX_SESSIONS = 1000;

function empty() {
  return { version: 1, sessions: [], weak: {} };
}

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return empty();
    const d = JSON.parse(raw);
    return d && Array.isArray(d.sessions) ? { ...empty(), ...d } : empty();
  } catch {
    return empty();
  }
}

function save(d) {
  try {
    localStorage.setItem(KEY, JSON.stringify(d));
    return true;
  } catch {
    return false;
  }
}

let data = load();

// 設定の組み合わせを表すキー（自己ベストの比較単位）
export function settingKey(s) {
  return [s.script, s.input, s.length, s.length === "word" ? `${s.source}${s.level}` : s.difficulty].join("|");
}

export const Records = {
  available() {
    try {
      localStorage.setItem("ctd:probe", "1");
      localStorage.removeItem("ctd:probe");
      return true;
    } catch {
      return false;
    }
  },

  // session: {settings, chars, keys, misses, secs, weak: {音節: ミス回数}}
  add(session) {
    const { weak, ...rest } = session;
    const entry = { ...rest, key: settingKey(session.settings), at: Date.now() };
    data.sessions.push(entry);
    if (data.sessions.length > MAX_SESSIONS) data.sessions.splice(0, data.sessions.length - MAX_SESSIONS);
    for (const [k, n] of Object.entries(weak || {})) data.weak[k] = (data.weak[k] || 0) + n;
    save(data);
    return entry;
  },

  sessions() {
    return data.sessions.slice();
  },

  best(key, exceptAt) {
    let best = null;
    for (const s of data.sessions) {
      if (s.key !== key || s.at === exceptAt || s.acc < 80) continue;
      if (!best || s.cpm > best.cpm) best = s;
    }
    return best;
  },

  weakTop(n = 12) {
    return Object.entries(data.weak).sort((a, b) => b[1] - a[1]).slice(0, n);
  },

  exportJSON() {
    return JSON.stringify(data, null, 1);
  },

  importJSON(text) {
    const d = JSON.parse(text);
    if (!d || !Array.isArray(d.sessions)) throw new Error("記録ファイルの形式が違います");
    const seen = new Set(data.sessions.map(s => s.at));
    for (const s of d.sessions) if (!seen.has(s.at)) data.sessions.push(s);
    data.sessions.sort((a, b) => a.at - b.at);
    for (const [k, n] of Object.entries(d.weak || {})) data.weak[k] = (data.weak[k] || 0) + n;
    save(data);
  },

  clear() {
    data = empty();
    save(data);
  },
};
