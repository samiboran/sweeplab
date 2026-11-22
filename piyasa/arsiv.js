/* Piyasa Hava Durumu — archive + track record. Fetched data is treated as data:
   textContent / DOM APIs only, never innerHTML. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var SHOW_FROM = "2026-10-01";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var WORD = { YESIL: "YEŞİL", SARI: "SARI", KIRMIZI: "KIRMIZI" };
  var CODES = ["L1", "L2", "L3", "D1", "K1", "K2", "K3", "N1", "P1"];
  var TITLES = { L1: "Stablecoin arzı", L2: "Fed net likiditesi", L3: "Reel faiz", D1: "Dolar endeksi",
    K1: "Kredi risk primi", K2: "Oynaklık (VIX)", K3: "Nasdaq Bileşik", N1: "Altın ve dolar", P1: "Petrol" };
  var ISO = /^\d{4}-\d{2}-\d{2}$/;
  var I = window.PHD_I18N, EN = !!(I && I.en);
  function L(tr, en) { return EN ? en : tr; }
  var MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  if (EN) {
    WORD = { YESIL: "GREEN", SARI: "YELLOW", KIRMIZI: "RED" };
    TITLES = { L1: "Stablecoin supply", L2: "Fed net liquidity", L3: "Real yield", D1: "Dollar index",
      K1: "Credit risk premium", K2: "Volatility (VIX)", K3: "Nasdaq Composite", N1: "Gold and the dollar", P1: "Oil" };
  }
  // Display words (Boran, 22 Kasım: neutral wording). sicil.json keeps its stored codes; only the label changes.
  var RESULT_TR = { "teyit edildi": "düşüş geldi", "yanlış alarm": "düşüş gelmedi", "bekliyor": "bekliyor", "kaçırılan": "KIRMIZI'sız düşüş", "kaçırılan düşüş": "KIRMIZI'sız düşüş" };
  var RESULT_EN = { "teyit edildi": "fall followed", "yanlış alarm": "no fall followed", "bekliyor": "pending", "kaçırılan": "fall without RED", "kaçırılan düşüş": "fall without RED" };

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + (EN ? MONTHS_EN : MONTHS)[+m[2] - 1] + " " + m[1] : "—";
  }
  if (EN) ["days-body", "days-note", "sicil-sum", "sicil-live", "sicil-retro", "sicil-meta"].forEach(function (id) { var e = $(id); if (e) e.setAttribute("data-noi18n", ""); });
  function get(path) {
    return fetch(DATA + path, { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r; });
  }
  function levelCell(code) {
    var td = el("td", "lv");
    var w = WORD[code];
    var d = el("span", "dot " + (w ? "lv-" + code.toLowerCase() : "lv-none"));
    d.setAttribute("aria-hidden", "true");
    td.appendChild(d);
    td.appendChild(document.createTextNode(w || "—"));
    return td;
  }

  function parseCsv(text) {
    var lines = String(text).trim().split(/\r?\n/);
    var head = lines.shift().split(",");
    return lines.map(function (ln) {
      var c = ln.split(","), o = {};
      head.forEach(function (h, i) { o[h] = c[i] == null ? "" : c[i]; });
      return o;
    }).filter(function (o) { return ISO.test(o.date); });
  }

  function renderDays(rows) {
    var body = $("days-body");
    body.textContent = "";
    rows.filter(function (r) { return r.date >= SHOW_FROM; }).reverse().forEach(function (r) {
      var tr = el("tr", r.mode === "live" ? "live" : "retro");
      var td = el("td", "d");
      var a = el("a", null, trDate(r.date));
      a.href = "./?tarih=" + encodeURIComponent(r.date) + (EN ? "&lang=en" : "");
      td.appendChild(a);
      tr.appendChild(td);
      tr.appendChild(levelCell(r.level));
      tr.appendChild(el("td", "n", (r.raw_score || "–") + "/9"));
      var flags = el("td", "flags");
      CODES.forEach(function (c) {
        var on = r[c] === "1", na = r[c] !== "0" && r[c] !== "1";
        var m = el("span", "fm" + (on ? " on" : na ? " na" : ""));
        m.title = c + " " + TITLES[c] + ": " + (on ? L("işaret var", "signal") : na ? L("veri yok", "no data") : L("işaret yok", "no signal"));
        flags.appendChild(m);
      });
      var sr = el("span", "sr", CODES.filter(function (c) { return r[c] === "1"; }).map(function (c) { return TITLES[c]; }).join(", ") || L("işaret yok", "no signal"));
      flags.appendChild(sr);
      tr.appendChild(flags);
      tr.appendChild(el("td", "v", r.rules_version || "—"));
      tr.appendChild(el("td", "m", r.mode === "live" ? L("canlı", "live") : L("geriye dönük", "retro")));
      body.appendChild(tr);
    });
    $("days-note").textContent = rows.length ? L("Son kayıt: ", "Latest record: ") + trDate(rows[rows.length - 1].date) + "." : L("Kayıt yok.", "No records.");
  }

  function resultText(e) {
    if (EN) {
      if (e.kind === "kaçırılan") return "The Nasdaq Composite fell at least 10% from its 20-day high; the level was never RED in that period.";
      if (e.result === "teyit edildi") return "Within " + e.days_to_confirm + " days the Nasdaq Composite closed at least 5% below its close on the signal day.";
      if (e.result === "yanlış alarm") return "Within 20 days the Nasdaq Composite did not close 5% below its close on the signal day.";
      if (e.result === "bekliyor") return "The 20-day window is not over; as of " + trDate(e.checked_until) + " the drop threshold has not been seen.";
      return "No comparison data for this day.";
    }
    if (e.kind === "kaçırılan") return "Nasdaq Bileşik son 20 günün zirvesinden en az %10 geriledi; bu sürede seviye hiç KIRMIZI olmadı.";
    if (e.result === "teyit edildi") return e.days_to_confirm + " gün içinde Nasdaq Bileşik, işaret günündeki kapanışının en az %5 altında kapandı.";
    if (e.result === "yanlış alarm") return "20 gün içinde Nasdaq Bileşik işaret günündeki kapanışının %5 altına inmedi.";
    if (e.result === "bekliyor") return "20 günlük süre dolmadı; " + trDate(e.checked_until) + " itibarıyla düşüş eşiği görülmedi.";
    return "Bu gün için karşılaştırma verisi yok.";
  }

  function sicilTable(list, host) {
    host.textContent = "";
    if (!list.length) return;
    var t = el("table", "sicil");
    var th = el("thead"), hr = el("tr");
    (EN ? ["Date", "Event", "Result", "Explanation"] : ["Tarih", "Olay", "Sonuç", "Açıklama"]).forEach(function (h) { var c = el("th", null, h); c.scope = "col"; hr.appendChild(c); });
    th.appendChild(hr); t.appendChild(th);
    var tb = el("tbody");
    list.slice().reverse().forEach(function (e) {
      var tr = el("tr", e.result === "yanlış alarm" || e.kind === "kaçırılan" ? "miss" : "");
      tr.appendChild(el("td", "d", trDate(e.date)));
      tr.appendChild(el("td", null, e.kind === "kaçırılan" ? L("Düşüş (seviye ", "Drop (level ") + (WORD[e.level] || "—") + ")" : L("KIRMIZI'ya geçiş", "Switch to RED")));
      tr.appendChild(el("td", "r", EN ? (RESULT_EN[e.result] || RESULT_EN[e.kind] || e.result) : (RESULT_TR[e.result] || RESULT_TR[e.kind] || e.result)));
      tr.appendChild(el("td", "x", resultText(e)));
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    host.appendChild(t);
  }

  function renderSicil(s) {
    var all = (s.entries || []).filter(function (e) { return ISO.test(e.date) && e.date >= (s.show_from || SHOW_FROM); });
    var live = all.filter(function (e) { return e.mode === "live"; });
    var retro = all.filter(function (e) { return e.mode !== "live"; });
    var sm = s.summary_live || {};
    $("sicil-sum").textContent = EN ? (live.length
      ? "Live record (since " + trDate(s.freeze_date) + "): " + (sm.canli_sinyal || 0) + " switches to RED — " +
        (sm.canli_teyit || 0) + " followed by a fall, " + (sm.canli_yanlis_alarm || 0) + " not followed by a fall, " +
        (sm.canli_bekliyor || 0) + " pending; " + (sm.canli_kacirilan || 0) + " falls without RED."
      : "The live record started after " + trDate(s.freeze_date) + "; no live signal has been evaluated yet.")
      : live.length
      ? "Canlı kayıt (" + trDate(s.freeze_date) + "'ten beri): " + (sm.canli_sinyal || 0) + " KIRMIZI geçişi — " +
        (sm.canli_teyit || 0) + " ardından düşüş geldi, " + (sm.canli_yanlis_alarm || 0) + " düşüş gelmedi, " +
        (sm.canli_bekliyor || 0) + " bekliyor; " + (sm.canli_kacirilan || 0) + " KIRMIZI'sız düşüş."
      : "Canlı kayıt " + trDate(s.freeze_date) + " sonrasında başladı; henüz değerlendirilmiş canlı işaret yok.";
    sicilTable(live, $("sicil-live"));
    sicilTable(retro, $("sicil-retro"));
    $("sicil-retro-wrap").hidden = !retro.length;
    $("sicil-meta").textContent = L("Değerlendirme verisi: ", "Evaluation data: ") + trDate(s.data_until) + L(" · Kural sürümü ", " · Rules ") + (s.rules_version || "—");
  }

  get("history.csv").then(function (r) { return r.text(); }).then(function (t) { renderDays(parseCsv(t)); })
    .catch(function () { $("days-note").textContent = L("Arşiv dosyasına şu an ulaşılamadı.", "The archive file could not be reached right now."); });
  get("sicil.json").then(function (r) { return r.json(); }).then(renderSicil)
    .catch(function () { $("sicil-sum").textContent = L("Sicil dosyasına şu an ulaşılamadı.", "The track-record file could not be reached right now."); });
})();
