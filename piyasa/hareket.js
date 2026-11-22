/* Piyasa Hava Durumu — "Günün hareketlileri ve anomaliler" (S10c). Fetched JSON is data:
   textContent / DOM APIs only. "Neden?" shows only sourced headlines from movers_news.json
   (optional file); causes are never written by this page. */
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
  function num(v, nd) { return Math.abs(v).toLocaleString("tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd }); }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return (v > 0 ? "+" : v < 0 ? "−" : "") + "⁠%" + num(v, 1);
  }
  function times(v) { return typeof v === "number" && isFinite(v) ? num(v, 1) + "×" : "—"; }
  function safeUrl(u) { return /^https:\/\/[^\s"'<>]+$/.test(String(u || "")) ? String(u) : null; }

  var news = {};
  function newsFor(m, asof, sym) {
    var e = news[m + "|" + asof + "|" + sym];
    if (!e) return null;
    var box = el("div", "mv-news");
    if (Array.isArray(e.items) && e.items.length) {
      e.items.slice().sort(function (a, b) { return String(b.published_at).localeCompare(String(a.published_at)); })
        .slice(0, 3).forEach(function (it) {
          var u = safeUrl(it.url);
          var p = el("p");
          if (u) {
            var a = el("a", null, it.headline);
            a.href = u; a.rel = "noopener noreferrer"; a.target = "_blank";
            p.appendChild(a);
          } else {
            p.appendChild(document.createTextNode(String(it.headline || "")));
          }
          p.appendChild(el("span", "mute", " — " + String(it.source || "") + (it.published_at ? ", " + trDate(it.published_at) : "")));
          box.appendChild(p);
        });
    } else if (e.status) {
      box.appendChild(el("p", "mute", String(e.status)));
    } else {
      return null;
    }
    return box;
  }

  function moverTable(title, rows, mk) {
    var wrap = el("div", "mv-col");
    wrap.appendChild(el("h3", "mv-h", title));
    if (!rows.length) { wrap.appendChild(el("p", "mute small", "Bugün bu yönde isim yok.")); return wrap; }
    var t = el("table", "mv");
    var th = el("thead"), hr = el("tr");
    [["Sembol", "l"], ["Değişim", "r"], ["Göreli hacim", "r"]].forEach(function (h) {
      var c = el("th", h[1], h[0]); c.scope = "col"; hr.appendChild(c);
    });
    th.appendChild(hr); t.appendChild(th);
    var tb = el("tbody");
    rows.forEach(function (r) {
      var tr = el("tr");
      var s = el("th", "l", r.sembol); s.scope = "row"; tr.appendChild(s);
      tr.appendChild(el("td", "r v" + (r.chg_1g < 0 ? " neg" : ""), pct(r.chg_1g)));
      tr.appendChild(el("td", "r", times(r.rel_hacim)));
      tb.appendChild(tr);
      var n = newsFor(mk.id, mk.asof, r.sembol);
      if (n) {
        var nr = el("tr", "mv-nr"), td = el("td");
        td.colSpan = 3;
        td.appendChild(el("span", "label", "Neden? "));
        td.appendChild(n);
        nr.appendChild(td);
        tb.appendChild(nr);
      }
    });
    t.appendChild(tb);
    wrap.appendChild(t);
    return wrap;
  }

  function render(d) {
    var box = $("m-markets");
    box.textContent = "";
    var dates = [];
    (d.markets || []).forEach(function (m) {
      var s = el("section", "mv-m");
      var hid = "mv-" + String(m.id || "").replace(/[^a-z0-9_-]/gi, "");
      var h = el("h2", "sh", m.baslik); h.id = hid;
      s.setAttribute("aria-labelledby", hid);
      s.appendChild(h);
      var e = m.endeks || {};
      s.appendChild(el("p", "meta", trDate(m.asof) + " kapanışı · " + (e.ad || "Endeks") + " " + pct(e.chg_1g) +
        (m.evren ? " · " + m.evren + " likit isim" : "")));
      if (m.asof) dates.push(m.asof);
      if (m.eski || !m.evren) {
        s.appendChild(el("p", "notice", m.evren ? "Bu pazarın verisi güncel değil; liste gösterilmiyor." : "Bu pazar için henüz veri yok."));
        box.appendChild(s);
        return;
      }
      var grid = el("div", "mv-grid");
      grid.appendChild(moverTable("En çok yükselenler", m.yukselenler || [], m));
      grid.appendChild(moverTable("En çok düşenler", m.dusenler || [], m));
      s.appendChild(grid);
      var an = m.anomaliler || [];
      var det = el("details", "mv-an");
      det.appendChild(el("summary", null, "Olağandışı hareketler (" + an.length + ")"));
      if (!an.length) det.appendChild(el("p", "mute small", "Bugün kurallara takılan hareket yok."));
      var ul = el("ul", "plain mv-list");
      an.forEach(function (r) {
        var li = el("li");
        var top = el("p", "mv-a");
        top.appendChild(el("strong", null, r.sembol));
        top.appendChild(el("span", "v" + (r.chg_1g < 0 ? " neg" : ""), " " + pct(r.chg_1g)));
        li.appendChild(top);
        (r.gerekce || []).forEach(function (g) { li.appendChild(el("p", "mv-g", g)); });
        var n = newsFor(m.id, m.asof, r.sembol);
        if (n) li.appendChild(n);
        ul.appendChild(li);
      });
      det.appendChild(ul);
      s.appendChild(det);
      if (m.not) s.appendChild(el("p", "mute small", m.not));
      box.appendChild(s);
    });
    var hasNews = Object.keys(news).length > 0;
    box.appendChild(el("p", "mute small", hasNews
      ? "Neden? satırları yalnız kaynaklı haber başlıklarıdır; hareketin nedeni hakkında yorum değildir."
      : "Neden? Haber eşleştirmesi bekleniyor. Hareketlerin nedeni tahmin edilmez; kaynaklı başlık eşleşince burada gösterilecek."));
    dates.sort();
    $("m-meta").textContent = dates.length ? "Son kapanış: " + trDate(dates[dates.length - 1]) : "Veri yok";
    $("foot-meta").textContent = "Üretildi " + String(d.generated_at || "—").replace("T", " ").replace("Z", " UTC") +
      " · Evren " + trDate(d.universe_set_date) + " tarihinde belirlendi";
  }

  function getJson(name) {
    return fetch(DATA + name, { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  var newsP = getJson("movers_news.json").then(function (n) {
    (n && Array.isArray(n.entries) ? n.entries : []).forEach(function (e) {
      if (e && e.market && e.date && e.symbol) news[e.market + "|" + e.date + "|" + e.symbol] = e;
    });
  }).catch(function () { /* optional file */ });
  Promise.all([getJson("movers.json"), newsP])
    .then(function (x) { render(x[0]); })
    .catch(function () { $("m-meta").textContent = "Günün hareketlileri henüz yayımlanmadı ya da yüklenemedi."; });
})();
