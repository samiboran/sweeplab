/* Piyasa Hava Durumu — wide-screen "Dünya" column on the home page (S10b).
   Loads dunya.json only on screens ≥ 1200 px; phones keep the question link.
   Fetched JSON is data: textContent / DOM APIs only. */
(function () {
  "use strict";
  if (!window.matchMedia || !window.matchMedia("(min-width:1200px)").matches) return;
  var box = document.getElementById("dunya-side");
  if (!box) return;
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    var a = Math.abs(v).toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (a === "0,0") return "%0,0";
    return (v > 0 ? "+" : "−") + "⁠%" + a;
  }
  fetch(DATA + "dunya.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      box.textContent = "";
      box.appendChild(el("p", "label", "Dünya · son gün"));
      var t = el("table");
      t.appendChild(el("caption", "sr", "Bölge endekslerinin son günlük değişimi"));
      (d.markets || []).forEach(function (m) {
        var ix = (m.endeksler || []).filter(function (r) { return r.tur === "endeks" && !r.eski; })[0];
        if (!ix) return;
        var tr = el("tr");
        tr.appendChild(el("td", null, m.baslik + " · " + ix.ad));
        tr.appendChild(el("td", "r" + (ix.chg_1g < 0 ? " neg" : ""), pct(ix.chg_1g)));
        t.appendChild(tr);
      });
      box.appendChild(t);
      var heads = [];
      ((d.basliklar || {}).konular || []).forEach(function (k) { heads = heads.concat(k.basliklar || []); });
      // Home sidebar: only headlines a Turkish/English reader can follow; dunya.html lists all languages.
      heads = heads.filter(function (h) { return !h.dil || h.dil === "en" || h.dil === "tr"; });
      heads.sort(function (a, b) { return String(b.zaman).localeCompare(String(a.zaman)); });
      if (heads.length) {
        box.appendChild(el("p", "label more", "Günün başlıkları"));
        var ul = el("ul");
        heads.slice(0, 5).forEach(function (h) {
          var li = el("li");
          if (/^https:\/\//.test(String(h.url || ""))) {
            var a = el("a", null, h.baslik);
            a.href = h.url;
            a.rel = "noopener noreferrer";
            li.appendChild(a);
          } else { li.appendChild(el("span", null, h.baslik)); }
          li.appendChild(el("span", "hs", h.kaynak));
          ul.appendChild(li);
        });
        box.appendChild(ul);
      }
      var p = el("p", "more");
      var a2 = el("a", null, "Dünyada durum ne?");
      a2.href = "dunya.html";
      p.appendChild(a2);
      box.appendChild(p);
      box.hidden = false;
    })
    .catch(function () { /* column simply stays hidden */ });
})();
