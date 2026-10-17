// 広告の設定。Google AdSense の審査に通ったら、ここに値を入れて公開し直す。
//   client: "ca-pub-1234567890123456" のような パブリッシャーID
//   slots:  広告ユニットのID（空なら、その枠には出さない。client だけ入れれば自動広告になる）
export const ADS = {
  client: "",
  slots: {
    belowPractice: "",
    footer: "",
  },
};

// 誤りの報告先。
//   googleForm.url を入れると Google フォームに、空なら GitHub の Issue 作成画面に送る。
//   Google フォームの「事前入力したURLを取得」で出てくる entry.数字 を fields に入れる。
export const REPORT = {
  googleForm: {
    url: "",            // 例: "https://docs.google.com/forms/d/e/XXXX/viewform"
    fields: {
      item: "",         // 例: "entry.123456789"（漢字）
      reading: "",      // 表示していた読み
      kind: "",         // 誤りの種類
      comment: "",      // 正しいと思う内容・コメント
      settings: "",     // 練習の設定
    },
  },
  githubRepo: "yamataku14/chinese-typing-dojo",
};
