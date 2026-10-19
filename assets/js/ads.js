// AdSense を config.js の設定どおりに読み込む。client が空なら何もしない。
import { ADS } from "./config.js?v=202610190854";

if (ADS.client) {
  const s = document.createElement("script");
  s.async = true;
  s.crossOrigin = "anonymous";
  s.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(ADS.client)}`;
  document.head.appendChild(s);

  const fill = () => {
    for (const slot of document.querySelectorAll(".ad-slot[data-slot]")) {
      const id = ADS.slots[slot.dataset.slot];
      if (!id) continue;
      const ins = document.createElement("ins");
      ins.className = "adsbygoogle";
      ins.style.display = "block";
      ins.dataset.adClient = ADS.client;
      ins.dataset.adSlot = id;
      ins.dataset.adFormat = "auto";
      ins.dataset.fullWidthResponsive = "true";
      slot.appendChild(ins);
      slot.hidden = false;
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    }
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fill);
  else fill();
}
