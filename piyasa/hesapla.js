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

  function $(id) { return document.getElementById(id); }
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
  function signedPct(v) { return (v > 0 ? "+" : v < 0 ? "−" : "") + "%" + num(Math.abs(v), 2); }
  function parse(s) {
    s = String(s || "").trim().replace(/\s/g, "");
    if (/,/.test(s)) s = s.replace(/\./g, "").replace(",", ".");   // 1.234,56 -> 1234.56
    var v = parseFloat(s);
    return isFinite(v) ? v : NaN;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
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
        localStorage.setItem(KEY, JSON.stringify({ a: $("varlik").value, c: ccy(), m: $("maliyet").value, q: $("miktar").value }));
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
      $("hatirla").checked = true;
    } catch (e) { /* ignore */ }
  }

  var UNIT_TR = { gram_altin: "gram altın", gram_gumus: "gram gümüş", dolar: "dolar", btc: "BTC", eth: "ETH", bist100: "puan" };

  function labels(a, c) {
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
    var L = labels(a, c);
    $("maliyet-label").textContent = L[0];
    $("miktar-label").textContent = L[1];
    var tp = todayPrice(a, c);
    $("maliyet").placeholder = tp ? "bugün: " + num(tp, tp >= 1000 ? 0 : 2) : "örn. 102,50";
    $("miktar").placeholder = a === "bist100" ? "örn. 10.000" : "örn. 10";
    save();
    var out = $("sonuc");
    out.textContent = "";
    if (!P) return;
    var cost = parse($("maliyet").value), qty = parse($("miktar").value);
    if (a === "bist100" && cost > 0) qty = qty / cost;           // TL invested -> index units
    var r = C.compute(a, cost, c, qty, P);
    if (!r) {
      if (show || $("maliyet").value || $("miktar").value) {
        var msg;
        if (!tp) msg = "Bu varlık için güncel fiyat yok; hesap yapılamaz.";
        else if (!(cost > 0)) msg = "Eksik: " + L[0] + " (bugünkü fiyat: " + num(tp, tp >= 1000 ? 0 : 2) + (a === "bist100" ? " puan" : c === "USD" && a !== "dolar" ? " $" : " TL") + "). Kendi ortalama maliyetini yaz.";
        else msg = "Eksik: " + L[1] + " Sıfırdan büyük bir sayı yaz.";
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
    var unitName = UNIT_TR[a], cur = r.ccy === "USD" ? "dolar" : "TL";
    out.appendChild(el("p", "label", "Sonuç"));
    out.appendChild(el("p", "big" + (r.plPct < 0 ? " neg" : ""), signedPct(r.plPct)));

    // plain-language summary (every number from the calculation above)
    var s1 = a === "bist100"
      ? num(r.costTotal, 2) + " TL, BIST 100 ortalama " + num(r.cost, 0) + " puandayken yatırılmış."
      : num(r.amount, Number.isInteger(r.amount) ? 0 : (r.amount < 1 ? 4 : 2)) + " " + unitName + ", tanesi ortalama " + money(r.cost, r.ccy) + ": toplam maliyet " + money(r.costTotal, r.ccy) + ".";
    var s2 = a === "bist100"
      ? "Bugün endeks " + num(r.price, 0) + " puan; aynı oranla bugünkü değer " + money(r.value, "TL") + "."
      : "Bugün 1 " + unitName + " " + money(r.price, r.ccy) + "; bugünkü değer " + money(r.value, r.ccy) + ".";
    var s3 = "Fark: " + (r.pl < 0 ? "−" : "+") + money(Math.abs(r.pl), r.ccy) + " (" + signedPct(r.plPct) + ").";
    [s1, s2, s3].forEach(function (x) { out.appendChild(el("p", "sum", x)); });
    var ratio = r.cost / r.price;
    if (ratio > 2 || ratio < 0.5) {
      out.appendChild(el("p", "notice", "Kontrol et: girdiğin maliyet (" + money(r.cost, r.ccy) + ") bugünkü fiyatın (" +
        money(r.price, r.ccy) + ") " + num(ratio, 1) + " katı. " + "1 " + unitName + " için ödediğin birim fiyatı (" + cur + ") girdiğinden emin ol."));
    }

    var t = el("table"), tb = el("tbody");
    row(tb, a === "bist100" ? "Bugünkü BIST 100" : "Bugünkü fiyat (1 " + unitName + ")", a === "bist100" ? num(r.price, 0) + " puan" : money(r.price, r.ccy));
    row(tb, "Toplam maliyet", money(r.costTotal, r.ccy));
    row(tb, "Bugünkü değer", money(r.value, r.ccy));
    row(tb, "Kâr / zarar", (r.pl < 0 ? "−" : "+") + money(Math.abs(r.pl), r.ccy), r.pl < 0 ? "neg" : null);
    row(tb, "Maliyetine dönmek için fiyat", a === "bist100" ? num(r.breakeven, 0) + " puan" : money(r.breakeven, r.ccy));
    row(tb, "Gereken yükseliş", r.toBreakevenPct <= 0 ? "Yok (maliyetin üzerindesin)" : signedPct(r.toBreakevenPct));
    t.appendChild(tb);
    out.appendChild(t);

    if (a === "bist100") return;
    out.appendChild(el("p", "label kicker", "Dolar/TL değişirse"));
    var showBe = a !== "dolar";
    var t2 = el("table"), th = el("thead"), hr = el("tr");
    var cols = ["Dolar/TL"];
    if (showBe) cols.push(r.ccy === "TL"
      ? (A.metal ? "Maliyetine dönmek için ons ($)" : "Maliyetine dönmek için 1 " + unitName + " ($)")
      : "Maliyetin TL karşılığı (1 " + unitName + ")");
    cols.push("Değer (TL)");
    cols.forEach(function (x) { hr.appendChild(el("th", null, x)); });
    th.appendChild(hr); t2.appendChild(th);
    var b2 = el("tbody");
    r.scenarios.forEach(function (sc) {
      var tr = el("tr");
      tr.appendChild(el("th", null, num(sc.usdtry, 2) + (sc.shockPct ? " (+%" + sc.shockPct + ")" : " (bugün)")));
      if (showBe) tr.appendChild(el("td", null, num(r.ccy === "TL" ? sc.breakevenUsd : sc.breakevenTl, 2)));
      tr.appendChild(el("td", null, sc.valueTl == null ? "—" : num(sc.valueTl, 0)));
      b2.appendChild(tr);
    });
    t2.appendChild(b2);
    out.appendChild(t2);
    var note = a === "dolar"
      ? "Değer sütunu, dolar/TL bu seviyeye gelirse elindeki dolarların TL karşılığıdır."
      : r.ccy === "TL"
        ? "Orta sütun: TL maliyetine dönmek için varlığın dolar fiyatının ne olması gerektiği" + (A.metal ? " (1 ons = 31,1035 gram)" : "") + ". Değer sütunu: dolar fiyatı bugünkü gibi kalırsa TL karşılığı."
        : "Maliyet dolar cinsinden; kur yalnız TL karşılığını değiştirir. Değer sütunu: dolar fiyatı bugünkü gibi kalırsa TL karşılığı.";
    out.appendChild(el("p", "mute small", note));
  }

  function init(d) {
    P = d && d.prices ? d.prices : null;
    var meta = P ? "Dolar/TL " + num(+P.usdtry, 4) + " · fiyat tarihi " + trDate(P.usdtry_asof) : "Güncel fiyat alınamadı.";
    $("fiyat-meta").textContent = meta;
    $("foot-meta").textContent = "Fiyat tarihi: " + (P ? trDate(P.usdtry_asof) : "—") + " · Kaynak: Piyasa Hava Durumu türetilmiş verisi";
    update();
  }

  ["varlik", "maliyet", "miktar", "hatirla"].forEach(function (id) {
    $(id).addEventListener(id === "varlik" || id === "hatirla" ? "change" : "input", function () { update(); });
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
