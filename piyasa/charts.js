/* Piyasa Hava Durumu — view-only charts inside answers (S5).
   Lazy: the chart library (self-hosted Lightweight Charts 4.1.3) and charts.json load only
   when an answer that needs a chart is opened. Fetched data -> DOM APIs only. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var LIB = "vendor/lightweight-charts-4.1.3.standalone.production.js";
  var INK = "#111111", RED = "#d7261e", GREY = "#9a9a9a", RULE = "#ececec", RETRO = "#cfcfcf";
  var libP = null, dataP = null;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
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
  function data() {
    if (!dataP) dataP = fetch(DATA + "charts.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    return dataP;
  }
  function fmt(v) {
    var a = Math.abs(v);
    return v.toLocaleString("tr-TR", { maximumFractionDigits: a >= 1000 ? 0 : a >= 10 ? 1 : 2 });
  }
  function isDate(s) { return typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s); }
  function num(v) { return typeof v === "number" && isFinite(v); }

  function base(LW, host, h, intOnly) {
    return LW.createChart(host, {
      width: host.clientWidth || 340, height: h,
      layout: { background: { type: "solid", color: "#ffffff" }, textColor: INK, fontFamily: "Inter, system-ui, sans-serif", fontSize: 11 },
      grid: { vertLines: { color: RULE }, horzLines: { color: RULE } },
      rightPriceScale: { borderColor: RULE }, timeScale: { borderColor: RULE },
      crosshair: { vertLine: { color: GREY, labelBackgroundColor: INK }, horzLine: { color: GREY, labelBackgroundColor: INK } },
      handleScroll: false, handleScale: false,
      localization: { locale: "tr-TR", priceFormatter: function (v) { return intOnly ? String(Math.round(v)) : fmt(v); } }
    });
  }
  function fit(chart, host) {
    chart.timeScale().applyOptions({ rightOffset: 2 });
    chart.timeScale().fitContent();
    if (window.ResizeObserver) new ResizeObserver(function () { chart.applyOptions({ width: host.clientWidth }); }).observe(host);
  }
  function figure(box, title, alt) {
    var f = el("figure", "chart");
    f.appendChild(el("figcaption", "label", title));
    var host = el("div", "chart-host");
    host.setAttribute("role", "img");
    host.setAttribute("aria-label", alt);
    f.appendChild(host);
    box.appendChild(f);
    return { fig: f, host: host };
  }
  function legend(fig, items) {
    var p = el("p", "chart-legend");
    items.forEach(function (it) {
      var item = el("span", "item");
      var k = el("span", "key " + it[0]);
      k.setAttribute("aria-hidden", "true");
      item.appendChild(k);
      item.appendChild(document.createTextNode(it[1]));
      p.appendChild(item);
    });
    fig.appendChild(p);
  }
  function credit(box) {
    var p = el("p", "mute small chart-credit");
    p.appendChild(document.createTextNode("Grafik kütüphanesi: "));
    var a = el("a", null, "TradingView Lightweight Charts");
    a.href = "https://www.tradingview.com/"; a.rel = "noopener noreferrer"; a.target = "_blank";
    p.appendChild(a);
    box.appendChild(p);
  }

  function crypto(LW, d, box) {
    [["btc", "BTC"], ["eth", "ETH"]].forEach(function (c) {
      var s = d.crypto && d.crypto[c[0]];
      if (!s || !Array.isArray(s.series)) return;
      var rows = s.series.filter(function (r) { return Array.isArray(r) && isDate(r[0]) && num(r[1]); });
      if (rows.length < 2) return;
      var f = figure(box, c[1] + " günlük kapanış (USDT)", c[1] + " son " + rows.length + " günlük kapanış, 50 ve 200 günlük ortalama");
      var ch = base(LW, f.host, 220);
      ch.addLineSeries({ color: GREY, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
        .setData(rows.filter(function (r) { return num(r[2]); }).map(function (r) { return { time: r[0], value: r[2] }; }));
      ch.addLineSeries({ color: RED, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
        .setData(rows.filter(function (r) { return num(r[3]); }).map(function (r) { return { time: r[0], value: r[3] }; }));
      ch.addLineSeries({ color: INK, lineWidth: 2, priceLineVisible: false })
        .setData(rows.map(function (r) { return { time: r[0], value: r[1] }; }));
      fit(ch, f.host);
      legend(f.fig, [["k-ink", "Kapanış"], ["k-grey", "50 gün ort."], ["k-red", "200 gün ort."]]);
    });
  }

  function macro(LW, d, box) {
    var rows = (d.macro || []).filter(function (r) { return Array.isArray(r) && isDate(r[0]) && num(r[1]); });
    if (!rows.length) return;
    var f = figure(box, "Makro hava geçmişi (ham skor, 0–9)", "Günlük ham skor; gri geriye dönük, siyah canlı, kırmızı canlı KIRMIZI gün");
    var ch = base(LW, f.host, 180, true);
    var hs = ch.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false, priceFormat: { type: "price", precision: 0, minMove: 1 },
      autoscaleInfoProvider: function () { return { priceRange: { minValue: 0, maxValue: 9 } }; } });
    hs.setData(rows.map(function (r) {
      var live = r[3] === "live";
      return { time: r[0], value: r[1], color: !live ? RETRO : (r[2] === "KIRMIZI" ? RED : INK) };
    }));
    var marks = [];
    (d.version_boundaries || []).forEach(function (b) {
      if (b && isDate(b.date)) marks.push({ time: b.date, position: "aboveBar", color: INK, shape: "arrowDown", text: String(b.rules_version || "") });
    });
    for (var i = 0; i < rows.length; i++) {
      if (rows[i][3] === "live") { marks.push({ time: rows[i][0], position: "aboveBar", color: RED, shape: "arrowDown", text: "canlı" }); break; }
    }
    marks.sort(function (a, b) { return a.time < b.time ? -1 : a.time > b.time ? 1 : 0; });
    hs.setMarkers(marks);
    ch.priceScale("right").applyOptions({ scaleMargins: { top: 0.2, bottom: 0 } });
    fit(ch, f.host);
    legend(f.fig, [["k-retro", "Geriye dönük"], ["k-ink", "Canlı"], ["k-red", "Canlı, KIRMIZI"]]);
  }

  var WHICH = { kripto: crypto, hava: macro };
  window.PHDCharts = {
    attach: function (id, box) {
      var fn = WHICH[id];
      if (!fn) return;
      var wrap = el("div", "charts");
      box.appendChild(wrap);
      Promise.all([lib(), data()]).then(function (x) {
        if (!wrap.isConnected) return;
        fn(x[0], x[1], wrap);
        if (wrap.childNodes.length) credit(wrap);
      }).catch(function () { wrap.appendChild(el("p", "mute small", "Grafik şu an yüklenemedi.")); });
    }
  };
})();
