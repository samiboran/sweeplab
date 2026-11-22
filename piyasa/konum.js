/* Piyasa Hava Durumu — "Ortalamalara göre konum" (S9). Fetched JSON is data:
   textContent / DOM APIs only, never innerHTML. Rows keep the order the file gives
   (asset class, then alphabetical); the page never re-sorts by distance. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];

  function $(id) { return document.getElementById(id); }
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
  function short(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1].slice(0, 3) : "—";
  }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    var a = Math.abs(v).toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (a === "0,0") return "%0,0";
    return (v > 0 ? "+" : "−") + "⁠%" + a;
  }
  function mark(v, w) {
    var td = el("td", "pm");
    if (v === 1 || v === 0) {
      td.appendChild(el("span", v === 1 ? "fm up" : "fm", null));
      td.appendChild(el("span", "sr", w + " günlük ortalamanın " + (v === 1 ? "üstünde" : "altında")));
    } else {
      td.appendChild(el("span", "mute", "—"));
      td.appendChild(el("span", "sr", "yeterli geçmiş yok"));
    }
    return td;
  }

  function table(g) {
    var wrap = el("div", "tablewrap");
    var t = el("table", "konum");
    var cap = el("caption", "sr", g.baslik + ": ortalamalara göre konum");
    t.appendChild(cap);
    var th = el("thead"), hr = el("tr");
    [["Varlık", "l"], ["20g", "c"], ["50g", "c"], ["200g", "c"], ["Fark", "r"], ["Veri", "r"]].forEach(function (h) {
      var c = el("th", h[1], h[0]);
      c.scope = "col";
      hr.appendChild(c);
    });
    th.appendChild(hr);
    t.appendChild(th);
    var tb = el("tbody");
    (g.satirlar || []).forEach(function (r) {
      var tr = el("tr", r.eski ? "stale" : null);
      var name = el("th", "l", r.ad);
      name.scope = "row";
      tr.appendChild(name);
      tr.appendChild(mark(r.ust20, 20));
      tr.appendChild(mark(r.ust50, 50));
      tr.appendChild(mark(r.ust200, 200));
      var v = typeof r.fark200 === "number" ? r.fark200 : null;
      tr.appendChild(el("td", "r v" + (v !== null && v < 0 ? " neg" : ""), pct(v)));
      tr.appendChild(el("td", "r d", r.asof ? short(r.asof) + (r.eski ? " · eski" : "") : "veri yok"));
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    wrap.appendChild(t);
    return wrap;
  }

  function render(d) {
    $("k-meta").textContent = "Son kapanış: " + trDate(d.data_date) + " · Evren " + trDate(d.universe_set_date) + " tarihinde belirlendi";
    var box = $("k-groups");
    box.textContent = "";
    (d.groups || []).forEach(function (g) {
      var s = el("section", "kg");
      var id = "kg-" + String(g.id || "").replace(/[^a-z0-9_-]/gi, "");
      var h = el("h2", "sh", g.baslik);
      h.id = id;
      s.setAttribute("aria-labelledby", id);
      s.appendChild(h);
      if (g.ozet) {
        var oz = String(g.ozet), pre = String(g.baslik) + ": ";
        s.appendChild(el("p", "k-ozet", oz.indexOf(pre) === 0 ? oz.charAt(pre.length).toLocaleUpperCase("tr-TR") + oz.slice(pre.length + 1) : oz));
      }
      s.appendChild(table(g));
      box.appendChild(s);
    });
    $("k-note").textContent = d.note || "";
    $("foot-meta").textContent = "Veri tarihi " + trDate(d.data_date) + " · Üretildi " +
      String(d.generated_at || "—").replace("T", " ").replace("Z", " UTC");
  }

  fetch(DATA + "konum.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(function () { $("k-meta").textContent = "Konum tablosu henüz yayımlanmadı ya da yüklenemedi."; });
})();
