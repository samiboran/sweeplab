/* Piyasa Hava Durumu — "Günün özeti" (daily news digest, prepared each morning; no live AI).
   Reads data/site/ozet.json (schema: docs/OZET_SCHEMA.md). Data -> textContent / DOM APIs only;
   links only https:// with rel="noopener noreferrer". Hidden when missing or older than 2 days. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var EN = !!(window.PHD_I18N && window.PHD_I18N.en);
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
  }
  function safeUrl(u) { return /^https:\/\/[^\s"'<>]+$/.test(String(u || "")) ? String(u) : null; }
  function fresh(iso) {
    var t = Date.parse(String(iso || "") + "T00:00:00Z");
    return isFinite(t) && (Date.now() - t) / 864e5 <= 2.5;
  }
  var sec = document.getElementById("s-ozet");
  if (!sec) return;
  fetch(DATA + "ozet.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      if (!d || !Array.isArray(d.items) || !d.items.length || !fresh(d.date)) return;
      var box = document.getElementById("ozet");
      box.textContent = "";
      d.items.slice(0, 8).forEach(function (it) {
        var art = el("article", "oz");
        art.appendChild(el("p", "oz-k", it.konu));
        var h = el("h3", null, EN && it.baslik_en ? it.baslik_en : it.baslik);
        var p = el("p", "oz-t", EN && it.ozet_en ? it.ozet_en : it.ozet);
        if (EN && it.baslik_en) { h.setAttribute("data-noi18n", ""); p.setAttribute("data-noi18n", ""); }
        art.appendChild(h);
        art.appendChild(p);
        var src = el("p", "oz-s");
        (Array.isArray(it.kaynaklar) ? it.kaynaklar : []).slice(0, 3).forEach(function (s, i) {
          var u = safeUrl(s && s.url);
          if (!u) return;
          if (src.childNodes.length) src.appendChild(document.createTextNode(" · "));
          var a = el("a", null, String(s.ad || "Kaynak"));
          a.href = u; a.rel = "noopener noreferrer"; a.target = "_blank";
          src.appendChild(a);
        });
        if (src.childNodes.length) art.appendChild(src);
        box.appendChild(art);
      });
      document.getElementById("ozet-meta").textContent = trDate(d.date) +
        " sabahı hazırlandı · Olgusal özet, kendi cümlelerimizle; haberlerin hakları kaynaklarına aittir.";
      sec.hidden = false;
    })
    .catch(function () { /* digest is optional */ });
})();
