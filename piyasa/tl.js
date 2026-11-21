/* Piyasa Hava Durumu — "TL tarafı" (S4b). Reads data/site/tl.json; DOM APIs only. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var SVG = "http://www.w3.org/2000/svg";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function num(v, nd) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return v.toLocaleString("tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return (v > 0 ? "+" : v < 0 ? "−" : "") + "%" + num(Math.abs(v), 1);
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
  }

  function spark(series, label) {
    var all = (Array.isArray(series) ? series : []).filter(function (p) {
      return Array.isArray(p) && typeof p[1] === "number" && /^\d{4}-\d{2}-\d{2}$/.test(String(p[0]));
    });
    var cut = "";
    if (all.length) {
      var dl = new Date(all[all.length - 1][0] + "T00:00:00Z");
      dl.setUTCDate(dl.getUTCDate() - 366);
      cut = dl.toISOString().slice(0, 10);
    }
    var pts = all.filter(function (p) { return p[0] >= cut; });     // last 1 year
    if (pts.length < 2) return null;
    var W = 320, H = 64, vals = [];
    pts.forEach(function (p) { vals.push(p[1]); if (typeof p[2] === "number") vals.push(p[2]); });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), span = hi - lo || 1;
    function path(idx) {
      var d = "", started = false;
      pts.forEach(function (p, i) {
        if (typeof p[idx] !== "number") { started = false; return; }
        var x = (i / (pts.length - 1)) * W, y = H - 2 - ((p[idx] - lo) / span) * (H - 4);
        d += (started ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
        started = true;
      });
      return d;
    }
    var svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("class", "spark");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", label + ": son 1 yıl, siyah çizgi kapanış, kırmızı çizgi 200 günlük ortalama");
    [[2, "ma"], [1, "px"]].forEach(function (k) {
      var d = path(k[0]);
      if (!d) return;
      var p = document.createElementNS(SVG, "path");
      p.setAttribute("d", d);
      p.setAttribute("class", k[1]);
      p.setAttribute("vector-effect", "non-scaling-stroke");
      svg.appendChild(p);
    });
    return svg;
  }

  var TL_EXPLAIN = {
    gram_altin: ["1 gram altının TL karşılığı.", "Ons altın fiyatı (dolar) × dolar/TL ÷ 31,1035 (1 ons = 31,1035 gram). Kuyumcu satış fiyatı değildir; işçilik ve makas içermez.", "Yahoo Finance: COMEX altın vadeli (GC=F) ve USD/TRY"],
    gram_gumus: ["1 gram gümüşün TL karşılığı.", "Ons gümüş fiyatı (dolar) × dolar/TL ÷ 31,1035. Banka ve kuyumcu fiyatları makas nedeniyle farklı olabilir.", "Yahoo Finance: COMEX gümüş vadeli (SI=F) ve USD/TRY"],
    dolar: ["1 ABD dolarının TL karşılığı (piyasa kuru).", "Günlük kapanış kuru. Banka ve döviz bürosu kurları alış-satış makası nedeniyle farklıdır.", "Yahoo Finance: USD/TRY (TRY=X)"],
    btc: ["Bitcoin'in dolar fiyatı (günlük kapanış, UTC).", "Kripto piyasası 7/24 açıktır; günlük kapanış UTC gece yarısı alınır. Hesaplayıcı OKX kapanışını kullanır, küçük fark olabilir.", "Yahoo Finance: BTC-USD"],
    eth: ["Ether'in dolar fiyatı (günlük kapanış, UTC).", "Kripto piyasası 7/24 açıktır; günlük kapanış UTC gece yarısı alınır.", "Yahoo Finance: ETH-USD"],
    bist100_usd: ["BIST 100 endeksinin dolar cinsinden değeri.", "BIST 100 ÷ dolar/TL. Grafikte başlangıç günü 100 kabul edilir; böylece TL'deki değer kaybından arındırılmış performans görülür.", "Yahoo Finance: XU100.IS (gecikmeli olabilir) ve USD/TRY"]
  };
  var CHG_NOTE = "1 gün: bir önceki kapanışa göre. 7 ve 30 gün: o kadar takvim günü önceki son kapanışa göre. Yılbaşı: geçen yılın son kapanışına göre. 1 yıl: 365 gün önceki son kapanışa göre. 200g ort. farkı: son 200 işlem gününün ortalamasına göre uzaklık. Grafikte siyah çizgi kapanış, kırmızı çizgi 200 günlük ortalama.";

  function render(d) {
    var box = document.getElementById("tl");
    box.textContent = "";
    if (d.status !== "ok") box.appendChild(el("p", "notice", "TL verisi bugün güncellenmedi; son geçerli değerler gösteriliyor."));
    (d.assets || []).forEach(function (a) {
      var item = el("div", "tl-item");
      var head = el("div", "tl-head");
      var h3 = el("h3");
      var btn = el("button", "tl-q", a.label);
      btn.type = "button";
      btn.setAttribute("aria-expanded", "false");
      h3.appendChild(btn);
      head.appendChild(h3);
      var info = TL_EXPLAIN[a.id];
      var panel = el("div", "explain");
      panel.hidden = true;
      if (info) {
        [["Nedir? ", info[0]], ["Nasıl hesaplanıyor? ", info[1]], ["Kaynak: ", info[2]], ["Değişimler: ", CHG_NOTE]].forEach(function (x) {
          var p = el("p"); p.appendChild(el("strong", null, x[0])); p.appendChild(document.createTextNode(x[1])); panel.appendChild(p);
        });
      }
      btn.addEventListener("click", function () {
        var open = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", open ? "false" : "true");
        panel.hidden = open;
      });
      if (a.status && (a.id === "btc" || a.id === "eth")) return;   // optional rows: hide when missing
      if (a.status) { item.appendChild(head); item.appendChild(el("p", "mute small", "Veri yok.")); box.appendChild(item); return; }
      var nd = a.id === "btc" ? 0 : 2;
      var unitTxt = a.unit === "$" ? " $" : (a.unit === "TL/gram" || a.unit === "TL") ? " TL" : "";
      var v = a.last == null ? pct(a.chg_ytd) : num(a.last, nd) + unitTxt;
      head.appendChild(el("span", "tl-val", a.last == null ? pct(a.chg_ytd) + " yılbaşından" : v));
      item.appendChild(head);
      item.appendChild(panel);
      var dl = el("dl", "tl-chg");
      [["1 gün", a.chg_1g], ["7 gün", a.chg_7g], ["30 gün", a.chg_30g], ["Yılbaşı", a.chg_ytd], ["1 yıl", a.chg_1y], ["200g ort. farkı", a.vs_ma200]].forEach(function (c) {
        var w = el("div");
        w.appendChild(el("dt", null, c[0]));
        w.appendChild(el("dd", null, pct(c[1])));
        dl.appendChild(w);
      });
      item.appendChild(dl);
      var s = spark(a.series, a.label);
      if (s) item.appendChild(s);
      if (a.date_1y) {
        var ago = "1 yıl önce (" + trDate(a.date_1y) + "): " + (a.val_1y != null ? num(a.val_1y, nd) + unitTxt : "—") +
          " · bugün: " + (a.last != null ? num(a.last, nd) + unitTxt : "—") + " · değişim " + pct(a.chg_1y);
        if (a.val_1y == null) ago = "1 yıl önceye (" + trDate(a.date_1y) + ") göre değişim: " + pct(a.chg_1y);
        item.appendChild(el("p", "tl-ago", ago));
      }
      var note = "Veri: " + trDate(a.asof) + (a.note ? " · " + a.note : "");
      item.appendChild(el("p", "mute small", note));
      box.appendChild(item);
    });
    if (d.note) box.appendChild(el("p", "mute small", d.note));
  }

  fetch(DATA + "tl.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) { if (!d || typeof d !== "object") throw new Error("bad"); render(d); })
    .catch(function () {
      var box = document.getElementById("tl");
      box.textContent = "";
      box.appendChild(el("p", "mute small", "TL verisi henüz yayımlanmadı."));
    });
})();
