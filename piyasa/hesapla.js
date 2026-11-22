/* Piyasa Hava Durumu — position calculator UI (S4c).
   User input never leaves the device: the only request is the public tl.json (no user data).
   localStorage only when "Bu cihazda hatırla" is ticked. DOM APIs only. */
(function () {
  "use strict";
  var C = window.PHDCalc;
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var KEY = "phd-hesapla-v1";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var P = null;
  var I = window.PHD_I18N, EN = !!(I && I.en);
  var MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function L(tr, en) { return EN ? en : tr; }

  function $(id) { return document.getElementById(id); }
  if (EN) ["sonuc", "fiyat-meta", "foot-meta", "maliyet-label", "miktar-label", "maliyet", "miktar", "makas-ref"].forEach(function (id) { var e = $(id); if (e) e.setAttribute("data-noi18n", ""); });
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function num(v, nd) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return v.toLocaleString(EN ? "en-US" : "tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function signedPct(v) { var sg = v > 0 ? "+" : v < 0 ? "−" : ""; return EN ? sg + num(Math.abs(v), 2) + "%" : sg + "%" + num(Math.abs(v), 2); }
  function parse(s) {
    s = String(s || "").trim().replace(/\s/g, "");
    if (EN && /\./.test(s)) s = s.replace(/,/g, "");                // 1,234.56 -> 1234.56
    else if (/,/.test(s)) s = s.replace(/\./g, "").replace(",", ".");   // 1.234,56 -> 1234.56
    else if (EN) s = s.replace(/,/g, "");                            // 10,000 -> 10000
    var v = parseFloat(s);
    return isFinite(v) ? v : NaN;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + (EN ? MONTHS_EN : MONTHS)[+m[2] - 1] + " " + m[1] : "—";
  }
  function ccy() {
    var r = document.querySelector('input[name="ccy"]:checked');
    return r ? r.value : "TL";
  }
  function money(v, c) { return num(v, Math.abs(v) < 10 ? 4 : 2) + (c === "USD" ? " $" : " TL"); }

  function row(tb, label, value, cls) {
    var tr = el("tr");
    tr.appendChild(el("th", null, label));
    var td = el("td", cls || null, value);
    tr.appendChild(td);
    tb.appendChild(tr);
  }

  function save() {
    try {
      if ($("hatirla").checked) {
        localStorage.setItem(KEY, JSON.stringify({ a: $("varlik").value, c: ccy(), m: $("maliyet").value, q: $("miktar").value, s: $("makas").value }));
      } else {
        localStorage.removeItem(KEY);
      }
    } catch (e) { /* storage unavailable: ignore */ }
  }
  function load() {
    try {
      var s = JSON.parse(localStorage.getItem(KEY) || "null");
      if (!s) return;
      if (C.ASSETS[s.a]) $("varlik").value = s.a;
      Array.prototype.forEach.call(document.querySelectorAll('input[name="ccy"]'), function (r) { r.checked = r.value === s.c; });
      $("maliyet").value = String(s.m || "").slice(0, 32);
      $("miktar").value = String(s.q || "").slice(0, 32);
      $("makas").value = String(s.s || "").slice(0, 8);
      $("hatirla").checked = true;
    } catch (e) { /* ignore */ }
  }

  var UNIT_TR = EN ? { gram_altin: "gram of gold", gram_gumus: "gram of silver", dolar: "dollar", btc: "BTC", eth: "ETH", bist100: "points" }
                   : { gram_altin: "gram altın", gram_gumus: "gram gümüş", dolar: "dolar", btc: "BTC", eth: "ETH", bist100: "puan" };

  function labels(a, c) {
    if (EN) {
      var curE = c === "USD" ? "dollars" : "TL";
      if (a === "dolar") return ["On average, how many TL did you pay for 1 dollar?", "How many dollars do you have?"];
      if (a === "bist100") return ["On average, where was BIST 100 (points) when you bought?", "Amount invested (TL)"];
      if (a === "btc" || a === "eth") return ["On average, how many " + curE + " did you pay for 1 " + UNIT_TR[a] + "?", "How many " + UNIT_TR[a] + " do you have?"];
      return ["On average, how many " + curE + " did you pay per gram?", "How many grams do you have?"];
    }
    var cur = c === "USD" ? "dolar" : "TL";
    if (a === "dolar") return ["1 doları ortalama kaç TL'ye aldın?", "Kaç doların var?"];
    if (a === "bist100") return ["Aldığında BIST 100 ortalama kaç puandı?", "Yatırdığın tutar (TL)"];
    if (a === "btc" || a === "eth") return ["1 " + UNIT_TR[a] + " için ortalama kaç " + cur + " ödedin?", "Kaç " + UNIT_TR[a] + " var?"];
    return ["1 gram için ortalama kaç " + cur + " ödedin?", "Kaç gramın var?"];
  }
  function todayPrice(a, c) {
    var px = P ? C.prices(a, P) : null;
    if (!px) return null;
    return a === "dolar" || a === "bist100" || c !== "USD" ? px.tl : px.usd;
  }

  function update(show) {
    show = show === true;
    var a = $("varlik").value, A = C.ASSETS[a];
    var tlOnly = !!(A && A.tlOnly);
    $("ccy-set").hidden = tlOnly;
    var c = tlOnly ? "TL" : ccy();
    var LB = labels(a, c);
    $("maliyet-label").textContent = LB[0];
    $("miktar-label").textContent = LB[1];
    var tp = todayPrice(a, c);
    $("maliyet").placeholder = tp ? L("bugün: ", "today: ") + num(tp, tp >= 1000 ? 0 : 2) : L("örn. 102,50", "e.g. 102.50");
    $("miktar").placeholder = a === "bist100" ? L("örn. 10.000", "e.g. 10,000") : L("örn. 10", "e.g. 10");
    save();
    var out = $("sonuc");
    out.textContent = "";
    if (!P) return;
    var cost = parse($("maliyet").value), qty = parse($("miktar").value);
    if (a === "bist100" && cost > 0) qty = qty / cost;           // TL invested -> index units
    var spread = parse($("makas").value);
    var r = C.compute(a, cost, c, qty, P, spread > 0 ? spread : 0);
    if (spread >= 50) $("makas").setAttribute("aria-invalid", "true"); else $("makas").removeAttribute("aria-invalid");
    if (!r) {
      if (show || $("maliyet").value || $("miktar").value) {
        var msg;
        if (!tp) msg = L("Bu varlık için güncel fiyat yok; hesap yapılamaz.", "No current price for this asset; nothing to calculate.");
        else if (!(cost > 0)) msg = L("Eksik: ", "Missing: ") + LB[0] + L(" (bugünkü fiyat: ", " (today's price: ") + num(tp, tp >= 1000 ? 0 : 2) + (a === "bist100" ? L(" puan", " points") : c === "USD" && a !== "dolar" ? " $" : " TL") + L("). Kendi ortalama maliyetini yaz.", "). Enter your own average cost.");
        else msg = L("Eksik: ", "Missing: ") + LB[1] + L(" Sıfırdan büyük bir sayı yaz.", ". Enter a number greater than zero.");
        out.appendChild(el("p", "notice", msg));
        if (show) {
          var f = !(cost > 0) ? $("maliyet") : $("miktar");
          if (f) { f.setAttribute("aria-invalid", "true"); f.focus(); }
        }
      }
      return;
    }
    $("maliyet").removeAttribute("aria-invalid");
    $("miktar").removeAttribute("aria-invalid");
    var unitName = UNIT_TR[a], cur = r.ccy === "USD" ? L("dolar", "dollars") : L("TL", "TL");
    out.appendChild(el("p", "label", L("Sonuç", "Result")));
    out.appendChild(el("p", "big" + (r.plPct < 0 ? " neg" : ""), signedPct(r.plPct)));

    // plain-language summary (every number from the calculation above)
    var s1, s2, s3, amt = num(r.amount, Number.isInteger(r.amount) ? 0 : (r.amount < 1 ? 4 : 2));
    if (EN) {
      s1 = a === "bist100"
        ? num(r.costTotal, 2) + " TL invested when BIST 100 averaged " + num(r.cost, 0) + " points."
        : amt + " × " + unitName + " at an average " + money(r.cost, r.ccy) + " each: total cost " + money(r.costTotal, r.ccy) + ".";
      s2 = a === "bist100"
        ? "Today the index is at " + num(r.price, 0) + " points; at the same ratio the value today is " + money(r.value, "TL") + "."
        : "Today 1 " + unitName + " is " + money(r.price, r.ccy) + "; value today " + money(r.value, r.ccy) + ".";
      s3 = "Difference: " + (r.pl < 0 ? "−" : "+") + money(Math.abs(r.pl), r.ccy) + " (" + signedPct(r.plPct) + ").";
    } else {
      s1 = a === "bist100"
        ? num(r.costTotal, 2) + " TL, BIST 100 ortalama " + num(r.cost, 0) + " puandayken yatırılmış."
        : amt + " " + unitName + ", tanesi ortalama " + money(r.cost, r.ccy) + ": toplam maliyet " + money(r.costTotal, r.ccy) + ".";
      s2 = a === "bist100"
        ? "Bugün endeks " + num(r.price, 0) + " puan; aynı oranla bugünkü değer " + money(r.value, "TL") + "."
        : "Bugün 1 " + unitName + " " + money(r.price, r.ccy) + "; bugünkü değer " + money(r.value, r.ccy) + ".";
      s3 = "Fark: " + (r.pl < 0 ? "−" : "+") + money(Math.abs(r.pl), r.ccy) + " (" + signedPct(r.plPct) + ").";
    }
    [s1, s2, s3].forEach(function (x) { out.appendChild(el("p", "sum", x)); });
    var ratio = r.cost / r.price;
    if (ratio > 2 || ratio < 0.5) {
      out.appendChild(el("p", "notice", EN
        ? "Check: the cost you entered (" + money(r.cost, r.ccy) + ") is " + num(ratio, 1) + "× today's price (" + money(r.price, r.ccy) +
          "). Make sure you entered the price paid per 1 " + unitName + " (" + cur + ")."
        : "Kontrol et: girdiğin maliyet (" + money(r.cost, r.ccy) + ") bugünkü fiyatın (" +
        money(r.price, r.ccy) + ") " + num(ratio, 1) + " katı. " + "1 " + unitName + " için ödediğin birim fiyatı (" + cur + ") girdiğinden emin ol."));
    }

    var t = el("table"), tb = el("tbody");
    row(tb, a === "bist100" ? L("Bugünkü BIST 100", "BIST 100 today") : L("Bugünkü fiyat (1 ", "Price today (1 ") + unitName + ")", a === "bist100" ? num(r.price, 0) + L(" puan", " points") : money(r.price, r.ccy));
    row(tb, L("Toplam maliyet", "Total cost"), money(r.costTotal, r.ccy));
    row(tb, L("Bugünkü değer", "Value today"), money(r.value, r.ccy));
    row(tb, L("Kâr / zarar", "Profit / loss"), (r.pl < 0 ? "−" : "+") + money(Math.abs(r.pl), r.ccy), r.pl < 0 ? "neg" : null);
    row(tb, L("Maliyetine dönmek için fiyat", "Breakeven price"), a === "bist100" ? num(r.breakeven, 0) + L(" puan", " points") : money(r.breakeven, r.ccy));
    row(tb, L("Gereken yükseliş", "Rise needed"), r.toBreakevenPct <= 0 ? L("Yok (maliyetin üzerindesin)", "None (above your cost)") : signedPct(r.toBreakevenPct));
    if (r.spreadPct) {
      var spTxt = EN ? num(r.spreadPct, 2) + "%" : "%" + num(r.spreadPct, 2);
      row(tb, L("Bozdurunca eline geçen (makas ", "Cash received (spread ") + spTxt + ")", a === "bist100" ? money(r.netValue, "TL") : money(r.netValue, r.ccy));
      row(tb, L("Makas sonrası kâr / zarar", "Profit / loss after spread"), (r.netPl < 0 ? "−" : "+") + money(Math.abs(r.netPl), r.ccy) + " (" + signedPct(r.netPlPct) + ")", r.netPl < 0 ? "neg" : null);
      row(tb, L("Makas dahil maliyetine dönmek için fiyat", "Breakeven price incl. spread"), a === "bist100" ? num(r.netBreakeven, 0) + L(" puan", " points") : money(r.netBreakeven, r.ccy));
      row(tb, L("Makas dahil gereken yükseliş", "Rise needed incl. spread"), r.netToBreakevenPct <= 0 ? L("Yok", "None") : signedPct(r.netToBreakevenPct));
    }
    t.appendChild(tb);
    out.appendChild(t);
    if (r.spreadPct) out.appendChild(el("p", "mute small", L(
      "Makas satırları, piyasa fiyatı yerine bozdururken eline geçecek fiyatla hesaplanır. Makası sen girdin; gerçek makas yere ve saate göre değişir.",
      "The spread rows use the price you would actually receive when selling instead of the market price. You entered the spread; real spreads vary by dealer and time.")));

    if (a === "bist100") return;
    out.appendChild(el("p", "label kicker", L("Dolar/TL değişirse", "If USD/TRY changes")));
    var showBe = a !== "dolar";
    var t2 = el("table"), th = el("thead"), hr = el("tr");
    var cols = [L("Dolar/TL", "USD/TRY")];
    if (showBe) cols.push(r.ccy === "TL"
      ? (A.metal ? L("Maliyetine dönmek için ons ($)", "Breakeven ounce ($)") : L("Maliyetine dönmek için 1 ", "Breakeven for 1 ") + unitName + " ($)")
      : L("Maliyetin TL karşılığı (1 ", "Your cost in TL (1 ") + unitName + ")");
    cols.push(L("Değer (TL)", "Value (TL)"));
    cols.forEach(function (x) { hr.appendChild(el("th", null, x)); });
    th.appendChild(hr); t2.appendChild(th);
    var b2 = el("tbody");
    r.scenarios.forEach(function (sc) {
      var tr = el("tr");
      tr.appendChild(el("th", null, num(sc.usdtry, 2) + (sc.shockPct ? (EN ? " (+" + sc.shockPct + "%)" : " (+%" + sc.shockPct + ")") : L(" (bugün)", " (today)"))));
      if (showBe) tr.appendChild(el("td", null, num(r.ccy === "TL" ? sc.breakevenUsd : sc.breakevenTl, 2)));
      tr.appendChild(el("td", null, sc.valueTl == null ? "—" : num(sc.valueTl, 0)));
      b2.appendChild(tr);
    });
    t2.appendChild(b2);
    out.appendChild(t2);
    var note = EN ? (a === "dolar"
      ? "Value column: what your dollars are worth in TL if USD/TRY reaches that level."
      : r.ccy === "TL"
        ? "Middle column: the asset's dollar price needed to get back to your TL cost" + (A.metal ? " (1 ounce = 31.1035 grams)" : "") + ". Value column: TL value if the dollar price stays as today."
        : "Cost is in dollars; the exchange rate only changes the TL value. Value column: TL value if the dollar price stays as today.")
      : a === "dolar"
      ? "Değer sütunu, dolar/TL bu seviyeye gelirse elindeki dolarların TL karşılığıdır."
      : r.ccy === "TL"
        ? "Orta sütun: TL maliyetine dönmek için varlığın dolar fiyatının ne olması gerektiği" + (A.metal ? " (1 ons = 31,1035 gram)" : "") + ". Değer sütunu: dolar fiyatı bugünkü gibi kalırsa TL karşılığı."
        : "Maliyet dolar cinsinden; kur yalnız TL karşılığını değiştirir. Değer sütunu: dolar fiyatı bugünkü gibi kalırsa TL karşılığı.";
    out.appendChild(el("p", "mute small", note));
  }

  function init(d) {
    P = d && d.prices ? d.prices : null;
    var meta = P ? L("Dolar/TL ", "USD/TRY ") + num(+P.usdtry, 4) + L(" · fiyat tarihi ", " · price date ") + trDate(P.usdtry_asof) : L("Güncel fiyat alınamadı.", "Current prices could not be loaded.");
    $("fiyat-meta").textContent = meta;
    var mr = d && d.makas_ref && d.makas_ref.usd;
    if (mr && typeof mr.pct === "number" && /^\d{4}-\d{2}-\d{2}$/.test(mr.tarih || "")) {
      var refEl = $("makas-ref");
      refEl.textContent = EN
        ? "Reference: Central Bank (TCMB) banknote buying/selling rates for the US dollar differ by " + num(mr.pct, 2) + "% (TCMB rates of " + trDate(mr.tarih) + ", published around 15:30). Banks and dealers usually apply a wider spread. There is no free daily spread data for gold and silver; check your own dealer."
        : "Referans: TCMB dolar efektif alış ve satış kuru arasındaki fark %" + num(mr.pct, 2) + " (TCMB'nin " + trDate(mr.tarih) + " kuru, ~15:30'da açıklanır). Bankalar ve döviz büroları genellikle daha geniş makas uygular. Altın ve gümüş için serbest günlük makas verisi yok; kendi aldığın yerin fiyatlarına bak.";
      refEl.hidden = false;
    }
    $("foot-meta").textContent = L("Fiyat tarihi: ", "Price date: ") + (P ? trDate(P.usdtry_asof) : "—") + L(" · Kaynak: Piyasa Hava Durumu türetilmiş verisi", " · Source: Piyasa Hava Durumu derived data");
    update();
  }

  ["varlik", "maliyet", "miktar", "makas", "hatirla"].forEach(function (id) {
    $(id).addEventListener(id === "varlik" || id === "hatirla" ? "change" : "input", function () { update(); });
  });
  // "Makası bilmiyor musun?": two dealer prices -> spread %
  ["makas-satis", "makas-alis"].forEach(function (id) {
    $(id).addEventListener("input", function () {
      var sp = C.spreadFromPrices(parse($("makas-satis").value), parse($("makas-alis").value));
      if (sp != null) { $("makas").value = num(sp, 2); update(); }
    });
  });
  Array.prototype.forEach.call(document.querySelectorAll('input[name="ccy"]'), function (r) { r.addEventListener("change", function () { update(); }); });
  // Mobile: "next" on the cost field moves on; "done"/Enter or the button computes and closes the keyboard.
  $("maliyet").addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); $("miktar").focus(); }
  });
  $("calc").addEventListener("submit", function (e) {
    e.preventDefault();
    update(true);
    var out = $("sonuc");
    if (out.querySelector(".big")) {
      if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
      out.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
  load();
  fetch(DATA + "tl.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(init)
    .catch(function () { init(null); });
})();
