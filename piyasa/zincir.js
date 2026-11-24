/* Piyasa Hava Durumu — "Zincir" (B6): petrol → dolar → ABD faizi → altın → borsa → bitcoin, one line per link.
   Home page: reads the small data/site/zincir.json. seviyeler.html reuses PHD_ZINCIR.render with seviyeler.json.
   Data -> textContent / DOM APIs only. Hidden when the file is missing or older than 4 days. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var EN = !!(window.PHD_I18N && window.PHD_I18N.en);
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    if (EN) e.setAttribute("data-noi18n", "");
    return e;
  }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    var a = Math.abs(v).toLocaleString(EN ? "en-US" : "tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    var sg = v > 0 ? "+" : v < 0 ? "−" : "";
    return EN ? sg + a + "%" : sg + "%" + a;
  }
  function render(box, d) {
    box.textContent = "";
    var ol = el("ol", "zincir");
    (d.chain || []).forEach(function (c) {
      var li = el("li", "z-link " + (c.chg20d_pct > 0.2 ? "up" : c.chg20d_pct < -0.2 ? "down" : "flat"));
      var head = el("p", "z-head");
      head.appendChild(el("span", "z-ad", EN ? c.ad_en : c.ad));
      head.appendChild(el("span", "z-chg", pct(c.chg20d_pct)));
      li.appendChild(head);
      var t = EN ? c.yakin_en : c.yakin;
      if (t) li.appendChild(el("p", "z-t", t.charAt(0).toUpperCase() + t.slice(1) + "."));
      var ev = EN ? c.son_olay_en : c.son_olay;
      if (ev) li.appendChild(el("p", "z-ev mute small", ev));
      ol.appendChild(li);
    });
    box.appendChild(ol);
    var note = el("p", "mute small z-note", EN ? d.chain_note_en : d.chain_note);
    box.appendChild(note);
  }
  window.PHD_ZINCIR = { render: render, pct: pct };

  var sec = document.getElementById("s-zincir");
  if (!sec) return;
  fetch(DATA + "zincir.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      if (!d || !Array.isArray(d.chain) || !d.chain.length) return;
      var t = Date.parse(String(d.data_date || "") + "T00:00:00Z");
      if (!isFinite(t) || (Date.now() - t) / 864e5 > 4.5) return;
      render(document.getElementById("zincir"), d);
      sec.hidden = false;
    })
    .catch(function () { /* optional */ });
})();
