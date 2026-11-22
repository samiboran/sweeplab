/* Piyasa Hava Durumu — "Grafikte karşılaştır". Pick 2–3 assets and see them together
   (each rebased to 100 at the start of the range) or the ratio of the first to the second.
   Data: compare.json (daily closes, ~2 years; BIST 100 and funds rebased only). Chart: the
   self-hosted Lightweight Charts 4.1.3 with drag / wheel / pinch enabled. DOM APIs only. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var LIB = "vendor/lightweight-charts-4.1.3.standalone.production.js";
  var INK = "#111111", RED = "#d7261e", GREY = "#8a8a8a", RULE = "#ececec";
  var COLORS = [[INK, 0], [RED, 0], [GREY, 2]];          // [color, lineStyle] — third series dashed grey
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var RANGES = [["1a", "1 ay", 31], ["3a", "3 ay", 92], ["6a", "6 ay", 183], ["yb", "Yılbaşı", 0], ["1y", "1 yıl", 366], ["2y", "2 yıl", 740]];
  var PRESETS = [["Altın / gümüş oranı", "ons_altin", "ons_gumus", "", "oran"],
                 ["Gram altın ve dolar/TL", "gram_altin", "dolar", "", "birlikte"],
                 ["BIST 100: TL ve dolar", "bist100_tl", "bist100_usd", "", "birlikte"],
                 ["Altın, Bitcoin, S&P 500", "ons_altin", "btc", "spy", "birlikte"],
                 ["Brent / altın oranı", "brent", "ons_altin", "", "oran"]];
  var I = window.PHD_I18N || { en: false };

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
  // DOM text is always written in Turkish format (i18n.js converts it in English mode);
  // the chart axis is drawn on canvas, so it gets the page locale directly.
  function num(v, nd, loc) { return Math.abs(v).toLocaleString(loc || "tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd }); }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return (v > 0 ? "+" : v < 0 ? "−" : "") + "%" + num(v, 1);
  }
  function lvl(v, loc) { var a = Math.abs(v); return (v < 0 ? "−" : "") + num(v, a >= 1000 ? 0 : a >= 10 ? 1 : a >= 1 ? 2 : 4, loc); }

  var D = null, A = {}, chart = null, series = [], LWref = null;

  function lib() {
    if (window.LightweightCharts) return Promise.resolve(window.LightweightCharts);
    return new Promise(function (ok, no) {
      var s = document.createElement("script");
      s.src = LIB; s.async = true;
      s.onload = function () { window.LightweightCharts ? ok(window.LightweightCharts) : no(new Error("lib")); };
      s.onerror = no;
      document.head.appendChild(s);
    });
  }

  // ---- state <-> URL (shareable; keeps ?lang=en)
  var ID = /^[a-z0-9_]{1,24}$/;
  function readUrl() {
    var p = new URLSearchParams(location.search);
    var g = function (k, d) { var v = p.get(k); return v && ID.test(v) ? v : d; };
    return { a: g("a", "ons_altin"), b: g("b", "ons_gumus"), c: g("c", ""), mod: p.get("mod") === "oran" ? "oran" : (p.get("mod") === "birlikte" ? "birlikte" : null), ara: g("ara", "1y") };
  }
  function writeUrl(s) {
    var p = new URLSearchParams(location.search);
    ["a", "b", "c", "mod", "ara"].forEach(function (k) { if (s[k]) p.set(k, s[k]); else p.delete(k); });
    try { history.replaceState(null, "", location.pathname + "?" + p.toString()); } catch (e) { /* ignore */ }
  }

  function state() {
    var mod = document.querySelector("input[name=mod]:checked");
    var on = document.querySelector("#ranges button[aria-pressed=true]");
    return { a: $("a1").value, b: $("a2").value, c: $("a3").value, mod: mod ? mod.value : "birlikte", ara: on ? on.getAttribute("data-r") : "1y" };
  }

  function startIndex(ara) {
    var dates = D.dates, last = dates[dates.length - 1];
    if (ara === "yb") {
      var y = last.slice(0, 4) + "-01-01";
      for (var i = 0; i < dates.length; i++) if (dates[i] >= y) return Math.max(0, i - 1);
      return 0;
    }
    var r = RANGES.filter(function (x) { return x[0] === ara; })[0] || RANGES[4];
    var cut = new Date(Date.parse(last + "T00:00:00Z") - r[2] * 864e5).toISOString().slice(0, 10);
    for (var j = 0; j < dates.length; j++) if (dates[j] >= cut) return j;
    return 0;
  }

  // points [time, value] for one asset from index i0; nulls skipped
  function pts(a, i0) {
    var out = [];
    for (var i = i0; i < D.dates.length; i++) { var v = a.v[i]; if (typeof v === "number" && isFinite(v)) out.push([D.dates[i], v]); }
    return out;
  }

  function draw() {
    var s = state();
    var oran = s.mod === "oran";
    var ids = [s.a, s.b, s.c].filter(function (x, k, arr) { return x && A[x] && arr.indexOf(x) === k; });
    // ratio needs exactly two different assets
    $("a3").disabled = oran;
    if (oran) ids = ids.slice(0, 2);
    writeUrl(s);
    series.forEach(function (x) { chart.removeSeries(x); });
    series = [];
    var leg = $("c-legend"); leg.textContent = "";
    var sum = $("c-sum"); sum.textContent = "";
    if (ids.length < (oran ? 2 : 1)) { sum.textContent = oran ? "Oran için iki farklı varlık seç." : "En az bir varlık seç."; return; }
    var i0 = startIndex(s.ara);
    var lines = [];
    if (!oran) {
      ids.forEach(function (id, k) {
        var p = pts(A[id], i0);
        if (p.length < 2) return;
        var b = p[0][1];
        var data = p.map(function (x) { return { time: x[0], value: x[1] / b * 100 }; });
        var ser = chart.addLineSeries({ color: COLORS[k][0], lineStyle: COLORS[k][1], lineWidth: 2, priceLineVisible: false, lastValueVisible: true, title: "" });
        ser.setData(data);
        series.push(ser);
        var chg = data[data.length - 1].value - 100;
        lines.push([k, A[id].label, chg, p[0][0], p[p.length - 1][0]]);
      });
      lines.forEach(function (l) {
        var it = el("span", "item");
        var key = el("span", "key " + ["k-ink", "k-red", "k-grey k-dash"][l[0]]); key.setAttribute("aria-hidden", "true");
        it.appendChild(key);
        it.appendChild(document.createTextNode(l[1] + " " + pct(l[2])));
        leg.appendChild(it);
      });
      if (lines.length) {
        sum.textContent = trDate(lines[0][3]) + " – " + trDate(lines[0][4]) + ": " +
          lines.map(function (l) { return l[1] + " " + pct(l[2]); }).join(" · ") + ".";
      }
    } else {
      var a = A[ids[0]], b = A[ids[1]];
      var data = [];
      for (var i = i0; i < D.dates.length; i++) {
        var x = a.v[i], y = b.v[i];
        if (typeof x === "number" && typeof y === "number" && y !== 0) data.push({ time: D.dates[i], value: x / y });
      }
      if (data.length < 2) { sum.textContent = "Bu iki varlığın ortak günü yok."; return; }
      var real = a.kind === "fiyat" && b.kind === "fiyat";
      if (!real) { var f0 = data[0].value; data = data.map(function (d) { return { time: d.time, value: d.value / f0 * 100 }; }); }
      var ser = chart.addLineSeries({ color: INK, lineWidth: 2, priceLineVisible: false, lastValueVisible: true });
      ser.setData(data);
      series.push(ser);
      var first = data[0].value, last = data[data.length - 1].value;
      var it = el("span", "item");
      var key = el("span", "key k-ink"); key.setAttribute("aria-hidden", "true");
      it.appendChild(key);
      it.appendChild(document.createTextNode(a.label + " ÷ " + b.label));
      leg.appendChild(it);
      sum.textContent = a.label + " ÷ " + b.label + (real ? " oranı" : " (başlangıç = 100)") + ": " +
        trDate(data[0].time) + " " + lvl(first) + " → " + trDate(data[data.length - 1].time) + " " + lvl(last) +
        " (" + pct((last / first - 1) * 100) + ")." +
        (real ? "" : " Endekslenmiş seri olduğu için oranın seviyesi değil, yönü anlamlıdır.");
    }
    chart.applyOptions({ rightPriceScale: { mode: 0 } });
    chart.timeScale().fitContent();
    $("c-host").setAttribute("aria-label", sum.textContent || "Karşılaştırma grafiği");
  }

  function options(sel, val, allowEmpty) {
    sel.textContent = "";
    if (allowEmpty) { var o0 = el("option", null, "—"); o0.value = ""; sel.appendChild(o0); }
    D.assets.forEach(function (a) {
      var o = el("option", null, a.label + (a.kind === "endeks" ? " (endeks)" : " (" + a.unit + ")"));
      o.value = a.id;
      sel.appendChild(o);
    });
    sel.value = A[val] ? val : (allowEmpty ? "" : D.assets[0].id);
  }

  function setup(LW) {
    LWref = LW;
    var st = readUrl();
    D.assets.forEach(function (a) { A[a.id] = a; });
    options($("a1"), st.a, false);
    options($("a2"), st.b, true);
    options($("a3"), st.c, true);
    var mod = st.mod || (st.c ? "birlikte" : "oran");
    if (st.mod === null && !(A[st.a] && A[st.b] && A[st.a].kind === "fiyat" && A[st.b].kind === "fiyat")) mod = "birlikte";
    Array.prototype.forEach.call(document.querySelectorAll("input[name=mod]"), function (r) { r.checked = r.value === mod; });
    var rg = $("ranges");
    RANGES.forEach(function (r) {
      var b = el("button", "rbtn", r[1]);
      b.type = "button";
      b.setAttribute("data-r", r[0]);
      b.setAttribute("aria-pressed", r[0] === st.ara ? "true" : "false");
      b.addEventListener("click", function () {
        Array.prototype.forEach.call(rg.querySelectorAll("button"), function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
        draw();
      });
      rg.appendChild(b);
    });
    if (!rg.querySelector("[aria-pressed=true]")) rg.querySelector("[data-r='1y']").setAttribute("aria-pressed", "true");
    var pr = $("presets");
    pr.appendChild(el("span", "label", "Hazır: "));
    PRESETS.forEach(function (p, k) {
      if (!A[p[1]] || !A[p[2]] || (p[3] && !A[p[3]])) return;
      var b = el("button", "preset", p[0]);
      b.type = "button";
      b.addEventListener("click", function () {
        $("a1").value = p[1]; $("a2").value = p[2]; $("a3").value = p[3];
        Array.prototype.forEach.call(document.querySelectorAll("input[name=mod]"), function (r) { r.checked = r.value === p[4]; });
        draw();
      });
      if (pr.childNodes.length > 1) pr.appendChild(document.createTextNode(" · "));
      pr.appendChild(b);
    });
    $("cmp").addEventListener("change", draw);
    $("cmp").addEventListener("submit", function (e) { e.preventDefault(); });

    var host = $("c-host");
    chart = LW.createChart(host, {
      width: host.clientWidth || 340, height: Math.max(260, Math.min(420, Math.round(window.innerHeight * 0.45))),
      layout: { background: { type: "solid", color: "#ffffff" }, textColor: INK, fontFamily: "Inter, system-ui, sans-serif", fontSize: 11 },
      grid: { vertLines: { color: RULE }, horzLines: { color: RULE } },
      rightPriceScale: { borderColor: RULE }, timeScale: { borderColor: RULE, rightOffset: 2 },
      crosshair: { vertLine: { color: GREY, labelBackgroundColor: INK }, horzLine: { color: GREY, labelBackgroundColor: INK } },
      handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: { time: true, price: true }, axisDoubleClickReset: true },
      kineticScroll: { touch: true, mouse: false },
      localization: { locale: I.en ? "en-US" : "tr-TR", priceFormatter: function (v) { return lvl(v, I.en ? "en-US" : "tr-TR"); } }
    });
    host.addEventListener("dblclick", function () { chart.timeScale().fitContent(); });
    if (window.ResizeObserver) new ResizeObserver(function () { chart.applyOptions({ width: host.clientWidth }); }).observe(host);
    var asof = D.assets.reduce(function (m, a) { return a.asof > m ? a.asof : m; }, "");
    $("c-meta").textContent = "Günlük kapanışlar · son veri " + trDate(asof);
    $("c-note").textContent = D.note || "";
    $("foot-meta").textContent = "Üretildi " + String(D.generated_at || "—").replace("T", " ").replace("Z", " UTC");
    draw();
  }

  Promise.all([
    fetch(DATA + "compare.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }),
    lib()
  ]).then(function (x) {
    D = x[0];
    if (!D || !Array.isArray(D.dates) || !Array.isArray(D.assets) || !D.assets.length) throw new Error("bad");
    setup(x[1]);
  }).catch(function () { $("c-meta").textContent = "Karşılaştırma verisi henüz yayımlanmadı ya da yüklenemedi."; });
})();
