/* Piyasa Hava Durumu — "Destek ve direnç" page (B6). Reads data/site/seviyeler.json.
   One asset at a time: chart (self-hosted Lightweight Charts 4.1.3, loaded lazily) with the zones as
   price lines, a ladder (direnç above, last close, destek below) and the last 10 sessions' events.
   Fund/index assets carry only % distances and a series rebased to 100. DOM APIs only. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var LIB = "vendor/lightweight-charts-4.1.3.standalone.production.js";
  var INK = "#111111", RED = "#d7261e", GREY = "#9a9a9a", RULE = "#ececec";
  var EN = !!(window.PHD_I18N && window.PHD_I18N.en);
  var MON = EN ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
               : ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
  var Z = window.PHD_ZINCIR;
  function L(tr, en) { return EN ? en : tr; }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    if (EN) e.setAttribute("data-noi18n", "");
    return e;
  }
  function num(v, nd) {
    return v.toLocaleString(EN ? "en-US" : "tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function price(a, v) {
    if (a.unit === "%") return EN ? num(v, a.nd) + "%" : "%" + num(v, a.nd);
    return num(v, a.nd) + (a.unit === "$" ? " $" : a.unit === "TL" ? " TL" : "");
  }
  function day(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MON[+m[2] - 1] + " " + m[1].slice(2) : "";
  }
  function name(a) { return EN ? a.label_en : a.label; }

  var libP = null;
  function lib() {
    if (window.LightweightCharts) return Promise.resolve(window.LightweightCharts);
    if (!libP) libP = new Promise(function (ok, no) {
      var s = document.createElement("script");
      s.src = LIB; s.async = true;
      s.onload = function () { window.LightweightCharts ? ok(window.LightweightCharts) : no(new Error("lib")); };
      s.onerror = no;
      document.head.appendChild(s);
    });
    return libP;
  }

  var chart = null;
  function drawChart(host, a) {
    lib().then(function (LW) {
      if (chart) { chart.remove(); chart = null; }
      host.textContent = "";
      var last = a.series.length ? a.series[a.series.length - 1][1] : null;
      chart = LW.createChart(host, {
        width: host.clientWidth || 340, height: 260,
        layout: { background: { type: "solid", color: "#ffffff" }, textColor: INK, fontFamily: "Inter, system-ui, sans-serif", fontSize: 11 },
        grid: { vertLines: { color: RULE }, horzLines: { color: RULE } },
        rightPriceScale: { borderColor: RULE }, timeScale: { borderColor: RULE },
        crosshair: { vertLine: { color: GREY, labelBackgroundColor: INK }, horzLine: { color: GREY, labelBackgroundColor: INK } },
        handleScroll: false, handleScale: false,
        localization: { locale: EN ? "en-US" : "tr-TR" }
      });
      var s = chart.addLineSeries({ color: INK, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: true });
      s.setData(a.series.map(function (p) { return { time: p[0], value: p[1] }; }));
      function lvl(z, col, title) {
        // fund/index assets: zone position on the rebased series = last × (1 + dist)
        var v = a.abs ? z.p : last * (1 + z.dist_pct / 100);
        s.createPriceLine({ price: v, color: col, lineWidth: 1, lineStyle: 2, axisLabelVisible: !!a.abs, title: title });
      }
      a.direnc.forEach(function (z) { lvl(z, RED, L("direnç", "resistance")); });
      a.destek.forEach(function (z) { lvl(z, INK, L("destek", "support")); });
      chart.timeScale().fitContent();
      if (window.ResizeObserver) new ResizeObserver(function () { if (chart) chart.applyOptions({ width: host.clientWidth }); }).observe(host);
    }).catch(function () { host.textContent = L("Grafik yüklenemedi.", "Chart could not load."); });
  }

  function zoneRow(a, z, kind) {
    var li = el("li", "sv-z " + kind);
    li.appendChild(el("span", "sv-k", kind === "direnc" ? L("Direnç", "Resistance") : L("Destek", "Support")));
    li.appendChild(el("span", "sv-p", a.abs ? price(a, z.p) : (EN ? z.text_en : z.text)));
    var meta = (a.abs ? Z.pct(z.dist_pct) + " · " : "") +
      L(z.touches + " kez döndü · son " + day(z.last), "turned " + z.touches + " times · last " + day(z.last));
    li.appendChild(el("span", "sv-m mute small", meta));
    return li;
  }

  function detail(a) {
    var box = $("sv-detay");
    box.textContent = "";
    var h = el("h2", "sv-h", name(a));
    box.appendChild(h);
    var line = (a.abs ? L("Son kapanış ", "Last close ") + price(a, a.close) + " · " : "") +
      L("1 gün ", "1 day ") + Z.pct(a.chg1d_pct) + " · " + L("20 gün ", "20 days ") + Z.pct(a.chg20d_pct) +
      " · " + day(a.asof) + (a.eski ? L(" (eski veri)", " (stale data)") : "");
    box.appendChild(el("p", "meta", line));
    if (!a.abs) box.appendChild(el("p", "mute small", L("Bu bir fon/endeks: bölgeler fiyat olarak değil, son kapanışa uzaklık olarak gösterilir; grafik ilk gün = 100.",
      "A fund/index: zones are shown as distance from the last close, not as prices; chart first day = 100.")));
    var host = el("div", "chart-host sv-chart");
    host.setAttribute("role", "img");
    host.setAttribute("aria-label", L(name(a) + ": son bir yıl ve destek/direnç bölgeleri", name(a) + ": last year with support/resistance zones"));
    box.appendChild(host);
    drawChart(host, a);

    var ol = el("ol", "sv-ladder");
    a.direnc.slice().reverse().forEach(function (z) { ol.appendChild(zoneRow(a, z, "direnc")); });
    var now = el("li", "sv-z now");
    now.appendChild(el("span", "sv-k", L("Son kapanış", "Last close")));
    now.appendChild(el("span", "sv-p", a.abs ? price(a, a.close) : L("1 gün ", "1 day ") + Z.pct(a.chg1d_pct)));
    if (a.bolgede) now.appendChild(el("span", "sv-m mute small", L("fiyat şu an " + a.bolgede.text + " bölgesinin içinde · " + a.bolgede.touches + " kez döndü",
      "price is inside the " + a.bolgede.text_en + " zone now · turned " + a.bolgede.touches + " times")));
    ol.appendChild(now);
    a.destek.forEach(function (z) { ol.appendChild(zoneRow(a, z, "destek")); });
    box.appendChild(ol);
    if (!a.direnc.length) box.appendChild(el("p", "mute small", L("Üstte iki yıl içinde iki kez dönülen bölge yok; 52 haftanın zirvesine uzaklık " + Z.pct(a.hi52_dist_pct) + ".",
      "No zone above where price turned twice in two years; distance to the 52-week high " + Z.pct(a.hi52_dist_pct) + ".")));
    if (!a.destek.length) box.appendChild(el("p", "mute small", L("Altta iki yıl içinde iki kez dönülen bölge yok; 52 haftanın dibine uzaklık " + Z.pct(a.lo52_dist_pct) + ".",
      "No zone below where price turned twice in two years; distance to the 52-week low " + Z.pct(a.lo52_dist_pct) + ".")));

    box.appendChild(el("p", "label sv-evl", L("Son 10 işlem günü", "Last 10 sessions")));
    if (a.events.length) {
      var ul = el("ul", "sv-ev");
      a.events.forEach(function (e) { ul.appendChild(el("li", null, EN ? e.text_en : e.text)); });
      box.appendChild(ul);
    } else box.appendChild(el("p", "mute small", L("Bölgelerde dikkate değer bir dönüş ya da geçiş olmadı.", "No notable turn or cross at the zones.")));
  }

  function table(d) {
    var t = $("sv-tbl");
    t.textContent = "";
    var hd = el("thead"), tr = el("tr");
    [L("Varlık", "Asset"), L("En yakın direnç", "Nearest resistance"), L("En yakın destek", "Nearest support"), L("Son olay", "Last event")].forEach(function (x) { tr.appendChild(el("th", null, x)); });
    hd.appendChild(tr); t.appendChild(hd);
    var tb = el("tbody");
    d.assets.forEach(function (a) {
      var r = el("tr");
      var c0 = el("td"); var b = el("button", "sv-link", name(a)); b.type = "button";
      b.addEventListener("click", function () { pick(a.id, true); });
      c0.appendChild(b); r.appendChild(c0);
      var up = a.direnc[0], dn = a.destek[0];
      r.appendChild(el("td", null, up ? Z.pct(up.dist_pct) : "—"));
      r.appendChild(el("td", null, dn ? Z.pct(dn.dist_pct) : "—"));
      var ev = a.events[0];
      r.appendChild(el("td", "mute small", ev ? (EN ? ev.text_en : ev.text) : ""));
      tb.appendChild(r);
    });
    t.appendChild(tb);
  }

  var DATA_ = null;
  function pick(id, scroll) {
    var a = DATA_.assets.filter(function (x) { return x.id === id; })[0] || DATA_.assets[0];
    Array.prototype.forEach.call($("sv-chips").children, function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-id") === a.id ? "true" : "false"); });
    detail(a);
    try { history.replaceState(null, "", location.pathname + location.search + "#" + a.id); } catch (e) { /* ignore */ }
    if (scroll) $("l-varlik").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  fetch(DATA + "seviyeler.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      if (!d || !Array.isArray(d.assets) || !d.assets.length) throw new Error("empty");
      DATA_ = d;
      $("sv-meta").textContent = L("Veri: ", "Data: ") + day(d.data_date) + L(" kapanışı · her sabah güncellenir", " close · updated every morning");
      Z.render($("zincir"), d);
      var chips = $("sv-chips");
      d.assets.forEach(function (a) {
        var b = el("button", "q sv-chip", name(a));
        b.type = "button";
        b.setAttribute("data-id", a.id);
        b.addEventListener("click", function () { pick(a.id, false); });
        chips.appendChild(b);
      });
      table(d);
      var want = (location.hash || "").slice(1);
      pick(/^[a-z0-9_]+$/.test(want) ? want : "gram_altin", false);
    })
    .catch(function () { $("sv-meta").textContent = L("Veri şu an yüklenemedi.", "Data could not be loaded right now."); });
})();
